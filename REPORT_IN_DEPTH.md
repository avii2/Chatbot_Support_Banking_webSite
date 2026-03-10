# Full-Stack RAG Chatbot: In-Depth End-to-End Report

## A) Executive Summary
- This repository implements a banking-themed web app with an embedded RAG chatbot.
- The UI is a React  and the chatbot widget is implemented in `frontend/src/components/ChatWidget.jsx`.
- The backend is a FastAPI service  exposing exactly one  routes:  `POST /api/chat`.
- Retrieval and generation are coordinated by `RAGPipeline`, which uses OpenAI for rewriting, answering, and verification.
- The knowledge base is a local PDF indexed into FAISS .
- Anti-hallucination is enforced by multiple gates: similarity threshold, answerability check, grounding check, and strict refusal fallback.
- The frontend supports language selection and browser speech recognition; speech-to-text is client-side only.
- Source citation objects exist in schema/UI, but response citation payload generation is currently not implemented (`sources` is returned as an empty list).

## B) System Architecture

### Component Diagram (ASCII)
```text
+---------------------------------------------------------------+
| Browser                             
| - frontend/src/App.jsx                                        |
| - frontend/src/components/ChatWidget.jsx                      |
| - storage: sessionStorage/localStorage                        |
+-------------------------------+-------------------------------+
                                |
                                | POST /api/chat
                                | {"sessionId":"...","message":"..."}
                                v
+---------------------------------------------------------------+
| FastAPI Backend (backend/main.py)                             |
| - AppSettings (env-backed config)                             |
| - InMemoryRateLimiter                                          |
| - /health, /api/chat                                          |
+-------------------------------+-------------------------------+
                                |
                                | pipeline.run(session_id, user_query)
                                v
+---------------------------------------------------------------+
| RAGPipeline (backend/rag/pipeline.py)                         |
| 1) _strip_prompt_injection                                    |
| 2) _rewrite_query (OpenAI)                                    |
| 3) similarity_search_with_score (FAISS)                       |
| 4) _is_context_answerable (OpenAI verifier)                   |
| 5) answer_chain.invoke (OpenAI answer model)                  |
| 6) _is_answer_grounded (OpenAI verifier)                      |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| VectorIndexManager (backend/rag/index.py)                     |
| - load_or_build FAISS index                                   |
| - PDF load/extract/chunk/embed                                |
| - Persist: index.faiss, index.pkl, meta.json                  |
+---------------------------------------------------------------+
```

### Runtime Dependencies and Where They Run
| Layer    | Key dependencies  | Runtime location |
|---|---|---|
| Frontend app | `react`, `react-dom`, `react-router-dom`, `vite`, `tailwindcss`  | Browser + Node dev server |
| Backend API | `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` (`backend/requirements.txt`) | Python server process |
| RAG stack | `langchain`, `langchain-openai`, `langchain-community`, `openai` | Python server process + outbound OpenAI API |
| Vector store | `faiss-cpu` | Python server process + local filesystem |
| PDF ingestion | `pypdf` and `PyPDFLoader` via `langchain_community.document_loaders` | Python server process |
| Persistence | `backend/vector_store/langchain_faiss/*` | Local disk |

## C) Frontend Deep Dive

### ChatWidget UI Behavior
- File: `frontend/src/components/ChatWidget.jsx`
- Main component: `export default function ChatWidget()`.
- UX behavior:
  - Floating round button toggles chat open/closed.
  - Chat panel shows user and assistant messages with role-based styling.
  - Textarea supports Enter-to-send.
  - Loading indicator shows animated dots while request is in-flight.
 
### State Management (session/local storage)
- Chat session and history:
  - `SESSION_STORAGE_KEY = 'dummybank_chat_session_id'`
  - Per-session history key: `dummybank_messages_${sessionId}` via `historyKey()`.
  - Session ID generation uses `crypto.randomUUID()` fallback to timestamp/random.
  - Session ID and message history are stored in `sessionStorage`.
- Language preference:
  - `LANGUAGE_STORAGE_KEY = 'dummybank_chat_language'` in `localStorage`.
- Theme state lives in `frontend/src/App.jsx`:
  - `THEME_KEY = 'visioapps_theme'` in `localStorage`.

### API Request Format and Error Handling
- API base URL:
  - `apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'`
  - Config key defined in `frontend/.env.example` as `VITE_API_BASE_URL`.
- Request path:
  - `fetch(`${apiBaseUrl}/api/chat`, { method: 'POST', ... })`
- Request body format:
```json
{
  "sessionId": "<uuid-or-generated-id>",
  "message": "<trimmed user text>"
}
```
- Timeout logic:
  - `REQUEST_TIMEOUT_MS = 25000`
  - Uses `AbortController` and abort timer.
- Error behavior:
  - Non-2xx status throws `Error('HTTP <status>')` and displays generic fallback message.
  - Abort timeout shows `Request timed out. Please try again.`
  - Other failures show `Backend is unreachable. Please make sure the server is running and try again.`

### Language Selection + Voice-to-Text Behavior
- Language list is static in `LANGUAGES` array (13 language codes including `en-IN`, `hi-IN`, `ta-IN`, etc.).
- Language selection modal:
  - `openLanguageModal()`, `submitLanguageSelection()`.
  - Selected code is saved in `localStorage` and used for speech recognition `recognition.lang`.
- Voice capture workflow:
  - User holds Send button; `handleSendPressStart` starts a 220ms timer.
  - If held long enough, `startVoiceRecognition()` starts browser SpeechRecognition.
  - `onresult` accumulates interim transcripts.
  - `onend` sends final transcript using `handleSend(transcript)`.
  - Releasing/canceling stops recognition through `stopVoiceRecognition()`.
- Not found in code:
  - No server-side translation pipeline.
  - No fallback speech-to-text provider beyond browser APIs (`window.SpeechRecognition` / `window.webkitSpeechRecognition`).

## D) Backend Deep Dive

### FastAPI Routes and Schemas
- File: `backend/main.py`
- App initialization:
  - `app = FastAPI(title="Banking Chatbot Backend", version="1.0.0")`
- Routes:
  - `@app.get('/health')` -> `{"status":"ok"}`
  - `@app.post('/api/chat', response_model=ChatResponse)` -> chatbot response
- Pydantic models:
  - `ChatRequest`: `sessionId` (1..128), `message` (1..5000)
  - `Source`: `doc`, `page`, `snippet`
  - `ChatResponse`: `answer`, `sources: list[Source]`
- Validation/error handling:
  - `@app.exception_handler(RequestValidationError)` returns refusal message with HTTP `400`.
  - Route-level guards trim/validate message and return refusal for empty or too long message.

### Environment Variables and Config Loading
- Config class: `AppSettings(BaseSettings)`.
- Loading behavior:
  - `SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore')`
- Config keys used:
  - `OPENAI_API_KEY`
  - `FRONTEND_ORIGIN` (default `http://localhost:5173`)
  - `OPENAI_CHAT_MODEL` (default `gpt-4o-mini`)
  - `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-large`)
  - `TOP_K` (default `4`)
  - `SIMILARITY_THRESHOLD` (default `0.46`)
  - `CHUNK_SIZE` (default `1100`)
  - `CHUNK_OVERLAP` (default `180`)
  - `GENERATION_MAX_TOKENS` (default `320`)
  - `MAX_MESSAGE_LENGTH` (default `1000`)
  - `RATE_LIMIT_REQUESTS` (default `20`)
  - `RATE_LIMIT_WINDOW_SECONDS` (default `60`)

### CORS Settings
- Configured via `CORSMiddleware` in `backend/main.py`.
- Allowed origins are generated by `_allowed_frontend_origins(frontend_origin)` and include localhost/127.0.0.1 equivalent.
- `allow_methods=["POST", "OPTIONS"]`, `allow_headers=["*"]`, `allow_credentials=True`.

## E) RAG Pipeline Deep Dive (Core)

### PDF Loading Path and Preprocessing
- Index manager: `VectorIndexManager` in `backend/rag/index.py`.
- Data path properties:
  - `IndexSettings.dataset_path` -> `backend/data/dataset.pdf`
  - Fallback source -> `backend_dir.parent / 'frontend' / 'dataset.pdf'`
  - Case-insensitive PDF fallback via `_resolve_case_insensitive_pdf(...)`.
- PDF loading method:
  - `_load_pdf_documents(pdf_path)` using `PyPDFLoader`.
  - Adds metadata per document: `page` (1-based), `doc`, `source`.

### Chunking Strategy and Why Those Values
- Preferred extraction path: `_extract_qa_documents(docs)`.
  - Uses regex for `Que`/`Ans` structure:
    - `r"(?is)\bque\s*[:\-]+\s*(.*?)\s*\bans\s*[:\-]+\s*(.*?)(?=(?:\bque\s*[:\-]+)|\Z)"`
  - Builds each chunk as:
    - `Question: ...\nAnswer: ...`
  - Deduplicates with SHA-256 of normalized text.
- Fallback path: `_split_and_deduplicate(docs)`.
  - `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)`
  - Defaults come from env: `CHUNK_SIZE=1100`, `CHUNK_OVERLAP=180`.
- Why these exact values were chosen:
  - Not found in code (no inline rationale/comments/docs explaining selection).

### Embedding Model and Vector Store
- Embeddings class: `OpenAIEmbeddings` in `VectorIndexManager.__init__`.
- Model config key: `OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-large`).
- Vector store: `FAISS` (`langchain_community.vectorstores.FAISS`).
- Persisted artifacts:
  - `backend/vector_store/langchain_faiss/index.faiss`
  - `backend/vector_store/langchain_faiss/index.pkl`
  - `backend/vector_store/langchain_faiss/meta.json`

### Retrieval Parameters and Threshold Interpretation
- In `RAGPipeline.run(...)`:
  - Retrieval call: `self.vector_store.similarity_search_with_score(query=rewritten_query, k=self._effective_top_k())`
  - `_effective_top_k()` clamps configured `TOP_K` to range `[1,4]`.
- Score interpretation:
  - Returned FAISS value is treated as distance.
  - Converted to confidence by `_distance_to_confidence(distance) = 1 / (1 + max(distance, 0))`.
  - Refuses when `top_score < SIMILARITY_THRESHOLD`.
- This means threshold is compared against derived confidence, not raw FAISS distance.

### Query Rewrite Step Prompt + Guarantees
- Prompt constant: `QUERY_REWRITE_PROMPT` in `backend/rag/prompts.py`.
- Chain: `self.rewrite_chain = LLMChain(...)`.
- Parser: `StructuredOutputParser` with schema key `corrected_query`.
- Intended guarantees from prompt text:
  - Correct spelling/grammar/punctuation only.
  - Do not change meaning.
  - Keep original language.
  - Do not answer the question.
- Runtime fallback:
  - If parser fails, raw model text is used; if empty, original query is used.

### Answer Generation Prompt + Refusal Rules
- Generation prompt parts:
  - `ANSWER_SYSTEM_PROMPT`
  - `ANSWER_USER_PROMPT`
- Answer model setup:
  - `self.answer_llm = ChatOpenAI(..., temperature=0, max_tokens=GENERATION_MAX_TOKENS)`
- Refusal checks in `run()`:
  - empty query
  - injection-only query after sanitization
  - no retrieval hits
  - low confidence
  - context marked `NOT_ANSWERABLE`
  - model answer text matches/refers to refusal pattern (`_must_refuse`)
  - grounding check not `SUPPORTED`
- Final refusal payload is returned by `_refusal_response()` with fixed text and empty `sources`.

### Source Citation Generation (page numbers/snippets)
- Schema support exists:
  - `Source` model in `backend/main.py` with `doc`, `page`, `snippet`.
  - Frontend `ChatWidget` can render `msg.sources`.
- Metadata exists in indexed documents (`doc`, `page`, `source`).
- Actual response behavior in `RAGPipeline.run()`:
  - success returns `{"answer": answer_text, "sources": []}`.
- Conclusion:
  - Source citation payload generation is **not implemented** in current backend response path.

### Index Persistence and Startup Behavior (Build vs Load)
- FastAPI startup hook: `startup()` calls `pipeline.initialize()`.
- `RAGPipeline.initialize()` calls `self.index_manager.load_or_build()`.
- Build/load logic in `VectorIndexManager.load_or_build()`:
  - If index files + metadata exist and metadata matches expected values, load via `FAISS.load_local(...)`.
  - If metadata changed or missing, rebuild index from PDF.
- Metadata keys used for rebuild decisions:
  - `embedding_model`, `chunk_size`, `chunk_overlap`, `dataset_sha256`, `index_schema_version`.

## F) Safety & Anti-Hallucination Controls

### Prompt Injection Resistance
- `RAGPipeline.INJECTION_PATTERN` filters lines containing patterns like:
  - `ignore previous`, `system prompt`, `developer message`, `show hidden instructions`, `jailbreak`, `api key`, `token`.
- Method: `_strip_prompt_injection(query)` keeps only lines that do not match the pattern.
- If all lines are removed, request is refused.

### Refusal Conditions (Consolidated)
- Backend-level refusal/guard cases (`backend/main.py`):
  - invalid request shape or field constraints -> `400`
  - empty/whitespace message -> `400`
  - message length above `MAX_MESSAGE_LENGTH` -> `400`
  - rate limit exceeded -> `429`
  - unhandled exception -> `500`
- Pipeline-level refusal cases (`backend/rag/pipeline.py`):
  - empty sanitized query
  - no retrieval results
  - low retrieval confidence
  - context not answerable
  - generated answer flagged by `_must_refuse`
  - grounding verdict `UNSUPPORTED`

### Sensitive Data Handling
- Prompt-level policy in `ANSWER_SYSTEM_PROMPT` says never ask for OTP/PIN/password/CVV/full card number.
- API key is loaded from `.env` via `AppSettings`.
- Not found in code:
  - no user authentication/authorization layer
  - no secret manager integration (beyond env file usage)
  - no explicit PII redaction in logs

## G) Testing & Validation

### Existing Test Script
- File: `backend/scripts/smoke_test.sh`
- It sends canned prompts to `POST /api/chat` and asserts keyword-based answer/refusal behavior.

### Curl Tests (manual)

1. Health check
```bash
curl -sS http://127.0.0.1:8000/health
```
Expected:
```json
{"status":"ok"}
```

2. Normal in-scope query
```bash
curl -sS -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"demo-1","message":"What happens if I enter wrong PIN multiple times?"}'
```
Expected:
- HTTP `200`
- JSON shape: `{"answer":"<non-empty>","sources":[]}`

3. Out-of-scope query
```bash
curl -sS -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"demo-2","message":"What is the weather in Tokyo today?"}'
```
Expected:
- HTTP `200`
- `answer` equals refusal text from `backend/rag/prompts.py`

4. Oversized message guard (>1000 chars)
```bash
python3 - <<'PY'
import requests
msg = 'a' * 1201
r = requests.post('http://127.0.0.1:8000/api/chat', json={'sessionId':'demo-3','message':msg})
print(r.status_code)
print(r.json())
PY
```
Expected:
- HTTP `400`
- refusal response payload

5. Rate-limit behavior (default 20 req / 60 sec)
```bash
for i in $(seq 1 25); do
  code=$(curl -s -o /tmp/out.json -w '%{http_code}' -X POST http://127.0.0.1:8000/api/chat \
    -H 'Content-Type: application/json' \
    -d '{"sessionId":"burst-1","message":"hi"}')
  echo "$i -> $code"
done
```
Expected:
- early requests `200`, later requests may become `429` with `Retry-After` header

### Suggested Test Matrix
| Case | Example input | Expected status | Expected behavior |
|---|---|---|---|
| Normal | "What is 3D secure password?" | 200 | Context-grounded answer |
| Paraphrase | "Explain 3D secure in simple words" | 200 | Similar answer intent after rewrite/retrieval |
| Out-of-scope | "What is Bitcoin price?" | 200 | Fixed refusal text |
| Multilingual | "मेरी कार्ड फीस क्या है?" | 200 | Answer should follow prompt rule: same language as question |

## H) Deployment Notes

### How to Deploy (Based on Current Repo)
- Backend:
  - Run `uvicorn main:app` from `backend/` with required env vars set.
- Frontend:
  - Build static files with `npm run build` from `frontend/`.
  - Serve generated assets from `frontend/dist/` using any static host.
- Required runtime configs:
  - Backend: `OPENAI_API_KEY`, `FRONTEND_ORIGIN`, and optional RAG tuning keys.
  - Frontend: `VITE_API_BASE_URL`.

### Production Considerations
- Rate limiting is in-memory (`InMemoryRateLimiter`); replace with distributed backend (e.g., Redis) for multi-instance deployments.
- Secrets should not be committed to repo; load from environment/secret manager.
- Restrict `FRONTEND_ORIGIN` to real production domain(s).
- Add structured logging and request tracing for observability.
- Run behind reverse proxy/TLS terminator.
- Not found in code:
  - no Dockerfile
  - no Kubernetes manifests
  - no CI/CD pipeline definition

## I) Limitations + Roadmap (Prioritized)

### P0 (High Priority)
- Implement real source citations in API response (`sources`) using retrieved `Document.metadata` and snippets.
- Add API authentication/authorization for `POST /api/chat`.
- Replace in-memory rate limit with shared datastore-backed limiter.

### P1 (Medium Priority)
- Persist chat history/session memory outside process; current memory resets on restart.
- Align message length constraints (`ChatRequest.message max_length=5000` vs `MAX_MESSAGE_LENGTH=1000`) for consistency.
- Improve frontend error UX by surfacing backend status-specific messages (currently generic fallback for all non-2xx).

### P2 (Enhancement)
- Migrate deprecated `LLMChain` usage to newer Runnable-based LangChain APIs.
- Expand ingestion beyond single PDF (multi-document ingestion + metadata filtering).
- Add automated tests for API contract, retrieval quality, and multilingual behavior.

## Explicit "Not found in code" Notes
- Reasoning behind exact defaults `CHUNK_SIZE=1100`, `CHUNK_OVERLAP=180`, and `SIMILARITY_THRESHOLD=0.46` is not documented.
- Full citation generation (doc/page/snippet in response payload) is not implemented.
- Deployment IaC/container orchestration assets are not present.
- Server-side translation module is not present.
