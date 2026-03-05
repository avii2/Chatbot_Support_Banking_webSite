# Bank + RAG Chatbot using langchain 

End-to-end demo banking website with an embedded chatbot widget powered by FastAPI + FAISS + OpenAI.

## Tech Stack

- Frontend: React  + Tailwind CSS
- Backend: FastAPI 
- Retrieval: FAISS local index on disk
- Embeddings: OpenAI embeddings API
- LLM: OpenAI chat completions API

## Project Structure

```text
Assignment_01/
├── backend/
│
│   ├── config.py
│   ├── main.py
│   ├── rag_service.py
│   ├── requirements.txt
│   ├── schemas.py
│   ├── data/
│   │   ├── accounts_faq.md
│   │   ├── card_fees.txt
│   │   ├── dispute_process.md
│   │   ├── kyc_requirements.txt
│   │   ├── loan_eligibility.md
│   │   └── support_escalation.txt
│   └── storage/

├── frontend/
│   
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── index.css
│       ├── main.jsx
│       ├── components/
│       │   └── ChatWidget.jsx
│       └── pages/
│           ├── Accounts.jsx
│           ├── Cards.jsx
│           ├── Fees.jsx
│           ├── Home.jsx
│           ├── Loans.jsx
│           └── Support.jsx
└── README.md
```

## Setup

### 1) Backend

```bash
cd backend
cp .env.example .env
# edit .env and set OPENAI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`.

### 2) Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

## Demo Steps

1. Start backend and frontend.
2. Open `http://localhost:5173`.
3. Click the floating chat button at bottom-right.
4. Ask questions like:
   - "What is the minimum balance for urban savings accounts?"
   - "What is the annual fee waiver for Signature card?"
   - "How do I escalate a complaint?"
5. Confirm chatbot replies include source snippets from local docs.


