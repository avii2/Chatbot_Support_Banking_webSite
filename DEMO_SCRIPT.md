# Demo Script (2–3 Minutes)

## Goal
Show a complete working flow: banking UI -> chat question -> RAG answer -> refusal behavior -> backend health.

## Pre-Demo Setup (before recording)
- Ensure backend `.env` has a valid `OPENAI_API_KEY`.
- Start backend:
```bash
cd backend
uvicorn main:app --reload
```
- Start frontend:
```bash
cd frontend
npm run dev
```
- Keep two tabs ready:
  - `http://localhost:5173` (frontend)
  - `http://127.0.0.1:8000/health` (backend health)

## Recording Flow (Suggested Timeline)

### 0:00 - 0:20 | Intro + Architecture Snapshot
- Say: "This is a full-stack RAG chatbot demo. The React frontend calls FastAPI `POST /api/chat`, and backend retrieves from a local FAISS index built from `dataset.pdf`."
- Briefly show repo files:
  - `frontend/src/components/ChatWidget.jsx`
  - `backend/main.py`
  - `backend/rag/pipeline.py`
  - `backend/rag/index.py`

### 0:20 - 0:50 | Show UI
- Open `http://localhost:5173`.
- Click through a couple pages (`Accounts`, `Cards`) to show this is a normal banking UI.
- Mention: "The floating button opens `ChatWidget`; message history is session-scoped in browser storage."

### 0:50 - 1:40 | In-Scope Query (Happy Path)
- Open chat and ask:
  - "What happens if I enter wrong PIN multiple times?"
- Narrate:
  - "Frontend sends `{sessionId, message}` to `/api/chat`."
  - "Backend rewrites query, retrieves FAISS chunks, runs answerability + grounding checks, then responds."
- Wait for answer and show it in chat.

### 1:40 - 2:10 | Out-of-Scope Query (Refusal Path)
- Ask:
  - "What is Bitcoin price today?"
- Expected behavior:
  - Assistant returns refusal text:
  - `I don't have that information in my documents. Please contact support.`
- Narrate:
  - "This demonstrates hallucination guardrails when context does not support an answer."

### 2:10 - 2:30 | Health + Close
- Open `http://127.0.0.1:8000/health` and show `{"status":"ok"}`.
- Close with:
  - "The current backend returns `sources: []`; citation schema/UI exists but citation payload generation is not yet implemented."

## Optional 20-Second Add-On (if time permits)
- Hold the Send button to trigger browser voice input.
- Open language selector (`Aa`) and switch language.
- Mention: "Speech recognition is browser-side (`SpeechRecognition`), not server-side ASR."
