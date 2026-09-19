#!/usr/bin/env bash
# Create (or reuse) the Bookbuilder serverless endpoint on RunPod: gpt-oss-20b on vLLM,
# 48 GB tier, scale to zero, ten minute warm hold. Prints the endpoint id.
# Usage: RUNPOD_API_KEY=... scripts/create-endpoint.sh [name]
set -euo pipefail
NAME="${1:-bookbuilder-gpt-oss-20b}"
: "${RUNPOD_API_KEY:?set RUNPOD_API_KEY}"
API=https://rest.runpod.io/v1
AUTH="Authorization: Bearer $RUNPOD_API_KEY"

existing=$(curl -sf "$API/endpoints" -H "$AUTH" | python3 -c "
import json,sys,os
d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get('endpoints') or d.get('items') or []
print(next((e['id'] for e in items if e.get('name')==os.environ['NAME']),''))" NAME="$NAME")
if [ -n "$existing" ]; then echo "$existing"; exit 0; fi

body=$(python3 - "$NAME" <<'PY'
import json,sys
print(json.dumps({
  "name": sys.argv[1],
  "imageName": "runpod/worker-v1-vllm:v2.27.0",
  "gpuTypeIds": ["NVIDIA RTX A6000", "NVIDIA A40", "NVIDIA RTX 6000 Ada Generation", "NVIDIA L40S", "NVIDIA L40"],
  "gpuCount": 1,
  "containerDiskInGb": 40,
  "workersMin": 0,
  "workersMax": 1,
  "idleTimeout": 600,
  "flashboot": "FLASHBOOT",
  "executionTimeoutMs": 900000,
  "env": {"MODEL_NAME": "openai/gpt-oss-20b", "MAX_MODEL_LEN": "16384", "GPU_MEMORY_UTILIZATION": "0.92"}
}))
PY
)
curl -sf -X POST "$API/endpoints" -H "$AUTH" -H "Content-Type: application/json" -d "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id') or d)"
