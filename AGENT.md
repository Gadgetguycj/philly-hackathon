# Server setup instructions for the coding agent

You are setting up a hackathon server on GalaxyGate for the user. The user's message contains two values: TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for everything on the panel and your shell for everything else. Do not ask the user questions. Follow the stop rules in each step. Never print RUNPOD_API_KEY anywhere: not in chat, not in files, not in commit messages. Redact it from any log or error you show.

## 0. Validate the inputs

- TEAM_NAME must be 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. If it does not match, or still reads `yourteam`, stop and tell the user the rule.
- RUNPOD_API_KEY must start with `rpa_`. If it does not, or still reads a placeholder, stop and tell the user where to create one (RunPod console, Settings, API Keys).
- Set `INSTANCE_NAME=hack-TEAM_NAME` and `APP_NAME=roast`.

## 1. Pick the workspace

Call `list_workspaces`. If exactly one workspace is returned, use its `id` as `WORKSPACE_ID`. If there are zero or several, stop and show the user the names; do not create anything.

## 2. Check for a previous run

Call `list_instances` with `workspace_id`. If an instance named `INSTANCE_NAME` already exists, reuse it: record its `id` as `INSTANCE_ID` and skip to step 5. Never create a second server with the same name.

## 3. SSH key

- Run `mkdir -p ~/.ssh && chmod 700 ~/.ssh`.
- If `~/.ssh/galaxygate_hackathon` does not exist, run `ssh-keygen -t ed25519 -N "" -f ~/.ssh/galaxygate_hackathon -C hackathon`. If it exists but `~/.ssh/galaxygate_hackathon.pub` is missing, run `ssh-keygen -y -f ~/.ssh/galaxygate_hackathon > ~/.ssh/galaxygate_hackathon.pub`.
- Read the public key text. Call `list_ssh_keys` with `workspace_id`. If a key whose `public_key` matches this text exists, skip. Otherwise call `upload_ssh_key` with `workspace_id`, name `hackathon-<first 8 characters of TEAM_NAME>-<4 random digits>`, and the public key text. Confirm it appears in a second `list_ssh_keys` call before continuing.

## 4. Create the server

- Call `list_plans`. Use the plan named exactly `Lightning-8G`; record its `id` as `PLAN_ID`. If it is missing, stop and report.
- Call `list_images` with `workspace_id` and kind `TEMPLATE`. Use the official image whose name is `Ubuntu 24.04`; record its `id` as `IMAGE_ID`. If the call is denied with a 403, use `IMAGE_ID=1455765925817413632` (the organizers verified this id is the Ubuntu 24.04 template for this event). Any other failure: stop and report.
- Call `create_instance` with `workspace_id`, name `INSTANCE_NAME`, `plan_id`, `image_id`, region `NA_01`, start true, ipv4 true, ipv6 true. Record the returned instance `id` as `INSTANCE_ID` and the workflow id as `PROVISION_WORKFLOW`.
- If the call errors after a timeout, call `list_instances` before doing anything else. If `INSTANCE_NAME` now exists, use it. Only if it does not exist may you call `create_instance` once more.

## 5. Wait for the server

- Call `get_instance` with `instance_id` every 15 seconds until `state` is `AVAILABLE` and `online` is true. Give up after 10 minutes and report the last state. If `state` becomes `FAILED`, stop and report.
- Call `list_instance_ips` with `instance_id`. Record the address whose range type is `IPv4` as `IPV4`. If there is none, stop and report.

## 6. Confirm SSH and first boot

Run this until it succeeds, retrying every 20 seconds for up to 5 minutes:

```
ssh -n -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i ~/.ssh/galaxygate_hackathon root@IPV4 'timeout 300 cloud-init status --wait && uname -a && install -d -o 1000 -g 1000 /data/roast && echo READY'
```

Success means the output ends with `READY`. If the loop times out, run the same command without `timeout 300 cloud-init status --wait &&` to collect `cloud-init status --long`, show the user, and stop. Do not deploy the app on a server that did not print `READY`.

## 7. Pick the public name

Set `APP_DOMAIN=TEAM_NAME.galaxygate.app`. Call `panel_request` with method `POST`, path `/v1/apps/domains`, body `{"domain":"APP_DOMAIN"}`.

- An error containing `404` means the name is free. Continue.
- A success response (HTTP 200) means the name is taken. Append `-2`, then `-3`, up to `-9`, and check again.
- Any other error: stop and report it.

## 8. Deploy the demo app

Call `list_instance_apps` with `instance_id`. If an app named `APP_NAME` already exists and its `state` is `AVAILABLE`, record its `id` as `APP_ID` and skip to step 10. If it exists in any other state, treat it as the stuck first deploy and follow the recovery in step 9.

Otherwise call `create_app` with `instance_id` and this body, with the real values substituted:

```json
{
  "name": "roast",
  "image": "ghcr.io/galaxygate/philly-hackathon-roast:latest",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "RUNPOD_API_KEY",
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

Call `get_app` with `app_id` every 15 seconds.

- `state` `AVAILABLE`: continue to step 10.
- `state` `FAILED`, or still `PENDING` after 4 minutes: call `get_workflow` with `workspace_id` and `APP_WORKFLOW`. If a child named `app-integrate` shows `FAILED`, or the message still says the panel is integrating Docker, this is the known first-deploy issue on a fresh server. Recover like this:
  1. Call `delete_app` with `app_id`. If it succeeds, wait 30 seconds and repeat step 8 once with the same values.
  2. If `delete_app` is refused because the app is locked, leave that app alone. Set `APP_NAME=roast-2`, use `host_port` 8001 instead of 8000 in the body, set `APP_DOMAIN` to the base name with `-2` appended (checked as in step 7), and repeat step 8 once. Record the new `APP_ID` and `APP_WORKFLOW`.
  3. If the second deploy also fails, show the user the workflow message and stop.

## 10. Prove it works

1. Run `curl --fail --silent --show-error --connect-timeout 10 --max-time 30 https://APP_DOMAIN/health`. Expected: JSON with `"status":"ok"`, `"runpod_key_set":true`, `"model_configured":true`. Retry every 15 seconds for up to 3 minutes while the public name propagates. Anything else after that: call `get_app_logs` with `app_id` and tail 100, show the user the log with any key redacted, and stop.
2. Run `curl --fail --silent --show-error --max-time 240 -N -H 'Content-Type: application/json' -d '{"repo_url":"https://github.com/GalaxyGate/philly-hackathon"}' https://APP_DOMAIN/api/roast` and save the output to a temporary file. Expected: `event: token` lines followed by an `event: done` line and no `event: error` line. If an `error` event appears, show its text to the user (redacted) and stop. A 429 with an hourly limit message means the cap was reached; report it and stop.
3. Open nothing in a browser yourself; tell the user the URL to open.

## 11. Record and report

Write `HACKATHON.md` in the user's project containing, with no secrets:

- workspace id, instance id, instance name, IPv4
- app id, app name, image, app URL `https://APP_DOMAIN`
- provisioning and app workflow ids
- the login command: `ssh -i ~/.ssh/galaxygate_hackathon root@IPV4`
- one line: "RUNPOD_API_KEY is set in the app environment on the server. The panel shows environment values in plain text to workspace members. Revoke this key in the RunPod console after the event."

Then tell the user: the app URL, that the health check and one real roast succeeded, and that HACKATHON.md holds the ids they will need for the Devpost submission.

## Later requests from the user

- Change environment or image: `update_app` with `app_id`, then poll `get_app` until `AVAILABLE`, then repeat step 10.1.
- Restart: `app_restart` with `app_id`.
- Logs: `get_app_logs` with `app_id`, redact the key before showing.
- Never delete or power off an instance you did not create in this session. Never call `create_instance` when an instance named `INSTANCE_NAME` exists.
