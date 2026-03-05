#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
REFUSAL="I don't have that information in my documents. Please contact support."

pass_count=0
fail_count=0

run_case() {
  local name="$1"
  local message="$2"
  local mode="$3"
  local payload
  payload=$(printf '{"sessionId":"smoke-%s","message":"%s"}' "$name" "$message")

  local response
  response=$(curl -sS -X POST "$BASE_URL/api/chat" \
    -H 'Content-Type: application/json' \
    -d "$payload")

  if RESPONSE="$response" MODE="$mode" REFUSAL="$REFUSAL" python3 - <<'PY'
import json, os, sys

data = json.loads(os.environ["RESPONSE"])
answer = (data.get("answer") or "").lower()
mode = os.environ["MODE"]
refusal = os.environ["REFUSAL"].lower()

if mode == "pin":
    ok = ("4" in answer) and ("disable" in answer or "not be accepted" in answer or "re-enable" in answer)
elif mode == "secure":
    ok = ("online" in answer) and ("mandatory" in answer or "required" in answer)
elif mode == "secure_block":
    ok = ("5" in answer) and ("block" in answer)
elif mode == "refusal":
    ok = answer.strip() == refusal.strip()
else:
    ok = False

if not ok:
    print(data.get("answer", ""))
    sys.exit(1)
PY
  then
    echo "PASS: $name"
    pass_count=$((pass_count + 1))
  else
    echo "FAIL: $name"
    fail_count=$((fail_count + 1))
  fi
}

run_case "wrong-pin" "What happens if I enter wrong PIN multiple times?" "pin"
run_case "what-is-3d" "What is 3D secure password?" "secure"
run_case "wrong-3d" "How many times wrong 3D secure blocks card?" "secure_block"
run_case "unrelated" "What is the bank IFSC format?" "refusal"

echo "----"
echo "Passed: $pass_count"
echo "Failed: $fail_count"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
