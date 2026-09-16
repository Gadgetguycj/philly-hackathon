# GalaxyGate + RunPod track

Coffee & Code AI Agent Hackathon. Follow Part 1 top to bottom, then build. Help: the GalaxyGate table, or the hackathon Discord at https://discord.com/invite/HP4BhW3hnp.

Before you start you need a laptop you can install software on, a GitHub account, and an email inbox you can open now. If you are a team, one teammate does Part 1 and shares the resulting URL and repository with the others.

## Part 1. Set up

### 1. Make a project folder and pick one coding tool

Create an empty folder on your laptop named `hackathon`. Everything below happens in that folder.

Pick one tool. If you have none, pick Cursor.

- **Cursor.** Download from https://cursor.com/downloads, sign in, then File, Open Folder, and choose `hackathon`. If you received one of the fifty Cursor credit cards at the GalaxyGate table, redeem it at the link on the card before you continue.
- **Claude Code.** Install Node.js LTS from https://nodejs.org if `node --version` in a terminal prints nothing. Then in a terminal opened in `hackathon` run `npm install -g @anthropic-ai/claude-code`, then `claude`, and sign in when it asks.
- **Codex.** Install Node.js LTS the same way. Then in a terminal opened in `hackathon` run `npm install -g @openai/codex`, then `codex`, and sign in when it asks.

Terminal commands in this guide are typed in a terminal. Prompts are pasted into the tool's chat.

### 2. Create your GalaxyGate account

1. Open https://dash.galaxygate.net/-/register. If the coupon box is empty, type the coupon code from the GalaxyGate table.
2. Open the verification email and click the link.
3. Sign in at https://dash.galaxygate.net. You should see one workspace and no servers. If you already had a GalaxyGate account before the event, sign in and ask at the GalaxyGate table to apply the coupon.

### 3. Create your RunPod account and one API key

1. Sign up at https://console.runpod.io/signup.
2. Open the RunPod credit link from your check-in email and redeem it. Your balance should read $15.
3. In the console open Settings, expand API Keys, click Create API Key. Name it `hackathon-app`, choose the permission `All`, create it, and copy the key. You paste it into the prompt in step 6.

This key can spend your credit. It goes into your app's environment on your server, never into your code or your repository. Revoke it on the same page after the event.

### 4. Connect the two MCP servers

Both servers sign you in through a browser window. There is no key to paste for this step.

**Cursor.** Inside the `hackathon` folder create a file at `.cursor/mcp.json` with this content. If the file already exists, add the two entries inside its existing `mcpServers` object instead of replacing it.

```json
{
  "mcpServers": {
    "galaxygate": { "url": "https://mcp.galaxygate.net/mcp" },
    "runpod": { "url": "https://mcp.getrunpod.io/" }
  }
}
```

Save, restart Cursor, open the Customize page from the sidebar, open MCPs, and complete the sign-in for each of the two servers.

**Claude Code.** In a terminal opened in `hackathon`:

```bash
claude mcp add --transport http galaxygate https://mcp.galaxygate.net/mcp
claude mcp add --transport http runpod https://mcp.getrunpod.io/
```

Then start `claude`, type `/mcp`, and complete the sign-in for each server.

**Codex.** In a terminal opened in `hackathon`:

```bash
codex mcp add galaxygate --url https://mcp.galaxygate.net/mcp
codex mcp login galaxygate
codex mcp add runpod --url https://mcp.getrunpod.io/
codex mcp login runpod
```

Codex blocks network access inside its sandbox by default, and the setup prompt needs SSH. Start Codex for this project with:

```bash
codex --sandbox workspace-write -c sandbox_workspace_write.network_access=true
```

Approve the requests it shows you; do not turn the sandbox off.

**Check.** Paste this into your tool: `Call the GalaxyGate list_workspaces tool and the RunPod list-endpoints tool and show me both results.` You should see one GalaxyGate workspace with your name on it, and a RunPod endpoint list, which may be empty. If either call fails, redo the sign-in for that server.

### 5. Windows only: make sure SSH exists

1. Open PowerShell as administrator: Start, type PowerShell, right click, Run as administrator.
2. Run `ssh -V`. If it prints a version, close the window and skip ahead.
3. Otherwise run `Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0`, wait for it to finish, close the window, open a normal terminal in `hackathon`, and run `ssh -V` again.

macOS and Linux already have SSH.

### 6. Create your server

Replace `yourteam` with your team name: 3 to 32 characters, lowercase letters, digits, and hyphens only. Replace the key. Then paste the whole block into your tool.

```text
TEAM_NAME=yourteam
RUNPOD_API_KEY=rpa_paste-your-key-here

Read https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md and follow it step by step. Stop and tell me if the page does not load.
```

If your tool cannot open web pages, open https://github.com/GalaxyGate/philly-hackathon/blob/main/AGENT.md yourself, copy its whole text, and paste it under the two lines instead.

The agent creates an SSH key, uploads it to your GalaxyGate workspace, creates your server, waits for it to boot, deploys the demo app with a public name, runs the demo once for real, and writes `HACKATHON.md` in your folder with every id you will need.

Done when the agent reports that both checks passed and gives you your URL, and https://yourteam.galaxygate.app opens in your browser and roasts a public GitHub repository when you paste one.

Your RunPod key is now in your agent's chat history and in the app's environment on your server, where anyone in your GalaxyGate workspace can see it. Keep the workspace to your team and revoke the key after the event.

## Part 2. Build

### The one rule

Your app, its data, and your RunPod key live on your GalaxyGate server. Your app's backend calls RunPod over HTTPS. Never call RunPod from browser JavaScript, and never put the key in your repository.

### Change the demo, or start your own app

The demo running on your server is `demos/roast` in https://github.com/GalaxyGate/philly-hackathon. Fork that repository into your GitHub account, then tell your agent: `Clone my fork of philly-hackathon into this folder.` Edit whatever you like, or add a new app folder next to the demos.

To put your changes on your server, tell your agent: `Build my app on the server and redeploy it.` The agent copies your code to the server over SSH, builds the Docker image there, and updates the app to the new image. Ask `Show me the app logs` when something is wrong, and `Restart the app` to restart it.

### Use a GPU model from your app

Ready-made models, no deployment. Tell your agent: `Add a route to my app that generates an image with RunPod's Flux Schnell public endpoint using the RUNPOD_API_KEY from the environment, saves the image on the server, and shows it on a page.` The endpoint is `https://api.runpod.ai/v2/black-forest-labs-flux-1-schnell/runsync`; it takes `{"input":{"prompt":"...","width":768,"height":768}}` with the key as a bearer token and returns an image URL in `output.result`. Other ready-made models, including Qwen for text, are listed at https://docs.runpod.io/public-endpoints/overview.

Your own Hugging Face model. Tell your agent: `Using the RunPod MCP, deploy the vLLM hub repo as a serverless endpoint named hackathon-llm with MODEL_NAME Qwen/Qwen2.5-Coder-7B-Instruct and MAX_MODEL_LEN 8192 on a 24 GB GPU pool, min workers 0, max workers 1, idle timeout 60 seconds. Then send one chat completion to it and show me the reply and the endpoint id.` Your app then calls `https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1/chat/completions` with your key and that model name. The first request after a quiet period waits while the model loads; keep your app's timeout above two minutes.

### Spending

The demo app caps itself at 30 generations per hour so a stranger cannot drain your credit; the cap is the `MAX_GENERATIONS_PER_HOUR` environment variable. Keep a cap in anything you build. Check your RunPod balance in the console before you submit.

## Part 3. Submit

### Eligibility

- Your GalaxyGate server and app were created during the build period. The organizers' starter code and RunPod's public models are allowed; say what you reused.
- Fabricated evidence, including a faked RunPod call, removes the project from this track.

### Devpost

Submit at https://coffee-and-code-agent.devpost.com/ before the deadline shown there, and select the GalaxyGate prize. Alongside the standard fields, give judges:

- Your app URL, GalaxyGate instance id and app id (all in `HACKATHON.md`), and one exact input to try.
- Your RunPod endpoint id, or the public model you used, plus one request record: a screenshot of the request in your RunPod console or a redacted response.
- Your repository, the commit you started from, the commit you submitted, and a short list of what you changed or built.
- A video under three minutes and a README that lets a stranger run it. Check both open in a browser where you are signed out.

Do not include environment screens, API keys, private keys, or credit links in anything you submit.

### Scoring, 100 points

- **Live app, 20.** The URL opens (5), a judge's fresh input succeeds (10), and the result is still reachable afterwards (5).
- **RunPod integration, 20.** A judge's fresh input produces a matching request in your RunPod console or a redacted response (10), and your app visibly uses the model's result (10).
- **Agent-operated infrastructure, 15.** Redacted tool-call records show your agent creating the server (5), deploying the app (5), and making one later update or restart (5).
- **Agentic usefulness, 25.** A stated user task with a clear success condition (5), a trace showing the model choosing actions and using their results (10), success on a judge-supplied input (5), and one honestly demonstrated limitation (5). A single fixed model call earns no action points.
- **Reliability, safety, cost, 15.** Secrets kept out of the repository, logs, and screenshots (5), paid routes protected by a cap or login (5), a slow start or upstream error handled visibly (5).
- **Submission, 5.** Video (2), README (2), the disclosures above (1).

Ties break on agentic usefulness, then reliability. If your app is down when judges test it, a timestamped end-to-end recording counts for everything except the live-app points.

## When something fails

- **An MCP server shows needs login or a tool call is denied.** Redo that server's sign-in: Cursor in Customize, MCPs; Claude Code with `/mcp`; Codex with `codex mcp login <name>`.
- **The agent says the server never became ready.** Ask it to run `get_instance` and show the state, and `cloud-init status --long` over SSH. Bring both to the GalaxyGate table.
- **The first app deploy sticks or fails.** The agent instructions already delete and redeploy once. If it fails twice, ask the agent for the workflow message and bring it to the table.
- **RunPod answers 401.** The key is wrong or missing from the app environment. Create a new key and ask the agent to update the app.
- **RunPod answers 402.** Your credit is gone. Check the console.
- **A generation hangs.** Ask the agent to read the app logs and, for your own endpoint, the endpoint's workers in the RunPod console. Do not resend the same request repeatedly.

When you ask for help, bring: your tool, the step you were on, the ids from `HACKATHON.md`, and the exact error text with your key removed.

## After the event

Delete the server from the GalaxyGate panel or ask your agent to, revoke the `hackathon-app` key in the RunPod console, and check that no RunPod endpoint you created still has workers running.
