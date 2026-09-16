# Server setup instructions for the coding agent

You are setting up a hackathon server on GalaxyGate and a GPU endpoint on RunPod for the user, then deploying the demo app that connects them. The user's message contains two values: TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for everything on the panel, the RunPod MCP tools for everything on RunPod, and your shell only for `curl`. Nothing here needs SSH. Do not ask the user questions except where a step says to. Follow the stop rules in each step.

Secret rule. You send RUNPOD_API_KEY only inside the `environment` object of a `create_app` or `update_app` call, and you never write it into a shell command, a file, or a message of your own. Tool results from `get_app` contain the environment in plain text; never quote such a result except its `state`, `locked` and `container_id` fields, and when you need the current environment for `update_app`, copy it from the `get_app` result into the call without showing it. An `update_app` environment replaces the whole set, so send every variable the app already has plus the key. Tell the user at the end that the key is visible in this chat's tool calls.

Shell rule. The only shell commands here are `curl`. On Windows PowerShell write `curl.exe` instead of `curl`. Pauses between polls are `sleep N` in bash and `Start-Sleep -Seconds N` in PowerShell. Every tool named in the guide can run `curl`; if yours asks the user to approve each command, tell the user to approve them. Never skip the generation check in step 10; if you truly cannot run it, say so in plain words and tell the user to open the app on their phone, photograph any sketch, and press Build the page before they consider setup done.

Id rule. Every GalaxyGate resource id is a string of digits, for example `"1549623084129976320"`. Pass ids as strings, never as numbers, and copy them exactly. A workflow id is the exception: it is a UUID with hyphens, for example `"9f2c1d7a-4b83-4c1e-9a55-6d0f3b8e27c4"`; pass it back exactly as it came. `create_instance` and `create_app` return `{"workflow": {...}, "resource": {...}}`; the new object's id is `resource.id`, and `resource.parent.id` is the workspace, not what you want.

Waiting rule. Every wait below is a fixed number of polls with a fixed pause. Count the polls. Never poll past the count. When a poll budget runs out with a workflow still pending or running, treat that as `FAILED` for that step.

List rule. Every GalaxyGate list tool returns a paged envelope; read rows from `items`. When a step names a `q` filter, pass it so the row you need is on the first page.

Server script rule. The panel runs a script on the server through a recipe and waits about 50 seconds for it. A script that takes longer is reported as `FAILED` even though it keeps running. So every script below either finishes in under 40 seconds or starts its real work in the background and writes a marker file when done. Scripts are passed exactly as written; the web firewall in front of the panel rejects some shell patterns, and these pass. The panel never returns a script's output. A script that exits non-zero ends its workflow in `FAILED`; one that exits zero ends in `COMPLETED`.

Recipes. `create_recipe` takes `workspace_id`, `name`, `category` `AUTOMATION`, `description`, and `commands` `[{"path":"/bin/sh","args":["-c","<script>"]}]`, and returns the recipe with its `id`. `install_recipe` takes `instance_id`, `recipe_id`, and `fields` `{}`, and returns a workflow whose `id` you poll with `get_workflow` and `workspace_id`; its `duration` is whole seconds since the workflow started. If `install_recipe` itself returns an error mentioning `Instance is not available` or `must be online`, the panel is holding the server for another operation; pause 20 seconds and call it again, at most 6 times, before treating that as a failure. Recipe names must be unique, so set `RUN` to the current UTC time as six digits (`HHMMSS`) once at the start and use it in every recipe name below.

## 0. Validate the inputs

- TEAM_NAME must be 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. If it does not match, or still reads `yourteam`, stop and tell the user the rule.
- RUNPOD_API_KEY must start with `rpa_` and must not be the placeholder text `rpa_paste-your-key-here`. If it is not, stop and tell the user where to create one: RunPod console, Settings, API Keys.
- Set `INSTANCE_NAME=hack-TEAM_NAME`, `APP_NAME=sketch`, `ENDPOINT_NAME=hackathon-vl`, `MODEL=Qwen/Qwen2.5-VL-7B-Instruct`, and `RUN` as above.

## 1. Pick the workspace

Call `list_workspaces`. If `items` holds exactly one workspace, use its `id` as `WORKSPACE_ID`. If zero or several, stop and show the user the names; create nothing.

## 2. Check for a previous run

Call `list_instances` with `workspace_id` and `q` set to `INSTANCE_NAME`. If a row's `name` equals `INSTANCE_NAME`, record its `id` as `INSTANCE_ID` and skip to step 4. Never create a second server with the same name.

## 3. Create the server

- Call `list_plans` with `q` set to `Lightning-8G`. Use the row whose `name` is exactly `Lightning-8G`; record its `id` as `PLAN_ID`. If there is none, stop and report.
- Call `list_images` with `workspace_id`, kind `TEMPLATE`, official true, and `q` set to `Ubuntu 24.04`. Use the row whose `name` is `Ubuntu 24.04`; record its `id` as `IMAGE_ID`. If the call is denied with a 403 that mentions permission or scope, use `IMAGE_ID=1455765925817413632`, the id of that image when these instructions were written, and if `create_instance` then rejects it, stop and tell the user to bring "image id rejected" to the GalaxyGate table. Any other failure, or an empty list: stop and report.
- Call `create_instance` with `workspace_id`, name `INSTANCE_NAME`, `plan_id`, `image_id`, region `NA_01`, start true, ipv4 true, ipv6 true. Record `resource.id` as `INSTANCE_ID`.
- If the call errors after a timeout, call `list_instances` with `q` set to `INSTANCE_NAME` before doing anything else. If the instance exists, use it. Only if it does not exist may you call `create_instance` once more.

## 4. Wait for the server to boot

1. Poll `get_instance` with `instance_id` at most 40 times, pausing 15 seconds between polls, until `state` is `AVAILABLE`, `online` is true, and `locked` is null or absent. The panel sets `AVAILABLE` and powers the server on before it releases its creation lock, and a recipe cannot be installed while the lock is held. If `state` becomes `FAILED`, stop and report. After 40 polls, stop and report the last state.
2. Call `create_recipe` with name `hk-boot-RUN`, description `Boot check`, and the command script `test -f /var/lib/cloud/instance/boot-finished`. Record its `id` as `BOOT_RECIPE`.
3. Call `install_recipe` with `instance_id`, `BOOT_RECIPE`, fields `{}`; poll its workflow at most 6 times pausing 10 seconds. `COMPLETED` means the server finished booting; continue. `FAILED` means not yet: pause 15 seconds and install it again. Do this at most 12 times in total. If none completes, stop and tell the user the server never finished its first boot.

## 5. Prepare the server and build the demo image on it

1. Call `create_recipe` with name `hk-prep-RUN`, description `Prepare and build`, and this exact command script. It writes the real work to a file, starts it in the background, and returns at once. The work installs Docker and socat the way the panel's own integration does, so the panel finds them present later, starts a registry that listens only on the server's loopback address, clones the organizers' repository, builds the demo image into that registry, and pulls it back once to prove the pull works.

```
cat > /opt/hackathon-prepare.sh <<'EOF2'
set -e
export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null 2>&1; then curl -fsSL https://get.docker.com -o /tmp/get-docker.sh; sh /tmp/get-docker.sh; fi
if ! command -v git >/dev/null 2>&1 || ! command -v socat >/dev/null 2>&1; then apt-get -o DPkg::Lock::Timeout=300 update -q; apt-get -o DPkg::Lock::Timeout=300 install -y -q git socat; fi
systemctl enable --now docker
install -d -o 1000 -g 1000 /data/sketch /data/sketch-2
docker start registry >/dev/null 2>&1 || docker run -d --restart always --name registry -p 127.0.0.1:5000:5000 registry:2
rm -rf /opt/build
git clone --depth 1 https://github.com/GalaxyGate/philly-hackathon /opt/build
docker build -t 127.0.0.1:5000/sketch:base /opt/build/demos/sketch
docker push 127.0.0.1:5000/sketch:base
docker image rm 127.0.0.1:5000/sketch:base
docker pull 127.0.0.1:5000/sketch:base
EOF2
mkdir /opt/hackathon-prepare.lock 2>/dev/null || exit 0
rm -f /opt/hackathon-prepare.done /opt/hackathon-prepare.failed
nohup sh -c 'if sh /opt/hackathon-prepare.sh > /var/log/hackathon-prepare.log 2>&1; then touch /opt/hackathon-prepare.done; else touch /opt/hackathon-prepare.failed; fi; rmdir /opt/hackathon-prepare.lock' > /dev/null 2>&1 &
```

2. Call `install_recipe` with `instance_id`, that recipe's `id`, fields `{}`; record the returned workflow's `id` as `PREPARE_WORKFLOW`; poll it at most 6 times pausing 10 seconds until `COMPLETED`. If it is `FAILED`, install it once more; the script exits at once if the first run is still going or has finished, so this is safe. If that also fails, stop and report the workflow state.
3. Call `create_recipe` with name `hk-check-RUN`, description `Prepare check`, and this exact command script. Record its `id` as `CHECK_RECIPE`.

```
for i in $(seq 1 35); do test -f /opt/hackathon-prepare.done && exit 0; test -f /opt/hackathon-prepare.failed && exit 1; sleep 1; done; exit 1
```

4. Call `install_recipe` with `instance_id`, `CHECK_RECIPE`, fields `{}`; poll its workflow at most 8 times pausing 10 seconds until `state` is `COMPLETED` or `FAILED`. Read the result:
   - `COMPLETED`: the build is done. Go to step 6.
   - `FAILED` with `duration` 25 seconds or more, or 25 seconds or more on your own clock between the `install_recipe` call and the poll that returned `FAILED`: the build is still running. Pause 20 seconds and install `CHECK_RECIPE` again. Do this at most 24 times in total.
   - `FAILED` with `duration` under 25 seconds by both measures: the build failed. Stop and tell the user the server could not build the demo, that the log is `/var/log/hackathon-prepare.log` on the server, and that the GalaxyGate table can read it by opening the server's console from the panel. Give them `INSTANCE_ID` in the same message.
   - After every fourth check that came back as still running, install the liveness recipe below once. `COMPLETED` means the build wrote to its log in the last five minutes; carry on. `FAILED` means the build never started or died without a marker: install the unlock recipe below once, then install the prepare recipe from item 1 again, and continue the checks. Do this relaunch at most once in the whole run.
   - After 24 checks with no `COMPLETED`, stop and tell the user the build did not finish in time.

5. Liveness and unlock recipes, created only when item 4 needs them. `hk-alive-RUN`, description `Build liveness`, command script:

```
test -f /var/log/hackathon-prepare.log && find /var/log/hackathon-prepare.log -mmin -5 | grep -q .
```

`hk-unlock-RUN`, description `Build unlock`, command script:

```
rmdir /opt/hackathon-prepare.lock 2>/dev/null || true
```

## 6. Create the GPU endpoint on RunPod and start warming it

Using the RunPod MCP tools:

1. Call `list-endpoints`. If an endpoint named `ENDPOINT_NAME` exists, record its id as `ENDPOINT_ID` and go to 3.
2. Otherwise call `create-endpoint` with `name` `ENDPOINT_NAME`, `imageName` `runpod/worker-v1-vllm:v2.27.0`, `gpuPoolIds` `["ADA_24"]`, `gpuCount` 1, `containerDiskInGb` 80, `workersMin` 0, `workersMax` 1, `idleTimeout` 60, `flashboot` `FLASHBOOT`, `executionTimeoutMs` 900000, and `env` `{"MODEL_NAME":"Qwen/Qwen2.5-VL-7B-Instruct","MAX_MODEL_LEN":"8192"}`. Record the returned id as `ENDPOINT_ID`. If creation fails because of balance or credit, tell the user their RunPod credit is not applied and stop. Any other failure: show the error and stop.
3. Call `run-endpoint` with `endpointId` `ENDPOINT_ID` and `input` `{"openai_route":"/v1/chat/completions","openai_input":{"model":"Qwen/Qwen2.5-VL-7B-Instruct","messages":[{"role":"user","content":"Reply with the word ready."}],"max_tokens":5}}`. Record the returned job `id` as `WARM_JOB`. This makes the endpoint download the model now, while you deploy the app. Do not wait for it here.

## The wait procedure, used by steps 7 and 9

Given an `app_id` and its `APP_DOMAIN`: poll `get_app` at most 32 times, pausing 15 seconds between polls. From poll 4 onward, before each poll, run the health check from step 10.1 once, without its stop path. The wait succeeds at the first poll where the health check passes. The panel sets `state` to `AVAILABLE` as soon as the container starts, before the process inside it is listening, and on some servers it keeps showing `PENDING` and `locked` `Deploying` long after the app is serving; the health check is the only real gate. The wait fails if `state` becomes `FAILED`, or after poll 32 with no passing health check. The wait never deletes or creates anything.

## 7. Find an existing app, or pick the public name

Call `list_instance_apps` with `instance_id`. If a row's `name` equals `APP_NAME` or `sketch-2`, this server already carries the demo from an earlier run: set `APP_NAME` to that row's `name`, record its `id` as `APP_ID`, leave `APP_WORKFLOW` unset, set `APP_DOMAIN` to its `domain` and `SUBDOMAIN` to the part of that domain before `.galaxygate.app`, and run the wait procedure on it. If two rows match, use `sketch-2`. If the wait succeeds, skip to step 10, whatever the panel state says. If it fails, go to the recovery in step 9.

Only when no row matches, pick the public name. Set `SUBDOMAIN=TEAM_NAME` and `APP_DOMAIN=SUBDOMAIN.galaxygate.app`. Call `panel_request` with method `POST`, path `/v1/apps/domains`, body `{"domain":"APP_DOMAIN"}`.

- The tool returns an error whose text is `panel API 404` or otherwise contains `404` with no HTML page and no `No static resource` text: the name is free. This endpoint uses 404 to mean available. Continue to step 8.
- The tool returns success (HTTP 200, usually an empty body): the name is taken. Set `SUBDOMAIN` to TEAM_NAME followed by `-2`, then `-3`, and so on up to `-9`, rebuild `APP_DOMAIN`, and check again. Example: team `orbit` taken, try `orbit-2.galaxygate.app`.
- If `-9` is also taken, stop and ask the user for a different team name.
- A `404` whose text contains `No static resource` or an HTML page means the route changed: stop and tell the user to bring "the domain check returned an unexpected 404" to the GalaxyGate table. Any other error: stop and report it.

## 8. Deploy the demo app

Call `create_app` with `instance_id` and this body. Substitute the real values; the key value is the RUNPOD_API_KEY from the user's message, not the text of this template.

```json
{
  "name": "APP_NAME",
  "image": "127.0.0.1:5000/sketch:base",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "<the key from the user's message>",
    "RUNPOD_ENDPOINT_ID": "ENDPOINT_ID",
    "LLM_MODEL": "Qwen/Qwen2.5-VL-7B-Instruct",
    "MAX_GENERATIONS_PER_HOUR": "20",
    "REQUEST_TIMEOUT_SECONDS": "900"
  },
  "mounts": [{"host_path": "/data/sketch", "container_path": "/data", "read_only": false}],
  "domain": "APP_DOMAIN"
}
```

Record `resource.id` as `APP_ID` and `workflow.id` as `APP_WORKFLOW`.

If `create_app` errors with a timeout or with no status code, the app may still have been created: call `list_instance_apps` with `instance_id`, and if a row named `APP_NAME` is there, record its `id` as `APP_ID`, leave `APP_WORKFLOW` unset, and go to step 9; if no row is there, call `create_app` once more. If `create_app` returns an error whose text contains `409` and mentions the name, an app called `APP_NAME` already exists elsewhere in this workspace: go to step 9 item 3. If it contains `409` and mentions the domain, go back to step 7's name check and take the next suffix. If it contains `400` and mentions a host port, go to step 9 item 3. Any other error: stop and report it.

## 9. Wait for the app, and recover once if the first deploy sticks

Run the wait procedure on `APP_ID`. If it succeeds, go to step 10. The first deploy on a new server also runs the panel's own integration workflow, so it is slower than later ones.

Recovery, at most once in this whole run:

1. If `APP_WORKFLOW` is set, call `get_workflow` with `workspace_id` and `APP_WORKFLOW`, and keep its `state` and, from `progress.children`, the `name` and `status` of every child that is not `COMPLETED`, for the report. If it is not set, record "reused app, no workflow" instead.
2. Call `get_app` with `app_id`. If `state` is `FAILED`, call `delete_app` with `app_id`. Deletion is asynchronous: poll `get_app` with the old `app_id` at most 12 times, pausing 10 seconds, until it returns an error whose text contains `404`. Then repeat step 8's `create_app` with the same values, record the new `resource.id` and `workflow.id`, and go to 4. If the app is still there after 12 polls, or `state` is not `FAILED`, or `delete_app` returned an error whose text contains `409`, go to 3.
3. Reaching this item means the first app stays where it is. Leave it. Set `APP_NAME=sketch-2`, use `host_port` 8001 with `container_port` 8000, use `host_path` `/data/sketch-2`, set `SUBDOMAIN` to `TEAM_NAME` followed by `-r2`, rebuild `APP_DOMAIN=SUBDOMAIN.galaxygate.app`, and check that exact name with the `panel_request` call from step 7 without re-running step 7's first sentence. If it is taken, use `TEAM_NAME` followed by `-r3` and check once more. Then call `create_app` with those values and record the new `resource.id` as `APP_ID` and `workflow.id` as `APP_WORKFLOW`. If this `create_app` returns an error whose text contains `409` or `400`, stop: tell the user the server already carries apps from an earlier run, list every row `list_instance_apps` returns with its `name`, `domain` and `state`, and ask them to bring that list to the GalaxyGate table.
4. Run the wait procedure once more. If it fails, show the user the workflow state and the non-completed children from 1, and stop.

## 10. Prove it works

1. Health. `curl --fail --silent --show-error --connect-timeout 10 --max-time 30 https://APP_DOMAIN/health` passes when it prints JSON containing `"status":"ok"`, `"runpod_key_set":true` and `"model_configured":true`. When this step is reached outside the wait procedure, try it at most 12 times, pausing 15 seconds, and after 12 failures call `get_app_logs` with `app_id` and tail 100; if that errors, call `get_app` and report its `state`, `locked` and `container_id` instead. Show the user whichever you got, with the key redacted, and stop.
2. Warm model. Call `get-job-status` with `endpointId` `ENDPOINT_ID` and `jobId` `WARM_JOB`. Poll at most 40 times, pausing 30 seconds, until `status` is `COMPLETED` or `FAILED`. If `COMPLETED`, read the job's `output`: an object containing `error`, or a list whose first item is such an object, means the worker ran but the model did not; show that `error.message`, tell the user the GPU endpoint could not start the model, and stop. Otherwise the model is warm. If `status` is `FAILED`, `CANCELLED` or `TIMED_OUT`, show the job's error to the user; if it mentions balance or credit, say the RunPod credit is not applied; otherwise submit the `run-endpoint` call from step 6.3 once more and poll it the same way, and stop if that also does not complete. After 40 polls, tell the user the model is still downloading and to retry the generation check later; stop.
3. Real generation. Download the sample sketch: `curl --fail --silent --show-error -o sample-sketch.jpg https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/demos/sketch/samples/sketch.jpg`. Then `curl --silent --show-error --max-time 900 -w '\nHTTP:%{http_code}\n' -F "image=@sample-sketch.jpg" -F "notes=A landing page with a header, a hero, three cards, and a footer." https://APP_DOMAIN/api/sketch`. Expected: JSON with `"url"` and `HTTP:200`. A `200` whose JSON has `detail` and no `url` is a failure; show the `detail` text. Then `curl --fail --silent --show-error --max-time 30 https://APP_DOMAIN<url>` must return HTML. If the response mentions 401, tell the user the key was not substituted or is wrong, and stop. If it mentions 402, tell the user their RunPod credit is exhausted, and stop. If it mentions an hourly limit, report the cap and stop. If it times out, or mentions 502, 503, 504, 520, 522 or 524, pause 120 seconds and run this item exactly once more; if that also fails, tell the user the page was probably built but the connection was cut while the model was writing, ask them to open `https://APP_DOMAIN/sites` and look for a new page there, and stop.
4. Tell the user the URL to open on their phone and laptop. Do not open it yourself.

## 11. Record and report

Write `HACKATHON.md` in the user's project containing, with no secrets, one value per line in exactly this form:

```
WORKSPACE_ID=...
INSTANCE_ID=...
INSTANCE_NAME=...
APP_ID=...
APP_NAME=...
APP_DOMAIN=...
APP_URL=https://...
IMAGE=127.0.0.1:5000/sketch:base
ENDPOINT_NAME=hackathon-vl
ENDPOINT_ID=...
PREPARE_WORKFLOW=...
APP_WORKFLOW=...
```

Below the values add the line: "RUNPOD_API_KEY is set in the app environment on the server, and the create_app call that set it is in this chat history. The panel shows environment values in plain text to workspace members. Revoke this key in the RunPod console after the event."

Then tell the user: the app URL, that the health check and one real generation succeeded, the endpoint id, and that `HACKATHON.md` holds the ids they need for the Devpost submission.

## 12. Redeploy after the user changes code

The panel always pulls an app's image from a registry when it deploys, so the new image goes into the registry that runs on the server itself and listens only on its loopback address. Everything below runs on the server through recipes; nothing needs SSH. First read `HACKATHON.md` for `WORKSPACE_ID`, `INSTANCE_ID`, `APP_NAME`, `APP_ID` and `APP_DOMAIN`; if it is missing, ask the user to paste it, or call `list_instances` with `q` set to the instance name, then `list_instance_apps`, and confirm the app's domain with the user before touching anything. The user's code must be in a public GitHub repository; ask for the repository URL `REPO_URL` and the folder inside it that holds the `Dockerfile`, `APP_DIR` (for example `demos/sketch`). Set `TAG` to the current UTC time as six digits and `RUN` to the same value.

1. Call `create_recipe` with name `hk-build-RUN`, description `Build`, and this exact command script with `REPO_URL`, `APP_DIR`, `APP_NAME` and `TAG` substituted, then `install_recipe` it and poll its workflow at most 6 times pausing 10 seconds until `COMPLETED`; if `FAILED`, install it once more and poll the same way, and only if that also fails stop and report the workflow state.

```
cat > /opt/hackathon-build.sh <<'EOF2'
set -e
docker start registry >/dev/null 2>&1 || docker run -d --restart always --name registry -p 127.0.0.1:5000:5000 registry:2
rm -rf /opt/build
git clone --depth 1 REPO_URL /opt/build
docker build -t 127.0.0.1:5000/APP_NAME:TAG /opt/build/APP_DIR
docker push 127.0.0.1:5000/APP_NAME:TAG
EOF2
mkdir /opt/hackathon-build.lock 2>/dev/null || exit 0
rm -f /opt/hackathon-build.done /opt/hackathon-build.failed
nohup sh -c 'if sh /opt/hackathon-build.sh > /var/log/hackathon-build.log 2>&1; then touch /opt/hackathon-build.done; else touch /opt/hackathon-build.failed; fi; rmdir /opt/hackathon-build.lock' > /dev/null 2>&1 &
```

2. Call `create_recipe` with name `hk-bcheck-RUN`, description `Build check`, and this exact command script. Install it and read its workflow the way step 5.4 does: `COMPLETED` means built; `FAILED` after 25 seconds or more means still building, so pause 20 seconds and install again, at most 24 times; `FAILED` in under 25 seconds means the build failed, so tell the user the build failed on the server, that the log is `/var/log/hackathon-build.log`, and that the GalaxyGate table can read it from the server's console in the panel, and stop. After every fourth still-building result, run the liveness and unlock recipes from step 5.5 with `hackathon-build` in place of `hackathon-prepare` in both scripts and names `hk-balive-RUN` and `hk-bunlock-RUN`; a `FAILED` liveness means relaunch item 1 once, as step 5.4 does.

```
for i in $(seq 1 35); do test -f /opt/hackathon-build.done && exit 0; test -f /opt/hackathon-build.failed && exit 1; sleep 1; done; exit 1
```

3. Call `get_app` with `app_id` and copy its `environment` object without showing it. Call `update_app` with `app_id` and body `{"image":"127.0.0.1:5000/APP_NAME:TAG","environment":<that object>}`, so the redeploy keeps every variable including the key.
4. The panel names the container after the app, so `APP_NAME` is the container name. Call `create_recipe` with name `hk-verify-RUN`, description `Verify`, and this exact command script with `APP_NAME` and `TAG` substituted. Install it and poll its workflow at most 8 times pausing 10 seconds. `COMPLETED` means the new image is running. Anything else means not yet: pause 10 seconds and install again, at most 8 times in total. If none completes, tell the user the panel did not swap the container within seven minutes, leave the app as it is, and stop.

```
for i in $(seq 1 35); do [ "$(docker inspect -f '{{.Config.Image}}' APP_NAME 2>/dev/null)" = "127.0.0.1:5000/APP_NAME:TAG" ] && exit 0; sleep 1; done; exit 1
```

5. Request `https://APP_DOMAIN/` with `curl --silent --head --max-time 20 https://APP_DOMAIN/` until the first line shows a status below 500, at most 12 times pausing 10 seconds. If all 12 fail, call `get_app_logs` with `app_id` and tail 100, show it with the key redacted, and stop. Then run step 10.1 once. If it prints `"runpod_key_set":false`, the redeploy lost the key: ask the user to paste their RunPod key again, call `get_app`, and repeat item 3 with that key added to the environment you read back. Never write the key into `HACKATHON.md` or any other file. A route the user removed is not a failure.

## Other later requests

- Change the environment: read the current environment with `get_app`, then `update_app` with `app_id` and the full `environment` object (every existing variable, changed or added as the user asked, copied without showing it), then the wait procedure, then step 10.1.
- Restart: `app_restart` with `app_id`. Logs: `get_app_logs` with `app_id`, redact the key before showing.
- Run a command on the server: `run_script` with `workspace_id`, `instance_id`, a name, and the script, then poll its workflow. Keep it under 40 seconds or use the background pattern from step 5. Output is not returned; only the exit code is, as `COMPLETED` or `FAILED`.
- Never delete or power off an instance you did not create in this session. Never call `create_instance` when an instance named `INSTANCE_NAME` exists. Never run the step 9 recovery outside step 9.
