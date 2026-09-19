#!/bin/sh
# Build the image and run it on port 8000 with a throwaway data directory.
# Reads RUNPOD_API_KEY and the other settings from the current environment or .env.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${IMAGE:-tts-demo}"
PORT="${PORT:-8000}"
DATA="$(mktemp -d -t tts-data-XXXXXX)"
chown 1000:1000 "$DATA"

docker build -t "$IMAGE" "$ROOT"
echo "data dir: $DATA"
echo "open http://127.0.0.1:$PORT"

set -- --rm -p "$PORT:8000" -v "$DATA:/data" --name "${IMAGE}-local"
[ -f "$ROOT/.env" ] && set -- "$@" --env-file "$ROOT/.env"
for name in RUNPOD_API_KEY TTS_ENDPOINT MAX_WORDS PUBLIC_BASE_URL; do
  eval "value=\${$name:-}"
  [ -n "$value" ] && set -- "$@" -e "$name=$value"
done

exec docker run "$@" "$IMAGE"
