# Server setup instructions for the coding agent

You are setting up a hackathon server on GalaxyGate for the user. The user's message contains TEAM_NAME and RUNPOD_API_KEY. Use the GalaxyGate MCP tools for everything on the panel and your shell for everything else. Work through every step without asking the user anything. If a step fails twice, report exactly what failed and stop.

1. Call `list_workspaces`. Remember the workspace id.
2. If `~/.ssh/galaxygate_hackathon` does not exist, run `ssh-keygen -t ed25519 -N "" -f ~/.ssh/galaxygate_hackathon -C hackathon`. Call `list_ssh_keys`; if no key named `hackathon-agent` exists, call `upload_ssh_key` with that name and the contents of `~/.ssh/galaxygate_hackathon.pub`.
3. Call `list_plans` and pick the plan named `Lightning-8G`. Call `list_images` with kind `TEMPLATE` and pick Ubuntu 24.04. If `list_images` is denied, use image id `1455765925817413632`.
4. Call `create_instance` with name `hack-TEAM_NAME`, region `NA_01`, that plan id, that image id, start true, ipv4 true, ipv6 true. Remember the instance id.
5. Call `get_instance` every 15 seconds until `state` is `AVAILABLE` and `online` is true. Then call `list_instance_ips` and remember the IPv4 address.
6. Run the following until it succeeds, retrying every 20 seconds for up to 5 minutes:
   `ssh -n -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -i ~/.ssh/galaxygate_hackathon root@IPV4 'cloud-init status --wait; uname -a'`
7. Check that `TEAM_NAME.galaxygate.app` is free: call `panel_request` with method POST, path `/v1/apps/domains`, body `{"domain":"TEAM_NAME.galaxygate.app"}`. A 404 means free. If it is taken, append a digit and check again.
8. Call `create_app` on the instance with this body, substituting the real values:
   ```json
   {"name":"roast","image":"ghcr.io/galaxygate/philly-hackathon-roast:latest",
    "ports":[{"host_port":8000,"container_port":8000,"protocol":"TCP","http":true}],
    "environment":{"RUNPOD_API_KEY":"RUNPOD_API_KEY"},
    "mounts":[{"host_path":"/data/roast","container_path":"/data","read_only":false}],
    "domain":"TEAM_NAME.galaxygate.app"}
   ```
   If it fails with a lock or dpkg error, wait 60 seconds and try once more.
9. Call `get_app` every 15 seconds until `state` is `AVAILABLE`. Then run `curl -s https://TEAM_NAME.galaxygate.app/health` and call `get_app_logs` with tail 50. Show the user both results.
10. Write `HACKATHON.md` in the user's project containing: the workspace id, the instance id, the IPv4, the exact ssh command from step 6, the app URL, and a line saying the RunPod key is set in the app environment. Then tell the user the app URL and that they can open it now.

Rules: never print RUNPOD_API_KEY back to the user. Never delete or power off an instance you did not create in this session. If the user later asks for changes, use `update_app` for environment or image changes, `app_restart` to restart, and `get_app_logs` to read logs.
