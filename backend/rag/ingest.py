from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)

PAGE_MARKER_REGEX = re.compile(r"\[\[\[PAGE:(?P<page>\d+)\]\]\]")
QA_REGEX = re.compile(
    r"(?is)\bque\s*:-\s*(?P<question>.+?)\s*ans\s*:-\s*(?P<answer>.+?)(?=\bque\s*:-|\Z)"
)


@dataclass
class IngestSettings:
    data_dir: Path
    vector_store_dir: Path
    embedding_model: str
    chunk_size: int = 1000
    chunk_overlap: int = 180


@dataclass
class QARecord:
    id: str
    doc: str
    page: int
    question: str
    answer: str


@dataclass
class ChunkRecord:
    id: str
    doc: str
    page: int
    qa_id: str
    text: str


@dataclass
class IngestedStore:
    qa_index: faiss.Index
    chunk_index: faiss.Index
    qa_records: list[QARecord]
    chunk_records: list[ChunkRecord]
    manifest: dict[str, Any]


@dataclass
class PDFPage:
    page_number: int
    text: str


class IngestPipeline:
    def __init__(self, settings: IngestSettings, client: OpenAI):
        self.settings = settings
        self.client = client

        self.settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.qa_index_path = self.settings.vector_store_dir / "qa_index.faiss"
        self.chunk_index_path = self.settings.vector_store_dir / "chunk_index.faiss"
        self.metadata_path = self.settings.vector_store_dir / "metadata.json"

    def ensure_indices(self) -> IngestedStore:
        manifest = self._build_manifest()
        if self._can_load_existing(manifest):
            return self._load_existing(manifest)
        return self._build_new(manifest)

    def embed_texts(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        if not texts:
            raise ValueError("Cannot embed an empty text list")

        vectors: list[np.ndarray] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self.client.embeddings.create(
                model=self.settings.embedding_model,
                input=batch,
            )
            matrix = np.array([row.embedding for row in response.data], dtype=np.float32)
            faiss.normalize_L2(matrix)
            vectors.append(matrix)

        return np.vstack(vectors)

    def _build_manifest(self) -> dict[str, Any]:
        pdf_path = resolve_dataset_pdf_path(self.settings.data_dir)
        return {
            "schema_version": 1,
            "pdf_relative_path": str(pdf_path.relative_to(self.settings.data_dir)),
            "pdf_sha256": _sha256_file(pdf_path),
            "embedding_model": self.settings.embedding_model,
            "chunk_size": self.settings.chunk_size,
            "chunk_overlap": self.settings.chunk_overlap,
        }

    def _can_load_existing(self, manifest: dict[str, Any]) -> bool:
        if not self.qa_index_path.exists() or not self.chunk_index_path.exists():
            return False
        if not self.metadata_path.exists():
            return False

        try:
            payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except Exception:
            return False

        stored_manifest = payload.get("manifest")
        qa_records = payload.get("qa_records", [])
        chunk_records = payload.get("chunk_records", [])
        if stored_manifest != manifest:
            return False
        if not qa_records or not chunk_records:
            return False

        return True

    def _load_existing(self, manifest: dict[str, Any]) -> IngestedStore:
        qa_index = faiss.read_index(str(self.qa_index_path))
        chunk_index = faiss.read_index(str(self.chunk_index_path))
        payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))

        qa_records = [QARecord(**row) for row in payload["qa_records"]]
        chunk_records = [ChunkRecord(**row) for row in payload["chunk_records"]]

        if qa_index.ntotal != len(qa_records):
            raise RuntimeError("QA index size does not match QA metadata records")
        if chunk_index.ntotal != len(chunk_records):
            raise RuntimeError("Chunk index size does not match chunk metadata records")

        logger.info("Loaded FAISS indices from %s", self.settings.vector_store_dir)
        return IngestedStore(
            qa_index=qa_index,
            chunk_index=chunk_index,
            qa_records=qa_records,
            chunk_records=chunk_records,
            manifest=manifest,
        )

    def _build_new(self, manifest: dict[str, Any]) -> IngestedStore:
        pdf_path = resolve_dataset_pdf_path(self.settings.data_dir)
        pages = extract_pdf_pages(pdf_path)
        qa_records = parse_qa_records(pages=pages, doc_name=pdf_path.name)
        if not qa_records:
            raise RuntimeError("No Q/A records could be parsed from dataset PDF")

        chunk_records = build_chunk_records(
            qa_records=qa_records,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        if not chunk_records:
            raise RuntimeError("No fallback chunks could be created from parsed Q/A records")

        qa_index = self._build_index_from_texts(
            [f"Question: {row.question}\nAnswer: {row.answer}" for row in qa_records]
        )
        chunk_index = self._build_index_from_texts([row.text for row in chunk_records])

        faiss.write_index(qa_index, str(self.qa_index_path))
        faiss.write_index(chunk_index, str(self.chunk_index_path))

        self.metadata_path.write_text(
            json.dumps(
                {
                    "manifest": manifest,
                    "qa_records": [asdict(row) for row in qa_records],
                    "chunk_records": [asdict(row) for row in chunk_records],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("Built and saved FAISS indices in %s", self.settings.vector_store_dir)

        return IngestedStore(
            qa_index=qa_index,
            chunk_index=chunk_index,
            qa_records=qa_records,
            chunk_records=chunk_records,
            manifest=manifest,
        )

    def _build_index_from_texts(self, texts: list[str]) -> faiss.Index:
        vectors = self.embed_texts(texts)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        return index


def resolve_dataset_pdf_path(data_dir: Path) -> Path:
    preferred = data_dir / "dataset.pdf"
    if preferred.exists():
        return preferred

    # Linux is case-sensitive. The project currently has DataSet.pdf, so we
    # safely resolve by case-insensitive name match without hard-failing.
    for candidate in sorted(data_dir.glob("*.pdf")):
        if candidate.name.lower() == "dataset.pdf":
            return candidate

    raise FileNotFoundError(
        f"Expected dataset PDF at {preferred}, but no case-insensitive match was found."
    )


def extract_pdf_pages(pdf_path: Path) -> list[PDFPage]:
    try:
        import pdfplumber  # type: ignore

        pages: list[PDFPage] = []
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                pages.append(PDFPage(page_number=idx, text=(page.extract_text() or "").strip()))
        return pages
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        pages = []
        for idx, page in enumerate(reader.pages, start=1):
            pages.append(PDFPage(page_number=idx, text=(page.extract_text() or "").strip()))
        return pages
    except ImportError as exc:
        raise RuntimeError(
            "Install either pdfplumber or PyPDF2 to parse backend/data/dataset.pdf"
        ) from exc


def parse_qa_records(pages: list[PDFPage], doc_name: str) -> list[QARecord]:
    stitched = "\n".join(f"[[[PAGE:{p.page_number}]]]\n{p.text}" for p in pages)
    page_offsets = [(m.start(), int(m.group("page"))) for m in PAGE_MARKER_REGEX.finditer(stitched)]

    records: list[QARecord] = []
    seen_hashes: set[str] = set()

    for match in QA_REGEX.finditer(stitched):
        page_number = _page_for_offset(page_offsets, match.start())

        question_raw = PAGE_MARKER_REGEX.sub(" ", match.group("question"))
        answer_raw = PAGE_MARKER_REGEX.sub(" ", match.group("answer"))

        question = _clean_question(question_raw)
        answer = _clean_answer(question=question, answer_raw=answer_raw)
        if not question or not answer:
            continue

        digest = _hash_normalized(f"{question} || {answer}")
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)

        records.append(
            QARecord(
                id=f"qa_{len(records) + 1:03d}",
                doc=doc_name,
                page=page_number,
                question=question,
                answer=answer,
            )
        )

    return records


def build_chunk_records(
    qa_records: list[QARecord],
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChunkRecord]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[ChunkRecord] = []
    seen_hashes: set[str] = set()

    for qa_row in qa_records:
        source_text = f"Question: {qa_row.question}\nAnswer: {qa_row.answer}"
        for chunk_text in _split_text(source_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
            normalized = " ".join(chunk_text.split()).strip()
            if not normalized:
                continue

            digest = _hash_normalized(normalized)
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)

            chunks.append(
                ChunkRecord(
                    id=f"chunk_{len(chunks) + 1:04d}",
                    doc=qa_row.doc,
                    page=qa_row.page,
                    qa_id=qa_row.id,
                    text=normalized,
                )
            )

    return chunks


def _clean_question(text: str) -> str:
    return " ".join(text.split()).strip(" -:\t\n")


def _clean_answer(question: str, answer_raw: str) -> str:
    answer = _remove_question_echoes(question=question, answer_text=answer_raw)
    lines = [
        re.sub(r"\s+", " ", line.strip())
        for line in answer.replace("\r", "\n").splitlines()
    ]
    lines = [line for line in lines if line and line != "?"]

    blocks: list[tuple[bool, str]] = []
    current: list[str] = []
    current_is_bullet = False

    def flush_current() -> None:
        nonlocal current
        if not current:
            return
        text = " ".join(current).strip()
        if text:
            blocks.append((current_is_bullet, text))
        current = []

    for line in lines:
        is_bullet = line.startswith(("●", "-", "•"))
        content = line.lstrip("●-• ").strip() if is_bullet else line

        if is_bullet:
            if current:
                flush_current()

            # OCR sometimes emits isolated bullet markers followed by text.
            if not content:
                continue

            if blocks and blocks[-1][0] and len(content.split()) <= 4:
                prev_is_bullet, prev_text = blocks[-1]
                blocks[-1] = (prev_is_bullet, f"{prev_text} {content}".strip())
                continue

            current_is_bullet = True
            current = [content]
            continue

        if not current and blocks and blocks[-1][0] and len(line.split()) <= 6:
            prev_is_bullet, prev_text = blocks[-1]
            blocks[-1] = (prev_is_bullet, f"{prev_text} {line}".strip())
            continue

        if not current:
            current_is_bullet = False
            current = [content]
            continue

        current.append(content)

    if current:
        flush_current()

    deduped_blocks: list[tuple[bool, str]] = []
    seen_hashes: set[str] = set()
    for is_bullet, text in blocks:
        digest = _hash_normalized(text)
        if not digest or digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        deduped_blocks.append((is_bullet, text))

    output_lines = [f"- {text}" if is_bullet else text for is_bullet, text in deduped_blocks]
    return "\n".join(output_lines).strip()


def _remove_question_echoes(question: str, answer_text: str) -> str:
    tokens = [re.escape(token) for token in re.findall(r"[A-Za-z0-9]+", question)]
    if len(tokens) < 4:
        return answer_text

    question_pattern = re.compile(r"\s*".join(tokens), re.IGNORECASE)
    return question_pattern.sub(" ", answer_text)


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    step = chunk_size - chunk_overlap
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


def _page_for_offset(page_offsets: list[tuple[int, int]], offset: int) -> int:
    page_number = 1
    for marker_offset, marker_page in page_offsets:
        if marker_offset <= offset:
            page_number = marker_page
        else:
            break
    return page_number


def _hash_normalized(text: str) -> str:
    normalized = re.sub(r"\W+", " ", text.lower()).strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
