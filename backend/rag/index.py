from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


@dataclass
class IndexSettings:
    openai_api_key: str
    embedding_model: str
    backend_dir: Path
    chunk_size: int = 1100
    chunk_overlap: int = 180

    @property
    def data_dir(self) -> Path:
        return self.backend_dir / "data"

    @property
    def dataset_path(self) -> Path:
        return self.data_dir / "dataset.pdf"

    @property
    def vector_store_dir(self) -> Path:
        return self.backend_dir / "vector_store"

    @property
    def index_dir(self) -> Path:
        return self.vector_store_dir / "langchain_faiss"

    @property
    def frontend_dataset_path(self) -> Path:
        return self.backend_dir.parent / "frontend" / "dataset.pdf"


class VectorIndexManager:
    INDEX_SCHEMA_VERSION = "qa_pairs_v1"

    def __init__(self, settings: IndexSettings):
        self.settings = settings
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )

    def load_or_build(self) -> FAISS:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_dataset_pdf()
        expected_meta = self._expected_index_meta(self.settings.dataset_path)

        faiss_file = self.settings.index_dir / "index.faiss"
        pkl_file = self.settings.index_dir / "index.pkl"
        meta_file = self.settings.index_dir / "meta.json"

        if faiss_file.exists() and pkl_file.exists() and meta_file.exists():
            stored_meta = self._load_meta(meta_file)
            if stored_meta != expected_meta:
                logger.info("Index metadata changed, rebuilding vector store.")
            else:
                logger.info("Loading existing vector store from %s", self.settings.index_dir)
                return FAISS.load_local(
                    folder_path=str(self.settings.index_dir),
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True,
                )
        elif faiss_file.exists() and pkl_file.exists() and not meta_file.exists():
            logger.info("Index metadata file missing, rebuilding vector store.")

        logger.info("Building vector store from %s", self.settings.dataset_path)
        docs = self._load_pdf_documents(self.settings.dataset_path)
        index_docs = self._extract_qa_documents(docs)
        if not index_docs:
            # Fallback to generic chunking if Q/A extraction fails.
            index_docs = self._split_and_deduplicate(docs)
        if not index_docs:
            raise RuntimeError("No text chunks were produced from dataset PDF.")

        vector_store = FAISS.from_documents(index_docs, self.embeddings)
        self.settings.index_dir.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(self.settings.index_dir))
        self._save_meta(meta_file, expected_meta)
        logger.info("Vector store saved to %s", self.settings.index_dir)
        return vector_store

    def _expected_index_meta(self, dataset_path: Path) -> dict[str, str | int]:
        return {
            "embedding_model": self.settings.embedding_model,
            "chunk_size": self.settings.chunk_size,
            "chunk_overlap": self.settings.chunk_overlap,
            "dataset_sha256": self._sha256_file(dataset_path),
            "index_schema_version": self.INDEX_SCHEMA_VERSION,
        }

    def _save_meta(self, path: Path, meta: dict[str, str | int]) -> None:
        path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _load_meta(self, path: Path) -> dict[str, str | int]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file_obj:
            for block in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _ensure_dataset_pdf(self) -> None:
        if self.settings.dataset_path.exists():
            return

        source = self.settings.frontend_dataset_path
        if not source.exists():
            source = self._resolve_case_insensitive_pdf(
                search_dir=self.settings.backend_dir.parent / "frontend",
                expected_name="dataset.pdf",
            )

        if source is None or not source.exists():
            raise FileNotFoundError(
                "Could not find source PDF at frontend/dataset.pdf "
                "(or case-insensitive equivalent)."
            )

        self.settings.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, self.settings.dataset_path)
        logger.info("Copied dataset from %s to %s", source, self.settings.dataset_path)

    def _load_pdf_documents(self, pdf_path: Path) -> list[Document]:
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        normalized: list[Document] = []

        for doc in docs:
            page = int(doc.metadata.get("page", 0)) + 1
            doc.metadata["page"] = page
            doc.metadata["doc"] = pdf_path.name
            doc.metadata["source"] = str(pdf_path)
            normalized.append(doc)

        return normalized

    def _split_and_deduplicate(self, docs: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        chunks = splitter.split_documents(docs)

        unique_chunks: list[Document] = []
        seen_hashes: set[str] = set()

        for chunk in chunks:
            normalized = " ".join(chunk.page_content.lower().split()).strip()
            if not normalized:
                continue

            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                continue

            seen_hashes.add(digest)
            unique_chunks.append(chunk)

        logger.info(
            "PDF chunking complete. total_chunks=%s unique_chunks=%s",
            len(chunks),
            len(unique_chunks),
        )
        return unique_chunks

    def _extract_qa_documents(self, docs: list[Document]) -> list[Document]:
        tagged_text = self._build_tagged_text(docs)
        page_markers = self._collect_page_markers(tagged_text)
        qa_pattern = re.compile(
            r"(?is)\bque\s*[:\-]+\s*(.*?)\s*\bans\s*[:\-]+\s*(.*?)(?=(?:\bque\s*[:\-]+)|\Z)"
        )

        qa_docs: list[Document] = []
        seen_hashes: set[str] = set()

        for match in qa_pattern.finditer(tagged_text):
            question = self._clean_text(match.group(1), keep_newlines=False)
            answer_text = re.sub(r"\[PAGE\s+\d+\]", " ", match.group(2), flags=re.IGNORECASE)
            answer = self._clean_text(answer_text, keep_newlines=True)
            if not question or not answer:
                continue

            page = self._page_for_offset(page_markers, match.start())
            content = f"Question: {question}\nAnswer: {answer}"
            normalized = " ".join(content.lower().split()).strip()
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                continue

            seen_hashes.add(digest)
            qa_docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "page": page,
                        "doc": self.settings.dataset_path.name,
                        "source": str(self.settings.dataset_path),
                    },
                )
            )

        logger.info("Q/A extraction complete. qa_docs=%s", len(qa_docs))
        return qa_docs

    def _build_tagged_text(self, docs: list[Document]) -> str:
        blocks: list[str] = []
        for doc in docs:
            page = int(doc.metadata.get("page", 1))
            blocks.append(f"[PAGE {page}]\n{doc.page_content}")
        return "\n\n".join(blocks)

    def _collect_page_markers(self, text: str) -> list[tuple[int, int]]:
        markers: list[tuple[int, int]] = []
        for marker in re.finditer(r"\[PAGE\s+(\d+)\]", text, flags=re.IGNORECASE):
            markers.append((marker.start(), int(marker.group(1))))
        return markers

    def _page_for_offset(self, markers: list[tuple[int, int]], offset: int) -> int:
        page = 1
        for marker_offset, marker_page in markers:
            if marker_offset <= offset:
                page = marker_page
            else:
                break
        return page

    def _clean_text(self, text: str, *, keep_newlines: bool) -> str:
        clean = text.replace("\u00a0", " ")
        if keep_newlines:
            lines = []
            for line in clean.splitlines():
                compact = " ".join(line.split()).strip()
                if compact:
                    lines.append(compact)
            return "\n".join(lines).strip()
        return " ".join(clean.split()).strip()

    def _resolve_case_insensitive_pdf(self, search_dir: Path, expected_name: str) -> Path | None:
        if not search_dir.exists():
            return None
        for candidate in sorted(search_dir.glob("*.pdf")):
            if candidate.name.lower() == expected_name.lower():
                return candidate
        return None
