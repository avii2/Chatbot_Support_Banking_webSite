#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
SESSION_ID="${SESSION_ID:-rag-acceptance-session}"

query() {
  local message="$1"
  echo ">>> ${message}"
  curl -sS "${API_BASE}/api/chat" \
    -H "Content-Type: application/json" \
    -d "{\"sessionId\":\"${SESSION_ID}\",\"message\":\"${message}\"}"
  echo
  echo
}

query "What happens if I enter wrong PIN multiple times?"
query "What is 3D secure password?"
query "How many times wrong 3D secure blocks card?"
query "What is the bank's IFSC format?"
