# Server setup for the coding agent

You deploy the Text to Speech starter app on a GalaxyGate server. The user's message holds TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for the panel and your shell only for `curl`. Nothing needs SSH. Ask nothing except where a step says to, and obey every stop.

## Rules

- **Secret.** The key goes only into `environment` on `create_app` or `update_app`, never into a command, a file, or a message. `get_app` shows that environment in plain text, so quote only `state`, `locked` and `container_id` from it. `update_app` replaces the whole environment, so resend every variable. Tell the user at the end that the key is in this chat's tool calls.
- **Shell.** Your only shell commands are `curl` and pauses. On Windows PowerShell write `curl.exe` and `Start-Sleep -Seconds N`.
- **Ids.** Resource ids are strings of digits. A new id is `resource.id`, never `resource.parent.id`. Pass a workflow UUID back unchanged. List tools page their rows into `items`, and a step's `q` filter puts the row you need on the first page.
- **Polling.** Poll counts and pauses are fixed, so count them and never go past them. `ABORTED` and `TIMED_OUT` are `FAILED`. A `404` from `get_workflow` in the first two polls is pending, not failed. Where no budget is given, poll a workflow 6 times pausing 10 seconds.
- **Recipes.** `create_recipe` needs `workspace_id`, `name`, `category` `AUTOMATION`, `description`, and `commands` `[{"path":"/bin/sh","args":["-c","<body>"]}]`. `install_recipe` needs `instance_id`, `recipe_id` and `fields` `{}`, and returns a workflow you poll with `get_workflow` and `workspace_id`, whose `duration` is whole seconds. The panel waits about 50 seconds, calls a longer script `FAILED` while it keeps running, and returns no output. A non-zero exit is `FAILED`. On `Instance is not available` or `must be online`, pause 20 seconds and install again, at most 6 times. Names cannot repeat, so set `RUN` once to the UTC time as `HHMMSS` and use it in every name.
- **Scripts.** Server side scripts live in the organizers' repository under `scripts/`, and a recipe body only fetches one and runs it. `RAW` is `https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/scripts`. Never pipe curl into sh, because the web firewall rejects it.

The **waiting body** runs a short script in the foreground, `NAME` and `ARGS` substituted:

```
curl -fsSL RAW/NAME.sh -o /tmp/NAME.sh
sh /tmp/NAME.sh ARGS
```

The **detached body** starts long work and returns at once, `NAME` and `ARGS` substituted:

```
curl -fsSL RAW/NAME.sh -o /tmp/NAME.sh
mkdir /opt/hackathon-NAME.lock 2>/dev/null || exit 0
rm -f /opt/hackathon-NAME.done /opt/hackathon-NAME.failed
nohup sh -c 'if sh /tmp/NAME.sh ARGS > /var/log/hackathon-NAME.log 2>&1; then touch /opt/hackathon-NAME.done; else touch /opt/hackathon-NAME.failed; fi; rmdir /opt/hackathon-NAME.lock' > /dev/null 2>&1 &
```

## The run procedure

Runs one long script `NAME` with `ARGS`.

1. Create recipe `hk-NAME-RUN`, description `NAME`, with the detached body. Install and poll it. On `FAILED`, install once more, then stop and report.
2. Create recipe `hk-NAME-c-RUN`, description `NAME check`, with the waiting body built from the script `check` and the argument `NAME`, so its second line reads `sh /tmp/check.sh NAME`. Install it and poll 8 times pausing 10 seconds:
   - `COMPLETED`: done.
   - `FAILED`, `duration` 25 seconds or more: still running, so pause 20 seconds and install the check again, at most 24 installs, then stop and say it did not finish in time.
   - `FAILED`, `duration` under 25 seconds: failed. Stop, give the user `INSTANCE_ID`, and say the log is `/var/log/hackathon-NAME.log` and the GalaxyGate table can read it from the server's console.

## 0. Validate the inputs

TEAM_NAME is 3 to 32 characters, lowercase letters, digits and hyphens, starting and ending with a letter or digit. RUNPOD_API_KEY starts with `rpa_`. If either fails, or still reads `yourteam` or `rpa_paste-your-key-here`, stop and say which. Set `INSTANCE_NAME=hack-TEAM_NAME`, `APP_NAME=tts`, and `RUN`.

## 1. Pick the workspace

`list_workspaces`. Exactly one row: its `id` is `WORKSPACE_ID`. Zero or several: stop, show the names, create nothing.

## 2. Find or create the server

1. `list_instances` with `workspace_id` and `q` `INSTANCE_NAME`. A row whose `name` equals `INSTANCE_NAME` is your server, so take its `id` as `INSTANCE_ID` and go to step 3. Never create a second server with that name.
2. `list_plans` with `q` `Lightning-8G` gives `PLAN_ID` and `list_images` with kind `TEMPLATE`, official true and `q` `Ubuntu 24.04` gives `IMAGE_ID`, each from the row whose name matches exactly. Any failure or empty list: stop and report.
3. `create_instance` with `workspace_id`, name `INSTANCE_NAME`, `plan_id`, `image_id`, region `NA_01`, start true, ipv4 true, ipv6 true. `resource.id` is `INSTANCE_ID`. On a timeout or error, run item 1 again, and create a second time only when no instance is there. On `Instance creation not available for this workspace`, stop and give the user that message for the GalaxyGate table.

## 3. Wait for the server to boot

1. Poll `get_instance` 40 times, pausing 15 seconds, until `state` is `AVAILABLE`, `online` is true, and `locked` is null or absent. No recipe installs while `locked` is set. On `state` `FAILED`, or after 40 polls, stop and report the last state.
2. Create recipe `hk-boot-RUN`, description `Boot check`, body `test -f /var/lib/cloud/instance/boot-finished`. Install and poll it. `COMPLETED`: the first boot is done. `FAILED`: pause 15 seconds and install again, at most 12 installs, then stop and say the server never finished its first boot.

## 4. Prepare the server and build the image

Run the run procedure twice, in order. `NAME` `prepare`, no `ARGS`, installs Docker and the loopback registry. `NAME` `build` with `ARGS` `https://github.com/GalaxyGate/philly-hackathon demos/tts base` builds the app as `127.0.0.1:5000/hackathon:base`.

## The wait procedure

Given an `app_id` and its `APP_DOMAIN`, poll `get_app` 32 times, pausing 15 seconds, and from poll 4 onward run step 8 item 1's health check once before each poll, without its stop path. The wait succeeds at the first passing health check, the only real gate. The panel reports `AVAILABLE` before the process inside the container listens, and some servers show `PENDING` and `locked` `Deploying` long after the app serves. The wait fails if `state` becomes `FAILED`, or after poll 32. It creates and deletes nothing.

## 5. Find an existing app, or pick the public name

`list_instance_apps` with `instance_id`. A row named `tts` or `tts-2` means the server already carries the app, so take that `name` as `APP_NAME`, its `id` as `APP_ID`, its `domain` as `APP_DOMAIN`, leave `APP_WORKFLOW` unset, and run the wait procedure on it. Both rows there: use `tts-2`. `state` `STOPPED`: `app_start` first. No `domain`: not a match. A wait that succeeds goes to step 8 whatever the panel state says. A wait that fails goes to step 7's recovery.

Only when no row matches, set `SUBDOMAIN=TEAM_NAME` and `APP_DOMAIN=SUBDOMAIN.galaxygate.app`, then `panel_request` with method `POST`, path `/v1/apps/domains`, body `{"domain":"APP_DOMAIN"}`.

- A `404`, usually an error ending in `panel API 404`: free, because this endpoint uses 404 to mean available. Go to step 6.
- HTTP 200, usually an empty body: taken. Try TEAM_NAME with `-2`, then `-3`, up to `-9`, rebuilding `APP_DOMAIN` each time. All taken: stop and ask for a different team name.
- A `404` carrying `No static resource` or an HTML page: stop and give the user "the domain check returned an unexpected 404" for the table. Any other error: stop and report it.

## 6. Create the app

`create_app` with `instance_id` and this body. The key is the one from the user's message, not this text.

```json
{
  "name": "APP_NAME",
  "image": "127.0.0.1:5000/hackathon:base",
  "ports": [{"host_port": 8000, "container_port": 8000, "protocol": "TCP", "http": true}],
  "environment": {
    "RUNPOD_API_KEY": "<the key from the user's message>",
    "PUBLIC_BASE_URL": "https://APP_DOMAIN"
  },
  "mounts": [{"host_path": "/data/tts", "container_path": "/data", "read_only": false}],
  "domain": "APP_DOMAIN"
}
```

`resource.id` is `APP_ID`, `workflow.id` is `APP_WORKFLOW`.

On a timeout or an error with no status code the app may exist, so call `list_instance_apps`: a row named `APP_NAME` is yours, `APP_WORKFLOW` stays unset, go to step 7. No row: call `create_app` once more. On `An app with this name already exists`, or `Host port` with `already allocated`, go to step 7 item 1. On `Domain is already in use`, take the next suffix from step 5. Any other error: stop and report it.

## 7. Wait for the app, and recover once

Run the wait procedure on `APP_ID`. If it succeeds, go to step 8. The first deploy on a server is the slowest, because the panel runs its own integration workflow with it.

Recovery, at most once in the whole run:

1. Leave the first app where it is. Set `APP_NAME=tts-2`, `host_port` 8001 with `container_port` 8000, `host_path` `/data/tts-2`, and `SUBDOMAIN` to TEAM_NAME with `-r2`, and rebuild `APP_DOMAIN`. Check that name with step 5's `panel_request` call, and if it is taken use `-r3` and check once more. `create_app` with those values and record the new ids. On a `409` or `400` here, stop: list every row from `list_instance_apps` with its `name`, `domain` and `state`, and ask the user to bring that list to the table.
2. Run the wait procedure once more. If it fails, show `state` and `locked` from `get_app`, and the failed `progress.children` from `get_workflow` on `APP_WORKFLOW` when it is set, and stop.

## 8. Prove it works

1. Health. `curl --fail --silent --show-error --connect-timeout 10 --max-time 30 https://APP_DOMAIN/health` passes when it prints `"status":"ok"` and `"runpod_key_set":true`. Outside the wait procedure, try it 12 times pausing 15 seconds, then `get_app_logs` with `app_id` and tail 100, or `get_app` if that errors, show what you got with the key redacted, and stop.
2. One real generation. Run this once. The app answers a server sent events stream.

```
curl --silent --show-error --no-buffer --max-time 300 -H 'Content-Type: application/json' -d '{"text":"Hello from the hackathon.","voice":"lucy"}' https://APP_DOMAIN/api/speak
```

   It passes when a `data:` line carries `"type": "done"` with a `url`. A line carrying `"type": "error"` is a failure, so show its `message`. On 401 the key is wrong. On 402 the RunPod credit is gone. On a timeout, 502, 503, 504, 520 or 522, pause 60 seconds and run this item exactly once more. Stop and show the error in each of those cases.
3. Give the user the URL to open on their phone and laptop. Do not open it yourself.

## 9. Record and report

Write `HACKATHON.md` in the user's project, no secrets, one value per line:

```
WORKSPACE_ID=...
INSTANCE_ID=...
INSTANCE_NAME=...
APP_ID=...
APP_NAME=...
APP_DOMAIN=...
APP_URL=https://...
IMAGE=127.0.0.1:5000/hackathon:base
```

Under the values add: "RUNPOD_API_KEY is in the app environment and in this chat's tool calls. Revoke it in the RunPod console after the event." Then give the user their app URL and say `HACKATHON.md` holds the ids for their Devpost submission.

## Redeploy after the user changes code

Read `HACKATHON.md` for `INSTANCE_ID`, `APP_NAME`, `APP_ID` and `APP_DOMAIN`, or ask the user to paste it. Ask for the public repository URL `REPO_URL` and the folder holding its `Dockerfile`, `APP_DIR`, for example `demos/tts`. Set `TAG` to `r1`, then `r2` and up, never reusing one, because item 3 compares image names. Set `RUN` afresh.

1. Run the run procedure with `NAME` `build` and `ARGS` `REPO_URL APP_DIR TAG`.
2. `get_app`, copy its `environment` without showing it, then `update_app` with `app_id` and `{"image":"127.0.0.1:5000/hackathon:TAG","environment":<that object>}`, which keeps the key. On `App is locked`, pause 20 seconds and call it again, at most 6 times, then stop and report.
3. Create recipe `hk-verify-RUN`, description `Verify`, with the waiting body built from the script `verify-image`, so its second line reads `sh /tmp/verify-image.sh APP_NAME 127.0.0.1:5000/hackathon:TAG`, the panel having named the container after the app. Install it and poll 8 times pausing 10 seconds. `COMPLETED` means the new image is running. Anything else: pause 10 seconds and install again, at most 8 installs, then say the panel did not swap the container, leave the app alone, and stop.
4. Run step 8 items 1 and 2, then change the `IMAGE=` line in `HACKATHON.md`.

## Later requests

- Change the environment: `get_app`, then `update_app` with the whole object copied without showing it and the change applied, then step 8 item 1.
- Restart with `app_restart`. Read logs with `get_app_logs`, key redacted.
- Never delete or power off an instance you did not create in this session, and never run step 7's recovery outside step 7.
