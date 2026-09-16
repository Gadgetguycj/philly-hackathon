# GalaxyGate + RunPod track

Coffee & Code AI Agent Hackathon. Follow this top to bottom. Setup takes about 20 minutes. Stuck? Come to the GalaxyGate table or post in the Discord channel.

You need: a laptop you can install software on, a GitHub account, an email you can open right now.

## Part 1. Set up

### 1. Install one coding tool

Pick one. No preference? Pick Cursor.

- **Cursor**: download from https://cursor.com and sign in. Redeem your $50 credit link from the GalaxyGate table.
- **Claude Code**: run `npm install -g @anthropic-ai/claude-code`, then `claude` in an empty folder, and sign in.
- **Codex**: run `npm install -g @openai/codex`, then `codex` in an empty folder, and sign in.

### 2. Create your GalaxyGate account

1. Open the GalaxyGate signup link from the QR code. The coupon is already filled in.
2. Open the verification email and click the link.
3. Sign in at https://dash.galaxygate.net. You should see one workspace and no servers.

### 3. Create your RunPod account and an API key

1. Sign up at https://console.runpod.io/signup.
2. Open your $15 credit link from the check-in email. Your balance should read $15.
3. In the console open Settings, then API Keys, then Create API Key. Copy the key. You paste it into the prompt in step 6. It never goes in your code.

### 4. Connect the two MCP servers

Both sign you in through a browser window. There is no key to paste.

**Cursor**: open Cursor Settings, then MCP, then Add new MCP server, and paste this. Save, then click Connect on each server and finish the sign-in in the browser.

```json
{
  "mcpServers": {
    "galaxygate": { "url": "https://mcp.galaxygate.net/mcp" },
    "runpod": { "url": "https://mcp.getrunpod.io/" }
  }
}
```

**Claude Code**: in your project folder run

```bash
claude mcp add --transport http galaxygate https://mcp.galaxygate.net/mcp
claude mcp add --transport http runpod https://mcp.getrunpod.io/
```

then start `claude`, type `/mcp`, and sign in to both.

**Codex**: run

```bash
codex mcp add galaxygate --url https://mcp.galaxygate.net/mcp
codex mcp login galaxygate
codex mcp add runpod --url https://mcp.getrunpod.io/
codex mcp login runpod
```

Codex blocks network inside its sandbox by default. Start it with `codex --sandbox danger-full-access` for this project so it can SSH to your server.

**Check**: ask your agent "List my GalaxyGate workspaces." It should answer with one workspace name.

### 5. Windows only: check SSH

Open PowerShell and run `ssh -V`. If it prints a version, skip ahead. If not, run:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

### 6. Create your server

Fill in the two lines, then paste the whole block into your agent.

```text
TEAM_NAME=yourteam
RUNPOD_API_KEY=paste-your-runpod-key-here

Read https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md and follow it step by step.
```

If your tool cannot open URLs, paste the contents of AGENT.md under those two lines instead.

What happens next, about 10 minutes:

1. The agent makes an SSH key and uploads it to your GalaxyGate workspace.
2. It creates your server and waits for it to boot.
3. It SSHes in to confirm the server is ready.
4. It deploys the demo app with your RunPod key and gives it a public name.
5. It writes HACKATHON.md in your project with the server address, the SSH command, and your app URL.

Done when https://yourteam.galaxygate.app opens and shows the demo.

## Part 2. Build

### What goes where

- **Your GalaxyGate server** runs your app: web pages, API, database, bots. It stays up all day.
- **RunPod** runs only the GPU work: language models, image generation, audio. Your app calls it over HTTPS with your API key.
- **Your coding agent** writes the code, deploys it, and reads the logs. Tell it what you want.

### Call a GPU model from your app

Option 1, a ready-made model. No setup. Example, one image:

```bash
curl -X POST https://api.runpod.ai/v2/black-forest-labs-flux-1-schnell/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"a sticker of a rocket","width":768,"height":768}}'
```

Full list of ready-made models: https://docs.runpod.io/public-endpoints/overview

Option 2, any Hugging Face language model. Tell your agent:

> Using the RunPod MCP, create a serverless vLLM endpoint with model Qwen/Qwen2.5-Coder-7B-Instruct on a 24 GB GPU, max 1 worker, idle timeout 60 seconds. Give me the endpoint id.

Your app then calls `https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1/chat/completions` exactly like the OpenAI API, with your RunPod key. The first request after a quiet period takes 30 to 90 seconds while the model loads.

### Change and redeploy

- Tell your agent what to change. It edits the code, rebuilds the image, and updates the app on your server.
- "Show me the app logs" makes it read the container logs through the panel.
- "Restart the app" restarts the container.
- Your RunPod key stays in the app's environment. Never commit it.

### The demo apps

Both are in this repo. Fork either one or start from scratch.

- **Roast My Repo**, `demos/roast`: paste a GitHub URL, a coder model on RunPod streams a roast, a Fix button returns a patch, a leaderboard keeps score.
- **The Sticker Wall**, `demos/stickerwall`: type a prompt, Flux draws a sticker, it lands on a shared wall page.

Each folder has a README with run and deploy steps.

### Ideas

- A Discord bot that answers with generated images
- Voice notes that get transcribed and summarised
- A comic strip generator
- A code review bot for pull requests
- A game master for a multiplayer text game
- A product photo studio

### Optional: run an agent platform on your server

Agent Zero is a self-hosted agent with a web UI in one container. Tell your agent:

> Deploy agent0ai/agent-zero on my server as an app named agent, container port 80, host port 8080, http true, domain TEAM_NAME-agent.galaxygate.app, with a mount from /data/agent-zero to /a0/usr.

Open the URL, set a password, then in Settings under External Services paste your RunPod vLLM endpoint URL and key. Agent Zero also exposes an MCP server; ask your agent to add it as a third MCP server if you want to delegate tasks to it.

### Optional: prefer plain SSH and docker compose?

Skip the panel apps. Tell your agent:

> SSH into my server, install docker.io and docker-compose-v2, clone https://github.com/GalaxyGate/philly-hackathon to /opt/hackathon, put RUNPOD_API_KEY in demos/roast/.env, and run docker compose up -d there.

Your app answers at `http://<server ip>:8000`.

## Part 3. Submit

### Submit on Devpost before the deadline

- Working prototype, description, repo link, video under 3 minutes, tools list, team list, setup steps
- GalaxyGate track fields: your instance id and app URL, your RunPod endpoint ids, a screenshot of your agent creating the server through MCP, what you built today
- Your app URL must still work when judges open it

### How the GalaxyGate track is scored, 100 points

- **Runs live on GalaxyGate, 25.** Judges open your URL and it works. Server and app were created during the hackathon.
- **Real GPU work on RunPod, 25.** The GPU call is the point of your app. Requests show in your RunPod console.
- **Agent-driven infrastructure, 20.** Your agent created and operated the server and app through MCP. Extra credit if it recovered from a failure.
- **Agentic design and usefulness, 15.** The product is an agent or agentic workflow that solves a real problem.
- **Reliability, safety, cost, 10.** Secrets in the environment, cold starts handled, endpoint scales to zero.
- **Demo and completeness, 5.** Video, README, honest statement of what was built today.
- **Zero points**: URL down with no proof it ran, a faked RunPod call, or infrastructure built before the hackathon.
- **Prize**: $1,000 and GalaxyGate compute credits, one winner.

## When something fails

- **MCP server says needs login**: click Connect again and finish the browser sign-in.
- **create_app fails with a lock or dpkg error**: the server is still finishing first boot. Wait 60 seconds and retry.
- **SSH connection refused**: the server is still booting. Retry in 20 seconds.
- **RunPod returns 401**: the API key is wrong or missing from the app environment.
- **RunPod request hangs**: cold start. Wait up to 90 seconds, then check the endpoint's workers in the RunPod console.
- **Anything else**: the GalaxyGate table, or the Discord channel.
