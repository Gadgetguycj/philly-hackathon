#!/bin/sh
set -eu

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
curl --fail --silent --show-error "$BASE_URL/health"
printf '\n'

if [ -n "${RUNPOD_API_KEY:-}" ]; then
  curl --fail --silent --show-error \
    -H 'Content-Type: application/json' \
    -d '{"team":"Smoke Test","prompt":"A friendly robot holding a small coffee cup"}' \
    "$BASE_URL/api/stickers"
  printf '\n'
fi

