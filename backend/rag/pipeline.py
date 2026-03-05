from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.chains import LLMChain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .index import IndexSettings, VectorIndexManager
from .prompts import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_USER_PROMPT,
    CONTEXT_ANSWERABILITY_PROMPT,
    GROUNDING_CHECK_PROMPT,
    QUERY_REWRITE_PROMPT,
    REFUSAL_MESSAGE,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineSettings:
    openai_api_key: str
    chat_model: str
    embedding_model: str
    backend_dir: Path
    top_k: int = 4
    # Confidence is computed as 1 / (1 + L2 distance).
    # 0.46 keeps multilingual semantic matches while refusing unrelated queries.
    similarity_threshold: float = 0.46
    chunk_size: int = 1100
    chunk_overlap: int = 180
    generation_max_tokens: int = 320


class RAGPipeline:
    INJECTION_PATTERN = re.compile(
        r"(?i)(ignore\s+all\s+previous|ignore\s+previous|system\s+prompt|developer\s+message|"
        r"reveal\s+prompt|show\s+hidden\s+instructions|jailbreak|bypass\s+safety|api\s*key|token)"
    )

    def __init__(self, settings: PipelineSettings):
        self.settings = settings

        self.index_manager = VectorIndexManager(
            IndexSettings(
                openai_api_key=settings.openai_api_key,
                embedding_model=settings.embedding_model,
                backend_dir=settings.backend_dir,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        )

        self.rewrite_llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.chat_model,
            temperature=0,
            max_tokens=60,
        )
        self.answer_llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.chat_model,
            temperature=0,
            max_tokens=settings.generation_max_tokens,
        )
        self.verify_llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.chat_model,
            temperature=0,
            max_tokens=12,
        )

        self.rewrite_chain = LLMChain(
            llm=self.rewrite_llm,
            prompt=PromptTemplate(
                input_variables=["query"],
                template=QUERY_REWRITE_PROMPT,
            ),
        )
        self.grounding_check_chain = LLMChain(
            llm=self.verify_llm,
            prompt=PromptTemplate(
                input_variables=["question", "answer", "context"],
                template=GROUNDING_CHECK_PROMPT,
            ),
        )
        self.answerability_check_chain = LLMChain(
            llm=self.verify_llm,
            prompt=PromptTemplate(
                input_variables=["question", "context"],
                template=CONTEXT_ANSWERABILITY_PROMPT,
            ),
        )

        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ANSWER_SYSTEM_PROMPT),
                ("human", ANSWER_USER_PROMPT),
            ]
        )
        self.answer_chain = create_stuff_documents_chain(self.answer_llm, answer_prompt)

        self.vector_store = None

    def initialize(self) -> None:
        self.vector_store = self.index_manager.load_or_build()
        logger.info("RAG pipeline initialized.")

    def run(self, session_id: str, user_query: str) -> dict[str, Any]:
        started_at = time.perf_counter()
        rewritten_query = ""
        top_scores: list[float] = []
        outcome = "error"

        try:
            query = user_query.strip()
            if not query:
                outcome = "refused_empty_query"
                return self._refusal_response()
            if self.vector_store is None:
                raise RuntimeError("Pipeline is not initialized.")

            sanitized_query = self._strip_prompt_injection(query)
            if not sanitized_query:
                outcome = "refused_injection_pattern"
                return self._refusal_response()

            # 1) raw query -> 2) rewrite
            rewritten_query = self._rewrite_query(sanitized_query)

            # 3) embeddings + 4) retrieval
            scored_docs_raw = self.vector_store.similarity_search_with_score(
                query=rewritten_query,
                k=self._effective_top_k(),
            )
            if not scored_docs_raw:
                outcome = "refused_no_retrieval"
                return self._refusal_response()

            scored_docs = [
                (doc, self._distance_to_confidence(float(distance)))
                for doc, distance in scored_docs_raw
            ]
            top_scores = [round(score, 4) for _, score in scored_docs]

            top_score = max(score for _, score in scored_docs)
            if top_score < self.settings.similarity_threshold:
                logger.info(
                    "Refusing answer due to low retrieval confidence. top_score=%.4f threshold=%.4f",
                    top_score,
                    self.settings.similarity_threshold,
                )
                outcome = "refused_low_confidence"
                return self._refusal_response()

            docs = [doc for doc, _ in scored_docs]
            if not self._is_context_answerable(rewritten_query, docs):
                outcome = "refused_not_answerable"
                return self._refusal_response()

            # 5) answer generation from retrieved context only
            answer_text = str(self.answer_chain.invoke({"input": rewritten_query, "context": docs})).strip()
            if self._must_refuse(answer_text):
                outcome = "refused_model_response"
                return self._refusal_response()
            if not self._is_answer_grounded(rewritten_query, answer_text, docs):
                logger.info("Refusing answer because grounding check returned UNSUPPORTED")
                outcome = "refused_grounding_check"
                return self._refusal_response()

            outcome = "answered"
            # Keep response schema stable, but do not expose source details.
            return {"answer": answer_text, "sources": []}
        finally:
            latency_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "chat_request sessionId=%s rewritten_query=%r top_scores=%s outcome=%s latency_ms=%.2f",
                session_id,
                rewritten_query,
                top_scores,
                outcome,
                latency_ms,
            )

    def _rewrite_query(self, query: str) -> str:
        result = self.rewrite_chain.invoke({"query": query})
        rewritten = str(result.get("text", "")).strip()
        return rewritten or query

    def _effective_top_k(self) -> int:
        return max(1, min(self.settings.top_k, 4))

    def _strip_prompt_injection(self, query: str) -> str:
        lines = [line.strip() for line in query.splitlines()]
        safe_lines = [line for line in lines if line and not self.INJECTION_PATTERN.search(line)]
        if not safe_lines:
            return ""
        return "\n".join(safe_lines).strip()

    def _build_sources(self, docs: list[Document]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen: set[tuple[str, int, str]] = set()

        for doc in docs:
            doc_name = str(doc.metadata.get("doc", "dataset.pdf"))
            page = int(doc.metadata.get("page", 1))
            snippet = self._make_snippet(doc.page_content)

            key = (doc_name, page, snippet)
            if key in seen:
                continue
            seen.add(key)

            sources.append(
                {
                    "doc": doc_name,
                    "page": page,
                    "snippet": snippet,
                }
            )

        return sources

    def _make_snippet(self, text: str, max_chars: int = 200) -> str:
        clean = " ".join(text.split()).strip()
        if len(clean) <= max_chars:
            return clean
        return clean[: max_chars - 3].rstrip() + "..."

    def _must_refuse(self, answer: str) -> bool:
        norm_answer = " ".join(answer.lower().split()).strip()
        norm_refusal = " ".join(REFUSAL_MESSAGE.lower().split()).strip()

        if not norm_answer:
            return True
        if norm_answer == norm_refusal:
            return True
        if "i don't have that information in my documents" in norm_answer:
            return True
        if "do not have that information" in norm_answer:
            return True
        if "not provided in the context" in norm_answer:
            return True
        return False

    def _refusal_response(self) -> dict[str, Any]:
        return {"answer": REFUSAL_MESSAGE, "sources": []}

    def _distance_to_confidence(self, distance: float) -> float:
        return 1.0 / (1.0 + max(distance, 0.0))

    def _is_answer_grounded(self, question: str, answer: str, docs: list[Document]) -> bool:
        if not docs:
            return False

        context_blocks = []
        for index, doc in enumerate(docs, start=1):
            page = int(doc.metadata.get("page", 1))
            chunk = " ".join(doc.page_content.split()).strip()
            context_blocks.append(f"[Chunk {index} | page {page}] {chunk}")
        context_text = "\n\n".join(context_blocks)[:10000]

        verdict_raw = self.grounding_check_chain.invoke(
            {"question": question, "answer": answer, "context": context_text}
        )
        verdict = str(verdict_raw.get("text", "")).strip().upper()
        return verdict.startswith("SUPPORTED")

    def _is_context_answerable(self, question: str, docs: list[Document]) -> bool:
        if not docs:
            return False

        context_text = "\n\n".join(
            f"[Chunk {index}] {' '.join(doc.page_content.split()).strip()}"
            for index, doc in enumerate(docs, start=1)
        )[:10000]

        verdict_raw = self.answerability_check_chain.invoke(
            {"question": question, "context": context_text}
        )
        verdict = str(verdict_raw.get("text", "")).strip().upper()
        return verdict.startswith("ANSWERABLE")
