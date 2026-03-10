# Full-Stack RAG Chatbot: High-Level Report

## Project Snapshot
- The project is a React banking UI with an embedded chatbot that answers from a local PDF knowledge base.
- Backend API is FastAPI  two routes: `GET /health` and `POST /api/chat`.
- Retrieval and generation are orchestrated by `RAGPipeline`.
- Vector index is local FAISS.
- Embeddings and LLM calls use OpenAI via `langchain-openai`.
- The backend uses a strict refusal strategy when retrieval grounding is insufficient.

## Architecture (Runtime)
```text
Browser: React + Tailwind 
 
            |
            | POST /api/chat
            v
[FastAPI: backend ]
            |
            v
[RAGPipeline: backend/rag/pipeline.py]
   | query rewrite (OpenAI)
   | retrieval (FAISS)
   | answerability check (OpenAI)
   | answer generation (OpenAI)
   | grounding check (OpenAI)
            |
            v
Response JSON: {answer, sources}

Index build/load path
backend/rag/index.py -> backend/data/dataset.pdf -> FAISS files + meta.json
```

## End-to-End Flow
- User opens chat bubble, enters a question, and `ChatWidget` sends:
  - `{"sessionId":"...","message":"..."}` to `${VITE_API_BASE_URL}/api/chat`.
- Backend validates payload, applies in-memory rate limit, and calls `pipeline.run(session_id, user_query)`.
- Pipeline sanitizes prompt-injection patterns, rewrites query, retrieves FAISS chunks, checks confidence, checks answerability, generates answer, and runs grounding verification.
- If any guard fails, backend returns the fixed refusal text from `backend/rag/prompts.py`.

## Data + RAG Pipeline
- Startup (`@app.on_event("startup")`) calls `pipeline.initialize()`.
- `VectorIndexManager.load_or_build()`:
  - loads existing index if `index.faiss`, `index.pkl`, and `meta.json` match expected metadata;
  - otherwise rebuilds from `backend/data/dataset.pdf`.
- Rebuild path:
  - PDF load (`PyPDFLoader`) -> Q/A extraction regex (`Que`/`Ans`) -> fallback recursive chunking (`CHUNK_SIZE`, `CHUNK_OVERLAP`) -> OpenAI embeddings -> FAISS save.
- Retrieval score interpretation:
  - raw FAISS distance is converted to confidence with `1 / (1 + distance)`.
  - refusal if top confidence < `SIMILARITY_THRESHOLD`.

## Hallucination and Safety Controls
- Model temperatures are `0` for rewrite, answer, and verification models.
- Prompts enforce context-only answers and fixed refusal when unsupported.
- Grounding and answerability are separately verified before final response.
- Injection-like lines are stripped using `INJECTION_PATTERN` in `RAGPipeline`.
- Request hardening:
  - Pydantic schema validation
  - message length guard (`MAX_MESSAGE_LENGTH`)
  - in-memory IP+session rate limiting
 
## Local Run
```bash
# Backend
cd backend
cp .env.example .env
# set OPENAI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
- Frontend: `http://localhost:5173`
- Backend health: `http://127.0.0.1:8000/health`

##  future improvements improvements 
- Source citations are modeled (`Source` schema) but actual citation payload generation is not implemented in `RAGPipeline.run` (returns `sources: []`).
- No authentication/authorization layer is present for chat API.
- No production deployment manifests (Docker/K8s/CI) found in code.
- Conversation memory is stored in-process and not persisted/shared across instances.
