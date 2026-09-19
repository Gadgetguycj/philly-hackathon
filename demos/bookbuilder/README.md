# Bookbuilder

Type an idea for a book, press Build, and watch a hundred pages get written page by page.
The model plans the chapters first, then writes every page in order, and each page appears
in the browser as the tokens arrive. The finished book is saved and gets a shareable address.

The point of the demo is speed, so the header shows the page counter, the elapsed time and
the words per second while the book is being written.

## Run it

```sh
cp .env.example .env
# Put your RUNPOD_API_KEY in .env.
install -d -o 1000 -g 1000 /data/bookbuilder
docker compose up --build
scripts/smoke.sh http://127.0.0.1:8000
```

`scripts/run-local.sh` does the same thing with a throwaway data directory instead of
`/data/bookbuilder`.

The default endpoint is RunPod's public Kimi endpoint, which is OpenAI compatible. Point
`LLM_BASE_URL` at any other OpenAI compatible base URL, such as your own serverless vLLM
endpoint, and nothing else has to change. The app sends a plain `/chat/completions` request
with `stream: true` and reads the chunks as they come back.

## Reasoning models

A reasoning model answers in two parts. The answer arrives as `content` and the thinking
arrives beside it, as `reasoning_content` on RunPod's Kimi and as `reasoning` on vLLM. This
app reads `content` only, so no thinking ever reaches a page or the browser.

Thinking still costs tokens, and a model that thinks past its budget sends back nothing at
all. Kimi with a 200 token budget spent 199 of them thinking and returned an empty reply,
which is what an empty outline looks like. Two things deal with that. The budgets are large
enough to think and then write, 4000 tokens for the outline and 1600 for a page. And
`LLM_EXTRA` carries the field that turns the thinking off, because every endpoint spells it
differently.

```sh
LLM_EXTRA='{"thinking":{"type":"disabled"}}'   # RunPod's Kimi
LLM_EXTRA='{"reasoning_effort":"low"}'         # gpt-oss on vLLM
```

RunPod's public Kimi endpoint needs one more field in that object. It answers with HTTP 200
and a zero byte body for any `temperature` except 0.6, which the app hits because it sends
0.4 for the outline and 0.8 for a page. Measured on 2026-09-19: absent or 0.6 answered 9
times out of 9, and 0.4, 0.8 and 1.0 came back empty 8 times out of 8. So the value that
builds a book on that endpoint is

```sh
LLM_EXTRA='{"thinking":{"type":"disabled"},"temperature":0.6}'
```

Whatever is in `LLM_EXTRA` is merged into the request body at the top level, after the
fields the app sets, so it can also replace one of them. It is empty by default, so the app
is not tied to one vendor. A value that is not a JSON object is ignored, with a warning in
the log at startup.

When the endpoint reports `completion_tokens_details.reasoning_tokens`, the `done` event
carries the total for the run as `reasoning_tokens`. That is how you see a model thinking
instead of writing. The field is absent when the endpoint does not report it.

## How it works

**Plan first.** One request asks for a JSON object with a title and a list of chapters, each
with a one line summary and a page count. The reply is parsed strictly. If it does not have
that shape, the app asks once more with a firmer instruction. If the second reply is also
wrong the run fails and shows the raw reply, rather than guessing what the model meant. The
chapter page counts are then scaled to add up to exactly the number of pages that was asked
for, keeping the proportions the model chose.

**Then the pages.** One request per page, about 300 words each. Every page request carries
the outline, the current chapter summary, and a rolling recap built from the tail of the
previous page and a shorter tail of the page before it. The whole book is never sent back.
A page of a 100 page book is asked for with about 4000 characters of prompt, near a
thousand tokens. The default endpoint holds 256K, so the budget is not the reason for
keeping it small. A small prompt is a fast prompt, and speed is the demo.

**Concurrency.** Up to three requests are in flight at once, and the limit is never exceeded.
The unit of parallelism is the chapter, not the page: chapter workers run three at a time,
and the pages inside a chapter are strictly sequential because page N is written from the
tail of page N minus 1. Cutting the work at chapter boundaries is what keeps continuity,
because a chapter already has a written contract in the outline, which is its summary and
its place in the chapter list. Pages never appear out of order. A single emitter walks page
1, 2, 3 and so on, forwarding tokens live when the page it is on is the page being written,
and replaying a page that was written ahead of its turn in one go. A page that was finished early appears the
instant the page before it is done.

**Nothing is capped.** There is no hourly limit, no per IP limit and no quota. The only limit
is the page count the reader picks.

## Routes

| Route | What it does |
| --- | --- |
| `GET /` | The build page. Idea, optional title, page count, Build and Stop. |
| `POST /api/runs` | `{"idea", "title", "pages"}`. Starts a run and returns `{"run_id", "book_id"}`. |
| `GET /api/runs/<id>/events` | The event stream for that run. |
| `POST /api/runs/<id>/stop` | Cancels the requests in flight and keeps the pages that finished. |
| `GET /b/<id>/` | The finished book, with a table of contents and an anchor per page. |
| `GET /b/<id>/book.md` | The same book as markdown. |
| `GET /books`, `GET /api/books` | Recent books, newest first. |
| `GET /health`, `GET /api/config` | Configuration, and what the build page needs to draw itself. |

## The event stream

Server sent events, one JSON object per event.

| Event | When |
| --- | --- |
| `run` | The run was accepted. |
| `status` | The phase changed, or a page is being retried. |
| `outline` | The outline parsed. Carries the title and every chapter. |
| `page_start`, `delta`, `page_done` | One page, in that order, always in page order. |
| `page_dropped` | A page that had started will not be finished, so the browser removes it. |
| `heartbeat` | Ten seconds passed with nothing else to send. |
| `failed` | The run stopped on an error. The message is the upstream error with the key removed. |
| `done` | The run ended, whether it finished, was stopped or failed. Carries the book address, and `reasoning_tokens` when the endpoint reported any. |

Every event carries an id, so a browser that loses the connection resumes from where it was
instead of replaying the book. A cold endpoint can take minutes to answer, so the heartbeat
keeps the connection from going quiet for more than ten seconds and getting cut by a proxy.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `RUNPOD_API_KEY` | none | The bearer token. Required. |
| `LLM_BASE_URL` | `https://api.runpod.ai/v2/moonshot-kimi/openai/v1` | Any OpenAI compatible base URL. |
| `LLM_MODEL` | `kimi-k2.6` | The model name sent in the request. |
| `LLM_EXTRA` | empty | A JSON object merged into every request body at the top level. |
| `BOOK_PAGES` | `30` | The page count the selector starts on. |
| `DATA_DIR` | `/data` | Books are written to `DATA_DIR/books/<id>/`. |

Nothing else is read from the environment.

## Errors

The upstream error is shown as it came back, with the key removed from the text. A 401 says
the key was rejected. A 402 says the RunPod account has no credit. A 404 names the base URL
and the model. If a page request fails before its first token, it is tried once more, because
that is what a cold endpoint looks like. Anything else stops the run and keeps the pages that
were already finished.

## On disk

```
DATA_DIR/books/<id>/
  book.md        the whole book as markdown
  outline.json   the parsed outline
  meta.json      written last, so a directory without it never finished
  pages/0001.md  one file per page
```
