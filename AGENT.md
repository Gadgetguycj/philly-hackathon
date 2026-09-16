# Server setup instructions for the coding agent

You are setting up a hackathon server on GalaxyGate and a GPU endpoint on RunPod for the user, then deploying the demo app that connects them. The user's message contains two values: TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for everything on the panel, the RunPod MCP tools for everything on RunPod, and your shell only for `curl`. Nothing here needs SSH. Do not ask the user questions. Follow the stop rules in each step.

Secret rule. You send RUNPOD_API_KEY only inside the `environment` object of a `create_app` or `update_app` call, and you never write it into a shell command, a file, or a message of your own. Tool results from `get_app` contain the environment in plain text; never quote such a result except its `state`, `locked` and `container_id` fields, and when you need the current environment for `update_app`, copy it from the `get_app` result into the call without showing it. An `update_app` environment replaces the whole set, so send every variable the app already has plus the key. Tell the user at the end that the key is visible in this chat's tool calls.

Shell rule. The only shell commands here are `curl`. On Windows PowerShell write `curl.exe` instead of `curl`. Pauses between polls are `sleep N` in bash and `Start-Sleep -Seconds N` in PowerShell. If your tool has no shell, use its own URL-fetch ability for the GET checks and tell the user the one POST check in step 10 was skipped.

Waiting rule. Every wait below is a fixed number of polls with a fixed pause. Count the polls. Never poll past the count.

List rule. Every GalaxyGate list tool returns a paged envelope; read rows from `items`. When a step names a `q` filter, pass it so the row you need is on the first page.

## 0. Validate the inputs

- TEAM_NAME must be 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. If it does not match, or still reads `yourteam`, stop and tell the user the rule.
- RUNPOD_API_KEY must start with `rpa_` and must not be the placeholder text. If it is not, stop and tell the user where to create one: RunPod console, Settings, API Keys.
- Set `INSTANCE_NAME=hack-TEAM_NAME`, `APP_NAME=sketch`, `ENDPOINT_NAME=hackathon-vl`.

## 1. Pick the workspace

Call `list_workspaces`. If `items` holds exactly one workspace, use its `id` as `WORKSPACE_ID`. If zero or several, stop and show the user the names; create nothing.

## 2. Check for a previous run

Call `list_instances` with `workspace_id` and `q` set to `INSTANCE_NAME`. If a row's `name` equals `INSTANCE_NAME`, record its `id` as `INSTANCE_ID` and skip to step 4. Never create a second server with the same name.

## 3. Create the server

- Call `list_plans` with `q` set to `Lightning-8G`. Use the row whose `name` is exactly `Lightning-8G`; record its `id` as `PLAN_ID`. If there is none, stop and report.
- Call `list_images` with `workspace_id`, kind `TEMPLATE`, official true, and `q` set to `Ubuntu 24.04`. Use the row whose `name` is `Ubuntu 24.04`; record its `id` as `IMAGE_ID`. If the call is denied with a 403 that mentions permission or scope, use `IMAGE_ID=1455765925817413632`: the organizers created an Ubuntu 24.04 server from this exact id during event preparation and re-check it on the morning of the event. Any other failure, or an empty list: stop and report.
- Call `create_instance` with `workspace_id`, name `INSTANCE_NAME`, `plan_id`, `image_id`, region `NA_01`, start true, ipv4 true, ipv6 true. Record the returned instance `id` as `INSTANCE_ID`.
- If the call errors after a timeout, call `list_instances` with `q` set to `INSTANCE_NAME` before doing anything else. If the instance exists, use it. Only if it does not exist may you call `create_instance` once more.

## 4. Wait for the server

Poll `get_instance` with `instance_id` at most 40 times, pausing 15 seconds between polls, until `state` is `AVAILABLE` and `online` is true. If `state` becomes `FAILED`, stop and report. After 40 polls, stop and report the last state.

## 5. Prepare the server and build the demo image on it

Call `run_script` with `workspace_id`, `instance_id`, name `hackathon-prepare`, and this script, passed exactly as written:

```
set -e
timeout 300 cloud-init status --wait || true
export DEBIAN_FRONTEND=noninteractive
command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
command -v git >/dev/null 2>&1 && command -v socat >/dev/null 2>&1 || { apt-get update -q && apt-get install -y -q git socat; }
systemctl enable --now docker
install -d -o 1000 -g 1000 /data/sketch /data/sketch-2
docker inspect registry >/dev/null 2>&1 || docker run -d --restart always --name registry -p 127.0.0.1:5000:5000 registry:2
rm -rf /opt/build && git clone --depth 1 https://github.com/GalaxyGate/philly-hackathon /opt/build
docker build -t 127.0.0.1:5000/sketch:base /opt/build/demos/sketch
docker push 127.0.0.1:5000/sketch:base
```

It installs Docker the same way the panel does, so the panel skips its own install later, and it builds the demo image into a registry that listens only on the server's loopback address. It returns a workflow id. Poll `get_workflow` with `workspace_id` and that id at most 60 times, pausing 15 seconds, until `state` is `COMPLETED`. A script that fails ends the workflow in `FAILED`. If it is `FAILED`, run it once more with the name `hackathon-prepare-2`; if that also fails, or the workflow is still running after 60 polls, stop and report the workflow state and the `data.message` field.

## 6. Create the GPU endpoint on RunPod

Using the RunPod MCP tools:

1. Call the endpoint list tool (`list-endpoints`). If an endpoint named `ENDPOINT_NAME` exists, record its id as `ENDPOINT_ID` and skip to step 7.
2. Otherwise call the endpoint creation tool (`create-endpoint`) with `name` `ENDPOINT_NAME`, `imageName` `runpod/worker-v1-vllm:v2.27.0`, `gpuPoolIds` `["ADA_24"]`, `gpuCount` 1, `containerDiskInGb` 40, `workersMin` 0, `workersMax` 1, `idleTimeout` 60, `flashboot` `FLASHBOOT`, `executionTimeoutMs` 900000, and `env` `{"MODEL_NAME":"Qwen/Qwen2.5-VL-7B-Instruct","MAX_MODEL_LEN":"8192"}`. Record the returned id as `ENDPOINT_ID`.
3. If creation fails because of balance or credit, tell the user their RunPod credit is not applied and stop. Any other failure: show the error and stop.

The endpoint costs nothing while idle. Its first request downloads the model and can take several minutes; step 10 allows for that.

## 7. Pick the public name

Set `SUBDOMAIN=TEAM_NAME` and `APP_DOMAIN=SUBDOMAIN.galaxygate.app`. Call `panel_request` with method `POST`, path `/v1/apps/domains`, body `{"domain":"APP_DOMAIN"}`.

- The tool returns an error whose text contains `404`: the name is free. This endpoint uses 404 to mean available. Continue.
- The tool returns success (HTTP 200, usually an empty body): the name is taken. Set `SUBDOMAIN` to TEAM_NAME followed by `-2`, then `-3`, and so on up to `-9`, rebuild `APP_DOMAIN`, and check again. Example: team `orbit` taken, try `orbit-2.galaxygate.app`.
- If `-9` is also taken, stop and ask the user for a different team name.
- Any other error: stop and report it.

## The wait procedure, used by steps 8 and 9

Given an `app_id` and its `APP_DOMAIN`: poll `get_app` at most 32 times, pausing 15 seconds between polls. From poll 4 onward, before each poll, run the health check from step 10.1 once. The wait succeeds at the first poll where `state` is `AVAILABLE` or the health check passes; the panel can report `PENDING` long after the container is serving. The wait fails if `state` becomes `FAILED`, or after poll 32 with neither condition met. The wait never deletes or creates anything.

## 8. Deploy the demo app

Call `list_instance_apps` with `instance_id`. If a row's `name` equals `APP_NAME`, record its `id` as `APP_ID`, set `APP_DOMAIN` to its `domain` and `SUBDOMAIN` to the part of that domain before `.galaxygate.app`, and run the wait procedure on it. If the wait succeeds, skip to step 10, whatever the panel state says. If it fails, go to the recovery in step 9.

Otherwise call `create_app` with `instance_id` and this body. Substitute the real values; the key value is the RUNPOD_API_KEY from the user's message, not the text of this template.

```json
{
  "name": "APP_NAME",
  "image": "127.0.0.1:5000/sketch:base",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "<the key from the user's message>",
    "RUNPOD_ENDPOINT_ID": "ENDPOINT_ID",
    "LLM_MODEL": "Qwen/Qwen2.5-VL-7B-Instruct",
    "MAX_GENERATIONS_PER_HOUR": "20"
  },
  "mounts": [{"host_path": "/data/sketch", "container_path": "/data", "read_only": false}],
  "domain": "APP_DOMAIN"
}
```

Record the returned app `id` as `APP_ID` and the workflow id as `APP_WORKFLOW`.

## 9. Wait for the app, and recover once if the first deploy sticks

Run the wait procedure on `APP_ID`. If it succeeds, go to step 10.

Recovery, at most once in this whole run:

1. Call `get_workflow` with `workspace_id` and `APP_WORKFLOW`. Keep its `state` and, from `progress.children`, the `name` and `status` of every child that is not `COMPLETED`, for the report.
2. Call `get_app` with `app_id`. If its `locked` field is set, go to 3. Otherwise call `delete_app` with `app_id`. Deletion is asynchronous: poll `get_app` with the old `app_id` at most 12 times, pausing 10 seconds, until it returns an error whose text contains `404`. Only then repeat step 8's `create_app` with the same values, and record the returned app `id` as `APP_ID` and workflow id as `APP_WORKFLOW`, replacing the old values. If the app is still there after 12 polls, go to 3.
3. If the app was locked, or `delete_app` returned an error whose text contains `409`, leave that app alone. Set `APP_NAME=sketch-2`, use `host_port` 8001 with `container_port` 8000, use `host_path` `/data/sketch-2`, set `SUBDOMAIN` to the current value with `-2` appended, rebuild `APP_DOMAIN=SUBDOMAIN.galaxygate.app`, check that exact name with the `panel_request` call from step 7 without re-running step 7's first sentence, and if it is taken append `-3` instead and check once more; then call `create_app` with those values. Record the new `APP_ID` and `APP_WORKFLOW`, replacing the old values.
4. Run the wait procedure once more. If it fails, show the user the workflow state and the non-completed children from 1, and stop.

## 10. Prove it works

1. Health. `curl --fail --silent --show-error --connect-timeout 10 --max-time 30 https://APP_DOMAIN/health` passes when it prints JSON containing `"status":"ok"`, `"runpod_key_set":true` and `"model_configured":true`. When this step is reached outside the wait procedure, try it at most 12 times, pausing 15 seconds, and after 12 failures call `get_app_logs` with `app_id` and tail 100; if that errors, call `get_app` and report its `state`, `locked` and `container_id` instead. Show the user whichever you got, with the key redacted, and stop.
2. Real generation. Download the sample sketch: `curl --fail --silent --show-error -o sample-sketch.jpg https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/demos/sketch/samples/sketch.jpg`. Then `curl --silent --show-error --max-time 900 -w '\nHTTP:%{http_code}\n' -F "image=@sample-sketch.jpg" -F "notes=A landing page with a header, a hero, three cards, and a footer." https://APP_DOMAIN/api/sketch`. Expected: JSON with `"url"` and `HTTP:200`. A `200` whose JSON has `detail` and no `url` is a failure; show the `detail` text. Then `curl --fail --silent --show-error --max-time 30 https://APP_DOMAIN<url>` must return HTML. If the response mentions 401, tell the user the key was not substituted or is wrong, and stop. If it mentions 402, tell the user their RunPod credit is exhausted, and stop. If it mentions an hourly limit, report the cap and stop. Any other error: show its text redacted and stop.
3. Tell the user the URL to open on their phone and laptop. Do not open it yourself.

## 11. Record and report

Write `HACKATHON.md` in the user's project containing, with no secrets:

- workspace id, instance id, instance name
- app id, app name, image, app URL `https://APP_DOMAIN`
- RunPod endpoint name and id
- the workflow ids from steps 5, 8 and 9, and whether the panel still showed the app as deploying when the health check passed
- the line: "RUNPOD_API_KEY is set in the app environment on the server, and the create_app call that set it is in this chat history. The panel shows environment values in plain text to workspace members. Revoke this key in the RunPod console after the event."

Then tell the user: the app URL, that the health check and one real generation succeeded, the endpoint id, and that HACKATHON.md holds the ids they need for the Devpost submission.

## 12. Redeploy after the user changes code

The panel always pulls an app's image from a registry when it deploys, so the new image goes into a registry that runs on the server itself and listens only on its loopback address. Everything below runs on the server through `run_script`; nothing needs SSH. First read `HACKATHON.md` for `INSTANCE_ID`, `WORKSPACE_ID`, `APP_NAME`, `APP_ID` and `APP_DOMAIN`; if it is missing, call `list_instances` with `q` set to the instance name, then `list_instance_apps`, and confirm the app's domain with the user before touching anything. The user's code must be in a public GitHub repository; ask for the repository URL `REPO_URL` and the folder inside it that holds the `Dockerfile`, `APP_DIR` (for example `demos/sketch`). Set `TAG` to the current UTC date and time as digits.

1. Call `run_script` with name `hackathon-build` and this script, values substituted, then poll its workflow as in step 5 but at most 60 times pausing 10 seconds:

```
docker start registry 2>/dev/null || docker run -d --restart unless-stopped -p 127.0.0.1:5000:5000 --name registry registry:2
rm -rf /opt/build && git clone --depth 1 REPO_URL /opt/build
docker build -t 127.0.0.1:5000/APP_NAME:TAG /opt/build/APP_DIR
docker push 127.0.0.1:5000/APP_NAME:TAG
```

If the workflow ends `FAILED`, tell the user the build failed on the server and stop.

2. Call `update_app` with `app_id` and body `{"image":"127.0.0.1:5000/APP_NAME:TAG"}`.
3. Call `run_script` with name `hackathon-verify` and this script, then poll its workflow at most 30 times pausing 10 seconds:

```
for i in $(seq 1 48); do [ "$(docker inspect -f '{{.Config.Image}}' APP_NAME 2>/dev/null)" = "127.0.0.1:5000/APP_NAME:TAG" ] && exit 0; sleep 5; done; exit 1
```

`COMPLETED` means the new image is running. `FAILED` means the panel did not swap the container within four minutes; tell the user, leave the app as it is, and stop.

4. Request `https://APP_DOMAIN/` with `curl --silent --output /dev/null --max-time 20 -w '%{http_code}'` until any code below 500 comes back, at most 12 times pausing 10 seconds. If the app still serves `/health`, run step 10.1. A route the user removed is not a failure.

## Other later requests

- Change the environment: read the current environment with `get_app`, then `update_app` with `app_id` and the full `environment` object (every existing variable, changed or added as the user asked, copied without showing it), then the wait procedure, then step 10.1.
- Restart: `app_restart` with `app_id`. Logs: `get_app_logs` with `app_id`, redact the key before showing.
- Run a command on the server: `run_script` with a name and the script, then poll its workflow. Output is not returned; write results to a file the app serves if you need to read them.
- Never delete or power off an instance you did not create in this session. Never call `create_instance` when an instance named `INSTANCE_NAME` exists. Never run the step 9 recovery outside step 9.
