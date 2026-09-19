# GalaxyGate + RunPod track

Coffee & Code AI Agent Hackathon. Do the account steps, open the section for your tool, then build. Help is at the GalaxyGate table. You need a laptop, a GitHub account and an email inbox. One teammate sets up and shares the URL.

## Accounts

1. Register at https://dash.galaxygate.net/-/register with the coupon `PHILLYHACKATHON-60`, open the verification email, and sign in. An older account needs the coupon applied at the GalaxyGate table.
2. Sign up at https://console.runpod.io/signup, then claim your RunPod credit and enter the swag raffle at https://runpod.galaxygate.app.
3. In the RunPod console open Settings, API Keys, Create API Key. Name it `hackathon-app`, permission `All`, and copy it now, because RunPod shows it once. It belongs in your app's environment, never in your repository.

Your team name is 3 to 32 characters, lowercase letters, digits and hyphens, starting and ending with a letter or digit. Setup takes a while, so stay at the laptop and watch for approval prompts. You are done when the health check and one generation pass and your URL opens on your phone.

## Using Claude Code

Open a terminal in a new empty folder named `hackathon` and connect the two MCP servers.

```bash
claude mcp add -t http galaxygate https://mcp.galaxygate.net/mcp
claude mcp add -t http runpod https://mcp.getrunpod.io/
```

Start `claude` there, type `/mcp`, and sign in to both servers. Always start Claude Code from this folder.

Fill in your team name and key, then paste this.

```text
TEAM_NAME=yourteam
RUNPOD_API_KEY=rpa_paste-your-key-here

Fetch https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md and follow it step by step. Stop and tell me if it does not load.
```

## Using Cursor

Install Cursor from https://cursor.com/download, sign in, and open a new empty folder named `hackathon`.

In Cursor's Explorer click New File, type `.cursor/mcp.json` as the whole name, and paste this. If it exists, add both entries to its `mcpServers` object.

```json
{
  "mcpServers": {
    "galaxygate": { "url": "https://mcp.galaxygate.net/mcp" },
    "runpod": { "url": "https://mcp.getrunpod.io/" }
  }
}
```

Save, restart Cursor, open Customize, MCP, and sign in to each server that says Needs login. Check both toggles are on.

Fill in your team name and key, then paste this.

```text
TEAM_NAME=yourteam
RUNPOD_API_KEY=rpa_paste-your-key-here

Fetch https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md and follow it step by step. Stop and tell me if it does not load.
```

## Using Codex

Open a terminal in a new empty folder named `hackathon`. Codex on the web cannot connect MCP servers.

```bash
codex mcp add galaxygate --url https://mcp.galaxygate.net/mcp
codex mcp login galaxygate
codex mcp add runpod --url https://mcp.getrunpod.io/
codex mcp login runpod
```

Codex blocks network access until you allow it. Put these lines in `~/.codex/config.toml`, creating it if missing, then start `codex`.

```toml
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

Fill in your team name and key, then paste this.

```text
TEAM_NAME=yourteam
RUNPOD_API_KEY=rpa_paste-your-key-here

Fetch https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md and follow it step by step. Stop and tell me if it does not load.
```

## The demos

Both run on GalaxyGate servers with GPU work on RunPod, and setup puts Text to Speech on yours.

**Text to Speech**, https://runpoddemo1.galaxygate.app. Paste up to 2000 words, pick a voice from 20, hear it aloud.

```text
Clone https://github.com/Gadgetguycj/philly-hackathon here, push it to a public repository of mine, then follow the redeploy section of https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md for my repository and demos/tts.
```

**Bookbuilder**, https://runpoddemo2.galaxygate.app. Name a subject and watch a fast mixture of experts model write a 100 page book.

```text
Clone https://github.com/Gadgetguycj/philly-hackathon here, push it to a public repository of mine, then follow the redeploy section of https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md for my repository and demos/bookbuilder.
```

## Build

Your app and your key live on your server, and only your server calls RunPod. Change a demo or start your own app, push it, and redeploy with the prompt above. Optional, and worth extra credit:

```text
Using the RunPod MCP, create a serverless endpoint for the model I name, then add a route to my app that calls it.
```

## Submit

Submit at https://coffee-and-code-agent.devpost.com/ and select the GalaxyGate prize. Give judges your app URL, one input to try, and the ids from `HACKATHON.md`. Include no keys or environment screens.

## Scoring

Required to be judged, and neither earns points:

- Your app runs on a GalaxyGate server a judge can open.
- Your app does its GPU work on RunPod and you can show the request.

Judges score live with their own inputs, out of 100.

- **It works, 20.** The judge's first input produces the promised result (10). A second, different input works (5). Nothing crashes, blanks, or spins forever (5).
- **Simple to use, 20.** A first-timer finishes the core task with no instructions (10). The screen says what is happening (5). The README gets a stranger running (5).
- **Reliable, 15.** Results survive a reload and a second run (5). Upstream errors reach the user instead of a hang (5). Two people using it at once do not break it (5).
- **Secure, 10.** Secrets live only in the server's environment (5). Only your server calls RunPod, never the browser (5).
- **Scalable, 10.** GPU work runs on an endpoint that scales to zero and adds workers (5). App state lives outside the container (5).
- **Agentic, 10.** The app decides its next step from model output or tools instead of one fixed call, and the judge can see it (10).
- **Creativity, 15.** An idea the judge has not seen before (5). A use of the GPU that is not just a chat box (5). A moment in the demo that makes the judge react (5).

Extra credit, up to 15, each for a visible reason:

- **More of GalaxyGate, 5 each, up to 10.** A second server doing real work, private networking, a floating IP, a backup or snapshot, or a load balancer.
- **More of RunPod, 5.** A second endpoint or model, a network volume, or a pod for training or a batch job.

Ties break on Simple to use, then Reliable.

## When something fails

- **A tool call is denied or says Needs login.** Redo that sign-in in your tool.
- **The agent stopped.** Paste the same block in a new chat, with the same team name and key.
- **A generation returns 401.** Make a new RunPod key and have your agent update the app's environment.
- **RunPod returns 402.** Your credit is gone, so check the console.
- **Anything else.** Ask your agent for the app logs, then bring the error text and `HACKATHON.md` to the table.

## After the event

Delete your server in the GalaxyGate panel and revoke the `hackathon-app` key in the RunPod console.
