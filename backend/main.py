import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag.retriever import RAGEngine, RAGSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


class AppSettings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    frontend_origin: str = Field("http://localhost:5173", alias="FRONTEND_ORIGIN")

    openai_embedding_model: str = Field(
        "text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )
    openai_chat_model: str = Field("gpt-4o-mini", alias="OPENAI_CHAT_MODEL")

    top_k: int = Field(5, alias="TOP_K")
    similarity_threshold: float = Field(0.55, alias="SIMILARITY_THRESHOLD")
    chunk_size: int = Field(1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(180, alias="CHUNK_OVERLAP")
    generation_max_tokens: int = Field(320, alias="GENERATION_MAX_TOKENS")

    data_dir: Path = Field(BASE_DIR / "data", alias="DATA_DIR")
    vector_store_dir: Path = Field(BASE_DIR / "vector_store", alias="VECTOR_STORE_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = AppSettings()

app = FastAPI(title="Banking RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

rag = RAGEngine(
    RAGSettings(
        openai_api_key=settings.openai_api_key,
        embedding_model=settings.openai_embedding_model,
        chat_model=settings.openai_chat_model,
        data_dir=settings.data_dir,
        vector_store_dir=settings.vector_store_dir,
        top_k=settings.top_k,
        similarity_threshold=settings.similarity_threshold,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        generation_max_tokens=settings.generation_max_tokens,
    )
)


class ChatRequest(BaseModel):
    sessionId: str
    message: str


class Source(BaseModel):
    doc: str
    page: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.on_event("startup")
def on_startup() -> None:
    rag.initialize()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = rag.answer_question(session_id=payload.sessionId, message=user_message)
        return ChatResponse(**result)
    except Exception as exc:  # pragma: no cover
        logger.exception("Chat request failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to process chat request") from exc
