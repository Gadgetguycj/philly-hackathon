# Server setup instructions for the coding agent

You are setting up a hackathon server on GalaxyGate for the user. The user's message contains two values: TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for everything on the panel and your shell for everything else. Do not ask the user questions. Follow the stop rules in each step.

Secret rule. RUNPOD_API_KEY appears exactly once in your work: inside the `environment` object of the `create_app` call in step 8. Never repeat it anywhere else: not in a shell command, not in a file you write, not in a log or error you quote. Assume the create_app call is visible in the chat history, and say so to the user at the end.

Shell rule. Commands below are written for bash. On Windows, if Git for Windows is installed run each command through `bash -lc '...'`. If it is not, use PowerShell equivalents: `New-Item -ItemType Directory -Force` for `mkdir -p`, skip `chmod`, `Start-Sleep -Seconds N` for `sleep N`, `curl.exe` instead of `curl`, one command per line instead of `&&`, and write files with `Out-File -Encoding ascii`.

Waiting rule. Every wait below is a fixed number of polls with a fixed pause. Count the polls. Never poll past the count.

## 0. Validate the inputs

- TEAM_NAME must be 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. If it does not match, or still reads `yourteam`, stop and tell the user the rule.
- RUNPOD_API_KEY must start with `rpa_` and must not be the placeholder text. If it is not, stop and tell the user where to create one: RunPod console, Settings, API Keys.
- Set `INSTANCE_NAME=hack-TEAM_NAME` and `APP_NAME=roast`.

## 1. Pick the workspace

Call `list_workspaces`. If exactly one workspace is returned, use its `id` as `WORKSPACE_ID`. If there are zero or several, stop and show the user the names; create nothing.

## 2. Check for a previous run

Call `list_instances` with `workspace_id` and `q` set to `INSTANCE_NAME`. If an instance with exactly that name exists, reuse it: record its `id` as `INSTANCE_ID` and skip to step 5. Never create a second server with the same name.

## 3. SSH key

- Create `~/.ssh` if missing (bash: `mkdir -p ~/.ssh && chmod 700 ~/.ssh`).
- If `~/.ssh/galaxygate_hackathon` does not exist, run `ssh-keygen -t ed25519 -N "" -f ~/.ssh/galaxygate_hackathon -C hackathon`. If it exists but the `.pub` file is missing, run `ssh-keygen -y -f ~/.ssh/galaxygate_hackathon` and save the single output line to `~/.ssh/galaxygate_hackathon.pub` as plain ASCII.
- Read the public key text. Call `list_ssh_keys` with `workspace_id`. If a key whose `public_key` equals this text exists, skip. Otherwise call `upload_ssh_key` with `workspace_id`, name `hackathon-` followed by the first 8 characters of TEAM_NAME and 4 random digits, and the public key text. Call `list_ssh_keys` again and confirm the key is present before continuing.

## 4. Create the server

- Call `list_plans`. Use the plan named exactly `Lightning-8G`; record its `id` as `PLAN_ID`. If it is missing, stop and report.
- Call `list_images` with `workspace_id` and kind `TEMPLATE`. Use the official image named `Ubuntu 24.04`; record its `id` as `IMAGE_ID`. If the call is denied with a 403, use `IMAGE_ID=1455765925817413632`; the organizers created a server from this id during event preparation and it provisioned Ubuntu 24.04. Any other failure: stop and report.
- Call `create_instance` with `workspace_id`, name `INSTANCE_NAME`, `plan_id`, `image_id`, region `NA_01`, start true, ipv4 true, ipv6 true. Record the returned instance `id` as `INSTANCE_ID` and the workflow id as `PROVISION_WORKFLOW`.
- If the call errors after a timeout, call `list_instances` with `q` set to `INSTANCE_NAME` before doing anything else. If it exists, use it. Only if it does not exist may you call `create_instance` once more.

## 5. Wait for the server

- Poll `get_instance` with `instance_id` at most 40 times, pausing 15 seconds between polls, until `state` is `AVAILABLE` and `online` is true. If `state` becomes `FAILED`, stop and report. After 40 polls, stop and report the last state.
- Call `list_instance_ips` with `instance_id`. Record the address whose range type is `IPv4` as `IPV4`. If there is none, stop and report.

## 6. Confirm SSH and first boot

Run this at most 15 times, pausing 20 seconds between attempts, until it succeeds:

```
ssh -n -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i ~/.ssh/galaxygate_hackathon root@IPV4 'timeout 300 cloud-init status --wait && install -d -o 1000 -g 1000 /data/roast && echo READY'
```

Success means the output ends with `READY`. After 15 failed attempts, run the same ssh command with `cloud-init status --long` as the remote command, show the user the output, and stop. Do not deploy the app on a server that did not print `READY`.

## 7. Pick the public name

Set `SUBDOMAIN=TEAM_NAME` and `APP_DOMAIN=SUBDOMAIN.galaxygate.app`. Call `panel_request` with method `POST`, path `/v1/apps/domains`, body `{"domain":"APP_DOMAIN"}`.

- The tool returns an error whose text contains `404`: the name is free. This endpoint uses 404 to mean available. Continue.
- The tool returns success (an HTTP 200, usually with an empty body): the name is taken. Set `SUBDOMAIN` to TEAM_NAME followed by `-2`, then `-3`, and so on up to `-9`, rebuild `APP_DOMAIN`, and check again. Example: team `orbit` taken, try `orbit-2.galaxygate.app`.
- If `-9` is also taken, stop and ask the user for a different team name.
- Any other error: stop and report it.

## 8. Deploy the demo app

Call `list_instance_apps` with `instance_id`. If an app named `APP_NAME` exists with `state` `AVAILABLE`, record its `id` as `APP_ID` and skip to step 10. If it exists in any other state, treat it as the stuck first deploy and go to step 9's recovery.

Otherwise call `create_app` with `instance_id` and this body. Substitute the real values; the key value is the RUNPOD_API_KEY from the user's message, not the text of this template.

```json
{
  "name": "roast",
  "image": "ghcr.io/galaxygate/philly-hackathon-roast:latest",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "<the key from the user's message>",
    "LLM_BASE_URL": "https://api.runpod.ai/v2/qwen3-32b-awq/openai/v1",
    "LLM_MODEL": "Qwen/Qwen3-32B-AWQ",
    "MAX_GENERATIONS_PER_HOUR": "30"
  },
  "mounts": [{"host_path": "/data/roast", "container_path": "/data", "read_only": false}],
  "domain": "APP_DOMAIN"
}
```

Record the returned app `id` as `APP_ID` and the workflow id as `APP_WORKFLOW`.

## 9. Wait for the app, and recover if the first deploy sticks

Poll `get_app` with `app_id` at most 16 times, pausing 15 seconds between polls.

- `state` `AVAILABLE` at any poll: go to step 10.
- `state` `FAILED` at any poll: go to the recovery below.
- On poll 12, if `state` is still `PENDING`, run the health check from step 10.1 once. If it returns the expected JSON, go to step 10 and later record in HACKATHON.md that the panel still showed the app as deploying. If it does not, continue polling.
- After poll 16 with no `AVAILABLE` and no passing health check: go to the recovery below.

Recovery, at most once:

1. Call `get_workflow` with `workspace_id` and `APP_WORKFLOW`. Keep its `message` for the report.
2. Call `delete_app` with `app_id`. If it succeeds, pause 30 seconds and repeat step 8 with the same values.
3. If `delete_app` is refused because the app is locked, leave that app alone. Set `APP_NAME=roast-2`, use `host_port` 8001 in the body, set `SUBDOMAIN` to the current value with `-2` appended, check it as in step 7, and repeat step 8. Record the new `APP_ID` and `APP_WORKFLOW`.
4. Poll as above once more. If it still does not pass, show the user the workflow message and stop.

## 10. Prove it works

1. Health. Run `curl --fail --silent --show-error --connect-timeout 10 --max-time 30 https://APP_DOMAIN/health` at most 12 times, pausing 15 seconds between attempts, until it prints JSON containing `"status":"ok"`, `"runpod_key_set":true` and `"model_configured":true`. After 12 failures call `get_app_logs` with `app_id` and tail 100, show the user the log with the key redacted, and stop.
2. Real roast. Run `curl --silent --show-error --max-time 240 -N -w '\nHTTP:%{http_code}\n' -H 'Content-Type: application/json' -d '{"repo_url":"https://github.com/GalaxyGate/philly-hackathon"}' https://APP_DOMAIN/api/roast` and save the output to a temporary file. Expected: `event: token` lines, then an `event: done` line, no `event: error` line, and `HTTP:200`. If an `error` event mentions 401, tell the user the key was not substituted or is wrong, and stop. If it mentions 402, tell the user their RunPod credit is exhausted, and stop. If it mentions an hourly limit or the code is 429, report the cap and stop. Any other `error` event: show its text redacted and stop.
3. Tell the user the URL to open in their browser. Do not open it yourself.

## 11. Record and report

Write `HACKATHON.md` in the user's project containing, with no secrets:

- workspace id, instance id, instance name, IPv4
- app id, app name, image, app URL `https://APP_DOMAIN`
- provisioning and app workflow ids
- the login command: `ssh -i ~/.ssh/galaxygate_hackathon root@IPV4`
- the line: "RUNPOD_API_KEY is set in the app environment on the server, and the create_app call that set it is in this chat history. The panel shows environment values in plain text to workspace members. Revoke this key in the RunPod console after the event."

Then tell the user: the app URL, that the health check and one real roast succeeded, and that HACKATHON.md holds the ids they need for the Devpost submission.

## 12. Redeploy after the user changes code

When the user asks to redeploy an app folder (for example `demos/roast` in their fork):

1. Copy the folder to the server: `rsync -az -e "ssh -i ~/.ssh/galaxygate_hackathon -o BatchMode=yes" <folder>/ root@IPV4:/opt/APP_NAME/` (or `scp -r` if rsync is missing).
2. Build on the server over the same ssh: `docker build -t APP_NAME:local /opt/APP_NAME`. Show the user the last lines if it fails, and stop.
3. Call `update_app` with `app_id` and body `{"image":"APP_NAME:local"}`. Poll `get_app` as in step 9 (16 polls). Then repeat step 10.1 and 10.2.
4. If the panel refuses the local image tag, tell the user, and instead run the container yourself over ssh on host port 8002 with `docker run -d --restart unless-stopped -p 8002:8000 --env-file /opt/APP_NAME/.env -v /data/APP_NAME:/data APP_NAME:local`, after writing `/opt/APP_NAME/.env` on the server from the app's current environment (fetch it with `get_app`, never echo the key). Report the URL `http://IPV4:8002`.

## Other later requests

- Change environment or image: `update_app` with `app_id`, then poll `get_app` as in step 9, then repeat step 10.1.
- Restart: `app_restart` with `app_id`. Logs: `get_app_logs` with `app_id`, redact the key before showing.
- Never delete or power off an instance you did not create in this session. Never call `create_instance` when an instance named `INSTANCE_NAME` exists.
