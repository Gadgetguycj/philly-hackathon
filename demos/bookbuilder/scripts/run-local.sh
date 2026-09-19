#!/bin/sh
# Builds the image and runs it on port 8000 with a throwaway data directory.
set -eu
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo "Copy .env.example to .env and put your RUNPOD_API_KEY in it." >&2
  exit 1
fi
DATA=$(mktemp -d)
chown 1000:1000 "$DATA" 2>/dev/null \
  || echo "Could not give $DATA to uid 1000. Run this as root or the container cannot save books." >&2
docker build -t bookbuilder .
echo "Books from this run land in $DATA"
exec docker run --rm -p 8000:8000 --env-file .env -v "$DATA:/data" --name bookbuilder bookbuilder
