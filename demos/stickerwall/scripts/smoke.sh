#!/bin/sh
set -eu

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
curl --fail --silent --show-error "$BASE_URL/health" | python -c '
import json
import sys
health = json.load(sys.stdin)
assert health["status"] == "ok"
assert isinstance(health["runpod_key_set"], bool)
assert isinstance(health["flux_model"], str)
'
printf '\n'

if [ -n "${RUNPOD_API_KEY:-}" ]; then
  curl --fail --silent --show-error \
    -H 'Content-Type: application/json' \
    -d '{"team":"Smoke Test","prompt":"A friendly robot holding a small coffee cup"}' \
    "$BASE_URL/api/stickers"
  printf '\n'
fi
