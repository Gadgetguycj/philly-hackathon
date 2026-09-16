# Roast My Repo

This FastAPI app reads selected files from a public GitHub repository and streams a code roast from a RunPod OpenAI-compatible endpoint.

## Run locally

```sh
cp .env.example .env
# Add RUNPOD_API_KEY and either RUNPOD_ENDPOINT_ID or LLM_BASE_URL to .env.
# Create the bind mount directory described under Deploy.
docker compose up --build
curl http://127.0.0.1:8000/health
```

For the Qwen3 32B public endpoint, set `LLM_BASE_URL=https://api.runpod.ai/v2/qwen3-32b-awq/openai/v1` and `LLM_MODEL=Qwen/Qwen3-32B-AWQ`.

## GalaxyGate create_app body

Replace the uppercase values before calling `create_app` on the target instance.

```json
{
  "name": "roast",
  "image": "ghcr.io/galaxygate/philly-hackathon-roast:latest",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "RUNPOD_API_KEY",
    "RUNPOD_ENDPOINT_ID": "RUNPOD_ENDPOINT_ID",
    "LLM_MODEL": "Qwen/Qwen2.5-Coder-7B-Instruct"
  },
  "mounts": [{"host_path": "/data/roast", "container_path": "/data", "read_only": false}],
  "domain": "TEAM_NAME.galaxygate.app"
}
```

Use `LLM_BASE_URL` instead of `RUNPOD_ENDPOINT_ID` when calling a compatible public endpoint. `GITHUB_TOKEN` is optional and raises GitHub API rate limits.

## Deploy

Before deploying with a bind mount, create the host directory for the container user:

```sh
install -d -o 1000 -g 1000 /data/roast
```

Deploying without a mount also works. The data then lives inside the container and is lost when the container is removed.
