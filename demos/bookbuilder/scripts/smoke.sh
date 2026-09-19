#!/bin/sh
# Checks a running Bookbuilder: health, then a 10 page book, in order, saved and served.
# Usage: scripts/smoke.sh http://127.0.0.1:8000
set -eu
BASE="${1:-http://127.0.0.1:8000}"
IDEA="${IDEA:-A night shift nurse finds a door in the hospital basement that opens onto the same night.}"
export IDEA

curl --fail --silent --show-error "$BASE/health" | python3 -c '
import json, sys
health = json.load(sys.stdin)
if health["status"] != "ok":
    sys.exit("health is not ok: " + json.dumps(health))
if not health["runpod_key_set"]:
    sys.exit("RUNPOD_API_KEY is not set in the container, so no book can be written.")
if not health["base_url_set"]:
    sys.exit("LLM_BASE_URL is empty.")
print("health ok, model " + health["model"])
'

BODY=$(python3 -c 'import json, os; print(json.dumps({"idea": os.environ["IDEA"], "pages": 10}))')
RUN=$(curl --fail --silent --show-error -X POST "$BASE/api/runs" \
  -H "Content-Type: application/json" -d "$BODY" \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["run_id"])')
echo "run $RUN started, waiting for 10 pages"

BOOK=$(curl --fail --silent --show-error --no-buffer --max-time 1800 "$BASE/api/runs/$RUN/events" | python3 -c '
import json, sys
seen = []
book = ""
name = None
while True:
    line = sys.stdin.readline()
    if not line:
        break
    line = line.rstrip("\n")
    if line.startswith("event: "):
        name = line[7:]
    elif line.startswith("data: "):
        data = json.loads(line[6:])
        if name == "page_done":
            seen.append(data["index"])
            print("  page %d of %d, %d words, %s words per second"
                  % (data["index"], data["total"], data["words"], data["words_per_second"]),
                  file=sys.stderr)
        elif name == "heartbeat":
            print("  waiting for the model, %ss elapsed" % data["seconds"], file=sys.stderr)
        elif name == "failed":
            sys.exit("the run failed: " + data["message"])
        elif name == "done":
            book = data["book_id"]
            print("  %d pages in %ss, %s words per second"
                  % (data["pages"], data["seconds"], data["words_per_second"]), file=sys.stderr)
            break
if seen != list(range(1, len(seen) + 1)):
    sys.exit("the pages arrived out of order: %r" % seen)
if len(seen) != 10:
    sys.exit("expected 10 pages, got %d" % len(seen))
if not book:
    sys.exit("the run saved no book")
print(book)
')

curl --fail --silent --show-error "$BASE/b/$BOOK/" | python3 -c '
import sys
html = sys.stdin.read()
missing = [n for n in range(1, 11) if ("id=\"p%d\"" % n) not in html]
if missing:
    sys.exit("the book page is missing pages %r" % missing)
print("book page serves all 10 pages")
' 
echo "smoke ok: $BASE/b/$BOOK/"
