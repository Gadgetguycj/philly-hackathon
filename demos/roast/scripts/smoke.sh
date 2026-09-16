#!/bin/sh
set -eu

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
curl --fail --silent --show-error "$BASE_URL/health"
printf '\n'

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

