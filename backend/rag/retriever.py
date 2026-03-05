from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.chains import LLMChain, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .prompts import (
    QUERY_REWRITE_TEMPLATE,
    RAG_HUMAN_TEMPLATE,
    RAG_SYSTEM_PROMPT,
    STRICT_FALLBACK,
)

logger = logging.getLogger(__name__)

INDEX_DIR_NAME = "langchain_faiss"
INDEX_FAISS_FILE = "index.faiss"
INDEX_PKL_FILE = "index.pkl"
MAX_SNIPPET_CHARS = 200


@dataclass
class RAGSettings:
    openai_api_key: str
    embedding_model: str
    chat_model: str
    data_dir: Path
    vector_store_dir: Path
    top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 180
    similarity_threshold: float = 0.55
    generation_max_tokens: int = 320


class RAGEngine:
    def __init__(self, settings: RAGSettings):
        self.settings = settings
        self.index_dir = self.settings.vector_store_dir / INDEX_DIR_NAME

        self.embeddings = OpenAIEmbeddings(
            api_key=self.settings.openai_api_key,
            model=self.settings.embedding_model,
        )
        self.rewrite_llm = ChatOpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.chat_model,
            temperature=0,
            max_tokens=64,
        )
        self.answer_llm = ChatOpenAI(
            api_key=self.settings.openai_api_key,
            model=self.settings.chat_model,
            temperature=0,
            max_tokens=self.settings.generation_max_tokens,
        )

        self.query_rewrite_chain = LLMChain(
            llm=self.rewrite_llm,
            prompt=PromptTemplate(
                input_variables=["query"],
                template=QUERY_REWRITE_TEMPLATE,
            ),
        )

        self.vector_store: FAISS | None = None
        self.retriever: Any = None
        self.rag_chain: Any = None

    def initialize(self) -> None:
        self.settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = self._load_or_build_vector_store()
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": self.settings.top_k})

        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RAG_SYSTEM_PROMPT),
                ("human", RAG_HUMAN_TEMPLATE),
            ]
        )
        combine_docs_chain = create_stuff_documents_chain(self.answer_llm, answer_prompt)
        self.rag_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        logger.info("LangChain RAG initialized. index_dir=%s", self.index_dir)

    def answer_question(self, session_id: str, message: str) -> dict[str, Any]:
        _ = session_id
        if self.vector_store is None or self.rag_chain is None:
            raise RuntimeError("RAG engine is not initialized")

        raw_query = message.strip()
        if not raw_query:
            return self._fallback_response()

        # 1) USER QUERY (raw) -> 2) QUERY REWRITE
        rewritten_query = self._rewrite_query(raw_query)

        # 3) EMBEDDINGS + 4) RETRIEVAL with explicit score check
        scored_docs = self.vector_store.similarity_search_with_relevance_scores(
            query=rewritten_query,
            k=self.settings.top_k,
        )
        if not scored_docs:
            return self._fallback_response()

        top_score = max(score for _, score in scored_docs)
        if top_score < self.settings.similarity_threshold:
            return self._fallback_response()

        # 5) LLM ANSWER GENERATION through LangChain retrieval chain
        result = self.rag_chain.invoke({"input": rewritten_query})
        answer_text = self._extract_answer_text(result)
        if self._is_refusal(answer_text):
            return self._fallback_response()

        retrieved_docs = [doc for doc, _ in scored_docs]
        sources = self._build_sources(retrieved_docs)
        answer_with_sources = self._append_sources(answer_text, sources)
        return {"answer": answer_with_sources, "sources": sources}

    def _load_or_build_vector_store(self) -> FAISS:
        index_file = self.index_dir / INDEX_FAISS_FILE
        pickle_file = self.index_dir / INDEX_PKL_FILE

        if index_file.exists() and pickle_file.exists():
            logger.info("Loading FAISS vector store from %s", self.index_dir)
            return FAISS.load_local(
                folder_path=str(self.index_dir),
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True,
            )

        dataset_path = self._resolve_dataset_path()
        logger.info("Building FAISS vector store from %s", dataset_path)

        loader = PyPDFLoader(str(dataset_path))
        raw_docs = loader.load()
        if not raw_docs:
            raise RuntimeError(f"No text extracted from {dataset_path}")

        normalized_docs = [self._normalize_doc_metadata(doc) for doc in raw_docs]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        chunks = splitter.split_documents(normalized_docs)
        if not chunks:
            raise RuntimeError("No chunks were produced from dataset.pdf")

        vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(self.index_dir))
        logger.info("Saved FAISS vector store to %s", self.index_dir)
        return vector_store

    def _rewrite_query(self, query: str) -> str:
        result = self.query_rewrite_chain.invoke({"query": query})
        rewritten = str(result.get("text", "")).strip()
        if not rewritten:
            return query
        return rewritten

    def _resolve_dataset_path(self) -> Path:
        preferred = self.settings.data_dir / "dataset.pdf"
        if preferred.exists():
            return preferred

        # Linux is case-sensitive. Use a safe fallback for projects that still
        # have "DataSet.pdf" while keeping dataset.pdf as the canonical target.
        for candidate in sorted(self.settings.data_dir.glob("*.pdf")):
            if candidate.name.lower() == "dataset.pdf":
                return candidate

        raise FileNotFoundError(
            f"Expected dataset file at {preferred}, but no case-insensitive match was found."
        )

    def _normalize_doc_metadata(self, doc: Document) -> Document:
        source_path = doc.metadata.get("source")
        doc_name = Path(source_path).name if source_path else "dataset.pdf"
        page = int(doc.metadata.get("page", 0)) + 1

        doc.metadata["doc"] = doc_name
        doc.metadata["page"] = page
        return doc

    def _build_sources(self, docs: list[Document]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        seen: set[tuple[str, int, str]] = set()

        for doc in docs:
            doc_name = str(doc.metadata.get("doc", "dataset.pdf"))
            page = int(doc.metadata.get("page", 1))
            snippet = self._short_snippet(doc.page_content, max_chars=MAX_SNIPPET_CHARS)

            key = (doc_name, page, snippet)
            if key in seen:
                continue
            seen.add(key)
            sources.append({"doc": doc_name, "page": page, "snippet": snippet})

        return sources

    def _extract_answer_text(self, result: Any) -> str:
        if isinstance(result, dict):
            answer = result.get("answer") or result.get("result") or ""
            return str(answer).strip()
        return str(result).strip()

    def _append_sources(self, answer: str, sources: list[dict[str, Any]]) -> str:
        if not sources:
            return answer.strip()

        source_lines = "\n".join(
            f"- {source['doc']} (page {source['page']})" for source in sources
        )
        return f"{answer.strip()}\n\nSources:\n{source_lines}"

    def _fallback_response(self) -> dict[str, Any]:
        return {"answer": STRICT_FALLBACK, "sources": []}

    def _short_snippet(self, text: str, max_chars: int) -> str:
        normalized = " ".join(text.split()).strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 3].rstrip() + "..."

    def _is_refusal(self, answer: str) -> bool:
        normalized_answer = " ".join(answer.lower().split()).strip()
        normalized_fallback = " ".join(STRICT_FALLBACK.lower().split()).strip()
        if not normalized_answer:
            return True
        if normalized_answer == normalized_fallback:
            return True
        if "i don't have that information in my documents" in normalized_answer:
            return True
        return False
