# Sketch to Site

This FastAPI app turns a phone photograph of a hand-drawn website sketch into a web page and hosts that page.
The photo goes to a vision model on an OpenAI-compatible RunPod endpoint, and the HTML that comes back is saved under `/data/sites`.

## Run locally

```sh
cp .env.example .env
# Add RUNPOD_API_KEY and either RUNPOD_ENDPOINT_ID or LLM_BASE_URL to .env.
# Create the bind mount directory described under Deploy.
docker compose up --build
curl http://127.0.0.1:8000/health
scripts/smoke.sh
```

Open `http://127.0.0.1:8000/` on a phone, take a photo of a sketch, and the page appears at `/s/<id>/` with a QR code for that address.
`samples/sketch.jpg` is a drawn sample for testing without a phone. `scripts/make_sample_sketch.py` draws it again if you want a different one.

## Routes

| Route | What it does |
| --- | --- |
| `GET /` | The phone page: take a photo, build the page, scan the QR code. |
| `POST /api/sketch` | Multipart `image` and optional `notes`. Returns `{"id", "url", "elapsed_seconds"}`. |
| `GET /s/<id>/` | The generated page, served with a Content-Security-Policy that blocks every outbound request. |
| `GET /sites` | Every page built so far, newest first, with the sketch it came from. |
| `GET /health`, `GET /api/usage` | Configuration and the hourly generation count. |

The response body of `POST /api/sketch` is one JSON object. While the GPU is still waking, the server flushes a newline every `KEEPALIVE_INTERVAL_SECONDS`, because Cloudflare answers 524 when an origin sends no byte for 100 seconds and a cold start takes minutes. Leading whitespace is legal in front of a JSON document, so the body is still parsed as one object. A single space follows the moment the model starts writing, which is how the phone switches from "GPU is waking up" to "Writing your page". An upstream failure inside the first interval returns HTTP 502 with the upstream body unchanged, and a later failure arrives as `{"detail": ...}` in the streamed object.

A request that builds no page gives its slot of the hourly cap back, so a run of cold-start failures cannot lock a team out of their own app.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `RUNPOD_API_KEY` | none | Bearer token for the endpoint. Required. |
| `RUNPOD_ENDPOINT_ID` | none | Builds `LLM_BASE_URL` as `https://api.runpod.ai/v2/<id>/openai/v1`. |
| `LLM_BASE_URL` | from the endpoint id | OpenAI-compatible base URL. |
| `LLM_MODEL` | `Qwen/Qwen2.5-VL-7B-Instruct` | Vision model name sent in the request. |
| `MAX_GENERATIONS_PER_HOUR` | `20` | Hourly cap, counted in SQLite. |
| `REQUEST_TIMEOUT_SECONDS` | `900` | Read timeout for the model call. |
| `KEEPALIVE_INTERVAL_SECONDS` | `10` | Gap between the whitespace bytes sent while the model is thinking. |
| `DATA_DIR` | `/data` | Holds `sketch.db` and `sites/<id>/`. |

## GalaxyGate create_app body

Replace the uppercase values before calling `create_app` on the target instance.

```json
{
  "name": "sketch",
  "image": "127.0.0.1:5000/sketch:base",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "RUNPOD_API_KEY",
    "RUNPOD_ENDPOINT_ID": "RUNPOD_ENDPOINT_ID",
    "LLM_MODEL": "Qwen/Qwen2.5-VL-7B-Instruct",
    "MAX_GENERATIONS_PER_HOUR": "20",
    "REQUEST_TIMEOUT_SECONDS": "900"
  },
  "mounts": [{"host_path": "/data/sketch", "container_path": "/data", "read_only": false}],
  "domain": "TEAM_NAME.galaxygate.app"
}
```

Use `LLM_BASE_URL` instead of `RUNPOD_ENDPOINT_ID` when calling a compatible public endpoint.

## Deploy

Before deploying with a bind mount, create the host directory for the container user:

```sh
install -d -o 1000 -g 1000 /data/sketch
```

Deploying without a mount also works. The pages then live inside the container and are lost when the container is removed.

## Tests

```sh
python -m pytest
```

The tests run against a fake OpenAI-compatible server defined in `tests/conftest.py`. Nothing in `app/` ever fakes a model call.
