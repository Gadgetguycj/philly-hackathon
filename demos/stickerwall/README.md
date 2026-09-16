# The Sticker Wall

This FastAPI app generates die-cut sticker images with RunPod Flux and keeps a shared wall in SQLite.

## Run locally

```sh
cp .env.example .env
# Add RUNPOD_API_KEY to .env.
docker compose up --build
curl http://127.0.0.1:8000/health
```

The default model is Flux Schnell. Set `FLUX_MODEL=black-forest-labs-flux-1-dev` to use Flux Dev.

## Deploy

Before deploying with a bind mount, create the host directory with:

```sh
install -d -o 1000 -g 1000 /data/stickerwall
```

Deploying without a mount also works. Data then lives inside the container and is lost when the container is removed.

## GalaxyGate create_app body

Replace the uppercase values before calling `create_app` on the target instance.

```json
{
  "name": "stickerwall",
  "image": "ghcr.io/galaxygate/philly-hackathon-stickerwall:latest",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "RUNPOD_API_KEY",
    "FLUX_MODEL": "black-forest-labs-flux-1-schnell"
  },
  "mounts": [{"host_path": "/data/stickerwall", "container_path": "/data", "read_only": false}],
  "domain": "TEAM_NAME-stickers.galaxygate.app"
}
```
