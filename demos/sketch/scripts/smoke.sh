#!/bin/sh
set -eu

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SKETCH="${SKETCH:-$(dirname "$0")/../samples/sketch.jpg}"
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
print("health ok")
' "$expected_key" "$expected_model"

if [ -n "${RUNPOD_API_KEY:-}" ] && [ -n "${LLM_BASE_URL:-}" ]; then
  curl --fail --silent --show-error --max-time "${REQUEST_TIMEOUT_SECONDS:-900}" \
    -F "image=@$SKETCH" -F "notes=${NOTES:-}" "$BASE_URL/api/sketch" | python3 -c '
import json, sys
result = json.load(sys.stdin)
if "url" not in result:
    sys.exit(result.get("detail", "The server returned no page."))
print(sys.argv[1] + result["url"], "in", result["elapsed_seconds"], "seconds")
' "$BASE_URL"
fi
