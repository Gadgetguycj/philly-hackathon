#!/usr/bin/env bash
# Create (or reuse) the Bookbuilder serverless endpoint on RunPod: gpt-oss-20b on vLLM,
# 48 GB tier, scale to zero, ten minute warm hold. Prints the endpoint id.
# Usage: RUNPOD_API_KEY=... scripts/create-endpoint.sh [name]
set -euo pipefail
NAME="${1:-bookbuilder-gpt-oss-20b}"
: "${RUNPOD_API_KEY:?set RUNPOD_API_KEY}"
API=https://rest.runpod.io/v1
AUTH="Authorization: Bearer $RUNPOD_API_KEY"

find_by_name() { python3 -c '
import json,sys
d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get("items") or []
print(next((e["id"] for e in items if e.get("name")==sys.argv[1]),""))' "$1"; }

existing=$(curl -sf "$API/endpoints" -H "$AUTH" | find_by_name "$NAME")
if [ -n "$existing" ]; then echo "$existing"; exit 0; fi

# The endpoint API needs a template that carries the image and its environment.
template=$(curl -sf "$API/templates" -H "$AUTH" | find_by_name "$NAME")
if [ -z "$template" ]; then
  template=$(curl -sf -X POST "$API/templates" -H "$AUTH" -H "Content-Type: application/json" -d "$(python3 -c '
import json,sys
print(json.dumps({"name":sys.argv[1],"imageName":"runpod/worker-v1-vllm:v2.27.0","containerDiskInGb":40,"isServerless":True,
  "env":{"MODEL_NAME":"openai/gpt-oss-20b","MAX_MODEL_LEN":"16384","GPU_MEMORY_UTILIZATION":"0.92"}}))' "$NAME")" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
fi

curl -sf -X POST "$API/endpoints" -H "$AUTH" -H "Content-Type: application/json" -d "$(python3 -c '
import json,sys
print(json.dumps({"name":sys.argv[1],"templateId":sys.argv[2],"computeType":"GPU","gpuCount":1,
  "gpuTypeIds":["NVIDIA RTX A6000","NVIDIA A40","NVIDIA RTX 6000 Ada Generation","NVIDIA L40S","NVIDIA L40"],
  "workersMin":0,"workersMax":1,"workersStandby":0,"idleTimeout":600,"flashboot":True,"executionTimeoutMs":900000}))' "$NAME" "$template")" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
