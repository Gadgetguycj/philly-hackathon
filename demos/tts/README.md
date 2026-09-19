# Text to Speech

Paste text, pick one of 20 voices, press Speak, hear it while it is still being
made, download the whole thing as one wav. The model is Chatterbox Turbo, an
open text to speech model from Resemble AI, served by RunPod's public endpoint.

This is a hackathon demo and a starting template. Everything it does is a real
call to RunPod. There is no offline mode and no canned audio, so with no key or
no credit it tells you exactly what the upstream said.

## Run it

```sh
cp .env.example .env          # put your RunPod API key in RUNPOD_API_KEY
scripts/run-local.sh          # builds the image, runs it on port 8000
```

Then open http://127.0.0.1:8000 and check it with:

```sh
scripts/smoke.sh http://127.0.0.1:8000
```

`docker compose up --build` works too, and writes audio to `/data/tts` on the
host. That directory has to be owned by uid 1000:

```sh
install -d -o 1000 -g 1000 /data/tts
```

## Configuration

| Variable | Default | What it does |
| --- | --- | --- |
| `RUNPOD_API_KEY` | none, required | Bearer token for api.runpod.ai |
| `TTS_ENDPOINT` | `chatterbox-turbo` | RunPod public endpoint id, or a full base URL |
| `MAX_WORDS` | `2000` | Words allowed in one run |
| `PUBLIC_BASE_URL` | unset | This app's public origin, needed for voice cloning |
| `DATA_DIR` | `/data` | Where audio, previews and clone clips are written |

Nothing else is read. There are no rate limits, no per IP quotas and no hourly
caps. The word cap is the only limit.

`TTS_ENDPOINT` normally holds the endpoint id and the app calls
`https://api.runpod.ai/v2/<id>/runsync`. If the value contains `://` it is used
as the base URL instead, which is how the tests point the app at a local
stand-in rather than at RunPod.

## How a run works

1. The browser posts the text to `/api/speak`.
2. The server counts words. Over `MAX_WORDS` it answers 400 and names both the
   cap and the count, before it calls RunPod at all.
3. The text is split at paragraph then sentence boundaries into chunks of at
   most 600 characters. A sentence longer than that is split on whitespace, so
   no word is ever cut in half.
4. Chunks go to RunPod one at a time, in order. Each finished wav is downloaded
   to `DATA_DIR` straight away, because RunPod's own audio links expire after
   seven days.
5. Every finished chunk is sent to the browser on a server sent events stream as
   soon as it lands, with a heartbeat every ten seconds so nothing times out
   behind a proxy. The browser schedules the chunks back to back on the Web
   Audio clock, so the first sentence plays while the last is still generating
   and there is no gap at the seams.
6. When the last chunk is in, the server joins them into one wav at
   `/a/<id>.wav` and the Download button appears.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | The page |
| GET | `/health` | `status`, `runpod_key_set`, `endpoint`, `max_words`, `cloning_enabled` |
| GET | `/api/voices` | The 20 preset ids, the default, and the cloning limits |
| POST | `/api/speak` | `{"text": "...", "voice": "lucy", "clone_id": ""}`, answers a server sent events stream |
| GET | `/p/<voice>.wav` | One fixed sentence in that voice, generated once and then cached on disk |
| POST | `/api/clone` | Upload a clip, multipart field `clip` |
| GET | `/a/<id>.wav` | The finished file for a run |
| GET | `/a/<id>/<nnn>.wav` | One chunk of a run |
| GET | `/clones/<name>` | An uploaded clip, so RunPod can fetch it |

Stream events are `start`, `chunk`, `ping`, `done` and `error`.

## Voices

The 20 presets, as RunPod documents them: aaron, abigail, anaya, andy, archer,
brian, chloe, dylan, emmanuel, ethan, evelyn, gavin, gordon, ivan, laura, lucy,
madison, marisol, meera, walter. The default is lucy. Each one has a Play button
that speaks a single fixed sentence, generated once and cached in
`DATA_DIR/previews`.

## Voice cloning

Upload a clip of up to 30 seconds and 5 MB as wav, mp3, m4a or ogg. The app
stores it under `DATA_DIR/clones` and passes its public URL to RunPod as
`voice_url`, which overrides the preset voice. RunPod fetches that URL over the
internet, so the app has to know its own public address. Without
`PUBLIC_BASE_URL` the feature is switched off and the page says so.

## Errors

Whatever RunPod said comes back, with the API key stripped out. A 401 says the
key is wrong and names `RUNPOD_API_KEY`. A 402 says the account has no credit.
Anything else is reported with its status and the upstream body.

## Cost

RunPod bills $0.001 per second of generated audio. A 2000 word run is roughly
13 minutes of speech, so about 80 cents.

## Tests

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The suite stands up a stand-in Chatterbox endpoint on a real socket that answers
with the documented response shape and a real wav, so the app's own HTTP client,
JSON handling and wav joining all run for real. It covers the word cap on both
sides, chunk sizes and word boundaries, chunk order inside the assembled file,
the assembled header and duration, a first chunk that is playable before the
last one is requested, the heartbeat, the key never reaching a response or a log
line, cloning being off without `PUBLIC_BASE_URL`, and a 402 turning into a
credit message.
