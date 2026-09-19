#!/bin/sh
# Walk health, voices and one short speak, and check a real wav came back.
# Usage: scripts/smoke.sh [base_url]
set -eu

BASE_URL="${1:-${BASE_URL:-http://127.0.0.1:8000}}"
TEXT="${TEXT:-Smoke test one. This is a second sentence so the run has something to chunk.}"
WORK="$(mktemp -d -t smoke-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

echo "base url: $BASE_URL"

curl --fail --silent --show-error "$BASE_URL/health" -o "$WORK/health.json"
python3 - "$WORK/health.json" <<'PY'
import json, sys
health = json.load(open(sys.argv[1]))
assert health["status"] == "ok", health
for field in ("runpod_key_set", "endpoint", "max_words", "cloning_enabled"):
    assert field in health, "health is missing " + field
print("health ok:", json.dumps(health))
if not health["runpod_key_set"]:
    sys.exit("RUNPOD_API_KEY is not set on the server, so a speak cannot be tried.")
PY

curl --fail --silent --show-error "$BASE_URL/api/voices" -o "$WORK/voices.json"
python3 - "$WORK/voices.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1]))
assert len(body["voices"]) == 20, body["voices"]
assert body["default"] == "lucy", body["default"]
print("voices ok:", " ".join(body["voices"]))
PY

TEXT="$TEXT" python3 - "$WORK/request.json" <<'PY'
import json, os, sys
json.dump({"text": os.environ["TEXT"], "voice": "lucy"}, open(sys.argv[1], "w"))
PY

curl --fail --silent --show-error --no-buffer --max-time 900 \
  -X POST "$BASE_URL/api/speak" -H 'Content-Type: application/json' \
  --data-binary "@$WORK/request.json" -o "$WORK/stream.sse"

python3 - "$WORK/stream.sse" "$WORK/url.txt" <<'PY'
import json, sys
url = None
for line in open(sys.argv[1]):
    if not line.startswith("data: "):
        continue
    event = json.loads(line[6:])
    if event["type"] == "start":
        print("start:", event["chunks"], "chunks, voice", event["voice"])
    elif event["type"] == "chunk":
        print("chunk", event["index"] + 1, "ready,", event["seconds"], "seconds")
    elif event["type"] == "error":
        sys.exit(event["message"])
    elif event["type"] == "done":
        print("done:", event["chunks"], "chunks,", event["seconds"], "seconds of audio")
        url = event["url"]
if not url:
    sys.exit("the stream ended without a finished file")
open(sys.argv[2], "w").write(url)
PY

AUDIO_PATH="$(cat "$WORK/url.txt")"
echo "assembled file: $BASE_URL$AUDIO_PATH"
curl --fail --silent --show-error "$BASE_URL$AUDIO_PATH" -o "$WORK/speech.wav"
python3 - "$WORK/speech.wav" <<'PY'
import sys, wave
head = open(sys.argv[1], "rb").read(12)
assert head[:4] == b"RIFF", head
assert head[8:12] == b"WAVE", head
with wave.open(sys.argv[1], "rb") as audio:
    seconds = audio.getnframes() / float(audio.getframerate())
    print("wav ok:", audio.getnchannels(), "channel(s),", audio.getframerate(), "Hz,",
          round(seconds, 2), "seconds")
    assert seconds > 0.1, "the wav is too short to be speech"
PY
echo "smoke passed"
