# Server setup instructions for the coding agent

You are setting up a hackathon server on GalaxyGate for the user. The user's message contains two values: TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for everything on the panel and your shell for everything else. Do not ask the user questions. Follow the stop rules in each step.

Secret rule. RUNPOD_API_KEY appears only inside the `environment` object of a `create_app` or `update_app` call. Never anywhere else: not in a shell command, not in a file you write, not in a log or error you quote. An `update_app` environment replaces the whole set, so first read the app's current environment with `get_app` and send every variable it already has, plus the key from the user's message. Assume those calls are visible in the chat history, and say so to the user at the end.

Shell rule. Commands below are written for bash. On Windows, run them in Git Bash, which your tool uses when Git for Windows is installed; do not wrap them in another shell. If Git for Windows is missing, use PowerShell equivalents: `New-Item -ItemType Directory -Force` for `mkdir -p`, skip `chmod`, `Start-Sleep -Seconds N` for `sleep N`, `curl.exe` instead of `curl`, one command per line instead of `&&`, and write files with `Set-Content -Encoding ascii` (never `Out-File` or `>`, which truncate lines at the console width). Step 12 needs Git Bash.

Waiting rule. Every wait below is a fixed number of polls with a fixed pause. Count the polls. Never poll past the count.

List rule. Every list tool returns a paged envelope; read rows from `items`. When a step names a `q` filter, pass it so the row you need is on the first page.

Key location. The SSH key lives inside the project folder at `.hackathon/galaxygate_hackathon`, so your sandbox can write it. Add a line `.hackathon/` to the project's `.gitignore` (create the file if needed) before generating the key.

## 0. Validate the inputs

- TEAM_NAME must be 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. If it does not match, or still reads `yourteam`, stop and tell the user the rule.
- RUNPOD_API_KEY must start with `rpa_` and must not be the placeholder text. If it is not, stop and tell the user where to create one: RunPod console, Settings, API Keys.
- Set `INSTANCE_NAME=hack-TEAM_NAME` and `APP_NAME=roast`.

## 1. Pick the workspace

Call `list_workspaces`. If `items` holds exactly one workspace, use its `id` as `WORKSPACE_ID`. If zero or several, stop and show the user the names; create nothing.

## 2. Check for a previous run

Call `list_instances` with `workspace_id` and `q` set to `INSTANCE_NAME`. If a row's `name` equals `INSTANCE_NAME`, record its `id` as `INSTANCE_ID` and set `REUSED=true`. Otherwise set `REUSED=false`. Continue to step 3 either way. Never create a second server with the same name.

## 3. SSH key

- Run `mkdir -p .hackathon && chmod 700 .hackathon` in the project folder.
- If `.hackathon/galaxygate_hackathon` does not exist, run `ssh-keygen -t ed25519 -N "" -f .hackathon/galaxygate_hackathon -C hackathon`. If it exists but the `.pub` file is missing, run `ssh-keygen -y -f .hackathon/galaxygate_hackathon` and save the single output line to `.hackathon/galaxygate_hackathon.pub` as plain ASCII.
- Read the public key text. Call `list_ssh_keys` with `workspace_id`. Compare each row's `public_key` to this text after stripping surrounding whitespace and ignoring the trailing comment (the third space-separated field). If one matches, set `KEY_UPLOADED=false`. Otherwise call `upload_ssh_key` with `workspace_id`, name `hackathon-` followed by the first 8 characters of TEAM_NAME and 4 random digits, and the public key text; call `list_ssh_keys` again to confirm it is present; set `KEY_UPLOADED=true`.
- If `REUSED` is true: if `KEY_UPLOADED` is true, call `sync_ssh_keys` with `instance_id` (workspace keys are injected only when a server is created). Then skip to step 5.

## 4. Create the server

- Call `list_plans` with `q` set to `Lightning-8G`. Use the row whose `name` is exactly `Lightning-8G`; record its `id` as `PLAN_ID`. If there is none, stop and report.
- Call `list_images` with `workspace_id`, kind `TEMPLATE`, official true, and `q` set to `Ubuntu 24.04`. Use the row whose `name` is `Ubuntu 24.04`; record its `id` as `IMAGE_ID`. If the call is denied with a 403 that mentions permission or scope, use `IMAGE_ID=1455765925817413632`: the organizers created an Ubuntu 24.04 server from this exact id during event preparation and will re-check it on the morning of the event. Any other failure, or an empty list: stop and report.
- Call `create_instance` with `workspace_id`, name `INSTANCE_NAME`, `plan_id`, `image_id`, region `NA_01`, start true, ipv4 true, ipv6 true. Record the returned instance `id` as `INSTANCE_ID` and the workflow id as `PROVISION_WORKFLOW`.
- If the call errors after a timeout, call `list_instances` with `q` set to `INSTANCE_NAME` before doing anything else. If the instance exists, use it. Only if it does not exist may you call `create_instance` once more.

## 5. Wait for the server

- Poll `get_instance` with `instance_id` at most 40 times, pausing 15 seconds between polls, until `state` is `AVAILABLE` and `online` is true. If `state` becomes `FAILED`, stop and report. After 40 polls, stop and report the last state.
- Call `list_instance_ips` with `instance_id`. Record the address written with dots (the IPv4 address) as `IPV4`. If there is none, stop and report.

## 6. Confirm SSH and first boot

Try this at most 15 times, pausing 20 seconds between attempts, but only retry when ssh could not connect (connection refused, timed out, or no route). If ssh connects and the remote command fails, that attempt is final:

```
ssh -n -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i .hackathon/galaxygate_hackathon root@IPV4 'timeout 300 cloud-init status --wait && install -d -o 1000 -g 1000 /data/roast /data/roast-2 && echo READY'
```

Success means the output ends with `READY`. On a final failure, run the same ssh command with `cloud-init status --long` as the remote command, show the user the output, and stop. Do not deploy the app on a server that did not print `READY`.

## 7. Pick the public name

Set `SUBDOMAIN=TEAM_NAME` and `APP_DOMAIN=SUBDOMAIN.galaxygate.app`. Call `panel_request` with method `POST`, path `/v1/apps/domains`, body `{"domain":"APP_DOMAIN"}`.

- The tool returns an error whose text contains `404`: the name is free. This endpoint uses 404 to mean available. Continue.
- The tool returns success (HTTP 200, usually an empty body): the name is taken. Set `SUBDOMAIN` to TEAM_NAME followed by `-2`, then `-3`, and so on up to `-9`, rebuild `APP_DOMAIN`, and check again. Example: team `orbit` taken, try `orbit-2.galaxygate.app`.
- If `-9` is also taken, stop and ask the user for a different team name.
- Any other error: stop and report it.

## The wait procedure, used by steps 8, 9, and 12

Given an `app_id` and its `APP_DOMAIN`: poll `get_app` at most 32 times, pausing 15 seconds between polls. From poll 12 onward, before each poll, run the health check from step 10.1 once. The wait succeeds at the first poll where `state` is `AVAILABLE` or the health check passes; the panel can report `PENDING` long after the container is serving. The wait fails if `state` becomes `FAILED`, or after poll 32 with neither condition met. The wait never deletes or creates anything.

## 8. Deploy the demo app

Call `list_instance_apps` with `instance_id`. If a row's `name` equals `APP_NAME`, record its `id` as `APP_ID`, set `APP_DOMAIN` to its `domain` and `SUBDOMAIN` to the part of that domain before `.galaxygate.app`, and run the wait procedure on it. If the wait succeeds, skip to step 10, whatever the panel state says. If it fails, go to the recovery in step 9.

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
    "MAX_GENERATIONS_PER_HOUR": "25"
  },
  "mounts": [{"host_path": "/data/roast", "container_path": "/data", "read_only": false}],
  "domain": "APP_DOMAIN"
}
```

Record the returned app `id` as `APP_ID` and the workflow id as `APP_WORKFLOW`.

## 9. Wait for the app, and recover once if the first deploy sticks

Run the wait procedure on `APP_ID`. If it succeeds, go to step 10.

Recovery, at most once in this whole run:

1. Call `get_workflow` with `workspace_id` and `APP_WORKFLOW`. Keep its `state` and, from `progress.children`, the `name` and `status` of every child that is not `COMPLETED`, for the report.
2. Call `get_app` with `app_id`. If its `locked` field is set, go to 3. Otherwise call `delete_app` with `app_id`. Deletion is asynchronous: poll `get_app` with the old `app_id` at most 12 times, pausing 10 seconds, until it returns an error whose text contains `404`. Only then repeat step 8's `create_app` with the same values, and record the returned app `id` as `APP_ID` and workflow id as `APP_WORKFLOW`, replacing the old values. If the app is still there after 12 polls, go to 3.
3. If the app was locked, or `delete_app` returned an error whose text contains `409`, leave that app alone. Set `APP_NAME=roast-2`, use `host_port` 8001, use `host_path` `/data/roast-2`, set `SUBDOMAIN` to the current value with `-2` appended, check it as in step 7, and call `create_app` with those values. Record the new `APP_ID` and `APP_WORKFLOW`, replacing the old values.
4. Run the wait procedure once more. If it fails, show the user the workflow state and the non-completed children from 1, and stop.

## 10. Prove it works

1. Health. `curl --fail --silent --show-error --connect-timeout 10 --max-time 30 https://APP_DOMAIN/health` passes when it prints JSON containing `"status":"ok"`, `"runpod_key_set":true` and `"model_configured":true`. When this step is reached outside the wait procedure, try it at most 12 times, pausing 15 seconds, and after 12 failures call `get_app_logs` with `app_id` and tail 100; if that errors, call `get_app` and report its `state`, `locked` and `container_id` instead. Show the user whichever you got, with the key redacted, and stop.
2. Real roast. Run `curl --silent --show-error --max-time 240 -N -w '\nHTTP:%{http_code}\n' -H 'Content-Type: application/json' -d '{"repo_url":"https://github.com/GalaxyGate/philly-hackathon"}' https://APP_DOMAIN/api/roast` and save the output to a temporary file. Expected: `event: token` lines, then an `event: done` line, no `event: error` line, and `HTTP:200`. If an `error` event mentions 401, tell the user the key was not substituted or is wrong, and stop. If it mentions 402, tell the user their RunPod credit is exhausted, and stop. If it mentions an hourly limit, report the cap and stop. Any other `error` event: show its text redacted and stop.
3. Tell the user the URL to open in their browser. Do not open it yourself.

## 11. Record and report

Write `HACKATHON.md` in the user's project containing, with no secrets:

- workspace id, instance id, instance name, IPv4
- app id, app name, image, app URL `https://APP_DOMAIN`
- provisioning and app workflow ids, and whether the panel still showed the app as deploying when the health check passed
- the login command: `ssh -i .hackathon/galaxygate_hackathon root@IPV4`
- the line: "RUNPOD_API_KEY is set in the app environment on the server, and the create_app call that set it is in this chat history. The panel shows environment values in plain text to workspace members. Revoke this key in the RunPod console after the event."

Then tell the user: the app URL, that the health check and one real roast succeeded, and that HACKATHON.md holds the ids they need for the Devpost submission.

## 12. Redeploy after the user changes code

This step needs Git Bash on Windows; in PowerShell the pipe in 12.2 corrupts the archive. The panel always pulls an app's image from a registry when it deploys, so the new image goes into a registry that runs on the server itself and listens only on its loopback address.

0. Recover the values. Read `HACKATHON.md` in the project for `INSTANCE_ID`, `IPV4`, `APP_NAME`, `APP_ID` and `APP_DOMAIN`. If it is missing, call `list_instances` with `q` set to the instance name, then `list_instance_apps`, and confirm the app's domain with the user before touching anything. Run every command in this step from the project folder, where `.hackathon` lives, not from inside the cloned repository.
1. Make sure the server has a running registry: `ssh -n -T -o BatchMode=yes -i .hackathon/galaxygate_hackathon root@IPV4 'docker start registry 2>/dev/null || docker run -d --restart unless-stopped -p 127.0.0.1:5000:5000 --name registry registry:2'`. If this command fails, show the user its output and stop.
2. Copy the folder: `tar czf - --exclude=.hackathon -C <parent of folder> <folder name> | ssh -T -o BatchMode=yes -i .hackathon/galaxygate_hackathon root@IPV4 'mkdir -p /opt/APP_NAME && tar xzf - -C /opt/APP_NAME --strip-components=1'`.
3. Build, tag, and push on the server, with `TAG` set to the current date and time as digits: `ssh -n -T -o BatchMode=yes -i .hackathon/galaxygate_hackathon root@IPV4 'docker build -t 127.0.0.1:5000/APP_NAME:TAG /opt/APP_NAME && docker push 127.0.0.1:5000/APP_NAME:TAG'`. If it fails, show the user the last lines and stop.
4. Call `update_app` with `app_id` and body `{"image":"127.0.0.1:5000/APP_NAME:TAG"}`. Run the wait procedure with two changes: start the check at poll 1, and in place of the health check request `https://APP_DOMAIN/` with `curl --silent --output /dev/null --max-time 20 -w '%{http_code}'`. Any code below 500 counts as serving; the proxy answers 502 while no container runs, and the panel removes the old container before it pulls the new image, so a non-5xx answer is the new one.
5. If the app still serves `/health`, run step 10.1; if it still serves `/api/roast`, run step 10.2. A route the user removed is not a failure.
6. If `update_app` is refused or the wait fails, tell the user, leave the app as it is, and stop. Do not start app containers outside the panel.

## Other later requests

- Change the environment: read the current environment with `get_app`, then `update_app` with `app_id` and the full `environment` object (every existing variable plus the key from the user's message), then the wait procedure, then step 10.1.
- Restart: `app_restart` with `app_id`. Logs: `get_app_logs` with `app_id`, redact the key before showing.
- Never delete or power off an instance you did not create in this session. Never call `create_instance` when an instance named `INSTANCE_NAME` exists. Never run the step 9 recovery outside step 9.
