#!/bin/sh
set -eu

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
expected_key=false
[ -n "${RUNPOD_API_KEY:-}" ] && expected_key=true
expected_model=false
{ [ -n "${LLM_BASE_URL:-}" ] || [ -n "${RUNPOD_ENDPOINT_ID:-}" ]; } && expected_model=true
curl --fail --silent --show-error "$BASE_URL/health" | python3 -c '
import json, sys
health = json.load(sys.stdin)
assert health["status"] == "ok"
assert isinstance(health["runpod_key_set"], bool)
assert isinstance(health["model_configured"], bool)
assert health["runpod_key_set"] == (sys.argv[1] == "true")
assert health["model_configured"] == (sys.argv[2] == "true")
' "$expected_key" "$expected_model"

if [ -n "${RUNPOD_API_KEY:-}" ]; then
  if [ -z "${LLM_BASE_URL:-}" ] && [ -z "${RUNPOD_ENDPOINT_ID:-}" ]; then
    echo "Set LLM_BASE_URL or RUNPOD_ENDPOINT_ID to run the real generation." >&2
    exit 1
  fi
  curl --fail --no-buffer --silent --show-error \
    -H 'Content-Type: application/json' \
    -d "{\"repo_url\":\"${ROAST_REPO_URL:-https://github.com/encode/httpx}\"}" \
    "$BASE_URL/api/roast"
fi
