from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag.pipeline import PipelineSettings, RAGPipeline
from rag.prompts import REFUSAL_MESSAGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent


class AppSettings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    frontend_origin: str = Field("http://localhost:5173", alias="FRONTEND_ORIGIN")
    openai_chat_model: str = Field("gpt-4o-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field("text-embedding-3-large", alias="OPENAI_EMBEDDING_MODEL")

    top_k: int = Field(4, alias="TOP_K")
    similarity_threshold: float = Field(0.46, alias="SIMILARITY_THRESHOLD")
    chunk_size: int = Field(1100, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(180, alias="CHUNK_OVERLAP")
    generation_max_tokens: int = Field(320, alias="GENERATION_MAX_TOKENS")

    max_message_length: int = Field(1000, alias="MAX_MESSAGE_LENGTH")
    rate_limit_requests: int = Field(20, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(60, alias="RATE_LIMIT_WINDOW_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = AppSettings()


def _allowed_frontend_origins(frontend_origin: str) -> list[str]:
    origins = {frontend_origin.rstrip("/")}
    if frontend_origin.startswith("http://localhost:"):
        origins.add(frontend_origin.replace("localhost", "127.0.0.1", 1).rstrip("/"))
    elif frontend_origin.startswith("http://127.0.0.1:"):
        origins.add(frontend_origin.replace("127.0.0.1", "localhost", 1).rstrip("/"))
    return sorted(origins)


app = FastAPI(title="Banking Chatbot Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_frontend_origins(settings.frontend_origin),
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

pipeline = RAGPipeline(
    PipelineSettings(
        openai_api_key=settings.openai_api_key,
        chat_model=settings.openai_chat_model,
        embedding_model=settings.openai_embedding_model,
        backend_dir=BACKEND_DIR,
        top_k=settings.top_k,
        similarity_threshold=settings.similarity_threshold,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        generation_max_tokens=settings.generation_max_tokens,
    )
)


class ChatRequest(BaseModel):
    sessionId: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=5000)


class Source(BaseModel):
    doc: str
    page: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            timestamps = self._hits[key]
            while timestamps and now - timestamps[0] >= self.window_seconds:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - timestamps[0])))
                return False, retry_after

            timestamps.append(now)
            return True, 0


rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    _ = request, exc
    body = ChatResponse(answer=REFUSAL_MESSAGE, sources=[]).model_dump()
    return JSONResponse(status_code=400, content=body)


@app.on_event("startup")
def startup() -> None:
    try:
        pipeline.initialize()
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to initialize RAG pipeline: %s", exc)
        raise


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse | JSONResponse:
    message = payload.message.strip()
    if not message:
        body = ChatResponse(answer=REFUSAL_MESSAGE, sources=[]).model_dump()
        return JSONResponse(status_code=400, content=body)
    if len(message) > settings.max_message_length:
        body = ChatResponse(answer=REFUSAL_MESSAGE, sources=[]).model_dump()
        return JSONResponse(status_code=400, content=body)

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{payload.sessionId}"
    allowed, retry_after = rate_limiter.allow(rate_key)
    if not allowed:
        body = ChatResponse(answer=REFUSAL_MESSAGE, sources=[]).model_dump()
        return JSONResponse(
            status_code=429,
            content=body,
            headers={"Retry-After": str(retry_after)},
        )

    try:
        result = pipeline.run(session_id=payload.sessionId, user_query=message)
        return ChatResponse(**result)
    except Exception as exc:  # pragma: no cover
        logger.exception("Chat request failed: %s", exc)
        body = ChatResponse(answer=REFUSAL_MESSAGE, sources=[]).model_dump()
        return JSONResponse(status_code=500, content=body)
