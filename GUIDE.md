# GalaxyGate + RunPod track

Coffee & Code AI Agent Hackathon. Follow Part 1 top to bottom, then build. Help is at the GalaxyGate table.

Before you start you need a laptop you can install software on, a GitHub account, and an email inbox you can open now. If you are a team, one teammate does Part 1 and shares the resulting URL and repository with the others.

## Part 1. Set up

### 1. Pick where you will work

Use the coding tool you already have. Any of these can do everything in this guide from a browser or a desktop app:

- **Cursor.** Desktop: download from https://cursor.com/download, sign in, then File, Open Folder, and choose a new empty folder named `hackathon` (create it on your Desktop first). Web: open https://cursor.com/agents; cloud agents need a paid Cursor plan. If you received a Cursor credit code card at the GalaxyGate table, redeem it at the link on the card first.
- **Claude Code.** Desktop app or terminal, opened in an empty folder named `hackathon`. Web: https://claude.ai/code, connected to a GitHub repository of yours (any empty repository works).
- **Codex.** Terminal, opened in an empty folder named `hackathon`; step 4 below is written for the terminal. Codex on the web cannot connect MCP servers.

If you have none of these, use Cursor.

### 2. Create your GalaxyGate account

1. Open https://dash.galaxygate.net/-/register. If the coupon box is empty, type the coupon code from the GalaxyGate table.
2. Open the verification email and click the link. Check your spam folder if it is not there within a minute.
3. Sign in at https://dash.galaxygate.net. You should see one workspace and no servers. If you already had a GalaxyGate account before the event, sign in and ask at the GalaxyGate table to apply the coupon.

### 3. Create your RunPod account and one API key

1. Sign up at https://console.runpod.io/signup.
2. Open https://runpod.galaxygate.app and follow it. It gives you your own $15 credit link, and it is where you enter the RunPod swag raffle. Redeem the link, then check your balance reads $15.
3. In the console open Settings, expand API Keys, click Create API Key. Name it `hackathon-app`, choose the permission `All`, create it, and copy the key now. RunPod shows it only once. You paste it into the prompt in step 5.

This key can spend your credit. It goes into your app's environment on your server, never into your code or your repository. Revoke it on the same page after the event. Your agent needs the `All` permission once, to create your endpoint. After that you can create a second key with only the permission your app needs and ask the agent to put that one in the app's environment; the Secure score in Part 3 rewards this.

### 4. Connect the two MCP servers

Both servers sign you in through a browser window. There is no key to paste for this step. The two addresses are `https://mcp.galaxygate.net/mcp` and `https://mcp.getrunpod.io/`.

**Cursor desktop.** In Cursor's Explorer sidebar click New File, type `.cursor/mcp.json` as the whole file name, press Enter, and paste this. Do not try to create the `.cursor` folder in File Explorer or Finder; they refuse names starting with a dot. If the file already exists, add the two entries inside its `mcpServers` object instead of replacing it.

```json
{
  "mcpServers": {
    "galaxygate": { "url": "https://mcp.galaxygate.net/mcp" },
    "runpod": { "url": "https://mcp.getrunpod.io/" }
  }
}
```

Save, restart Cursor, open Customize in the sidebar, then MCP. Each of the two servers shows Needs login. Click it, approve in the browser tab that opens, come back, and check the toggle next to each server is on.

**Cursor web.** At https://cursor.com/agents open the MCP dropdown, add each address as an HTTP server, and complete the sign-in each one asks for.

**Claude Code desktop or terminal.** In a terminal opened in `hackathon`:

```bash
claude mcp add -t http galaxygate https://mcp.galaxygate.net/mcp
claude mcp add -t http runpod https://mcp.getrunpod.io/
```

Then start `claude` in that same folder, type `/mcp`, and complete the sign-in for each server. The servers are saved for this folder, so always start Claude Code from it.

**Claude Code web.** At https://claude.ai open Customize, then Connectors, then Add custom connector. Paste one address, save, and sign in when asked; repeat for the second. Then in https://claude.ai/code start a session on your repository and turn both connectors on for it. In the session's environment settings set network access to Full so the checks in step 5 can reach your server.

**Codex.** In a terminal opened in `hackathon`:

```bash
codex mcp add galaxygate --url https://mcp.galaxygate.net/mcp
codex mcp login galaxygate
codex mcp add runpod --url https://mcp.getrunpod.io/
codex mcp login runpod
```

Codex blocks network access from commands unless you allow it. Add these lines to `~/.codex/config.toml` (create the file if it is missing), then start `codex`:

```toml
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

**Check.** Paste this into your tool: `Call the GalaxyGate list_workspaces tool and the RunPod list-endpoints tool and show me both results.` You should see one GalaxyGate workspace with your name on it, and a RunPod endpoint list, which may be empty. If either call is denied, redo the sign-in for that server.

### 5. Create your server, your GPU endpoint, and the demo

Replace `yourteam` with your team name: 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. Replace the key. Then paste the whole block into your tool.

```text
TEAM_NAME=yourteam
RUNPOD_API_KEY=rpa_paste-your-key-here

Fetch https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md, with curl if you have no tool for web pages, and follow it step by step. Stop and tell me if it does not load.
```

If your tool cannot open web pages, open https://github.com/GalaxyGate/philly-hackathon/blob/main/AGENT.md yourself, copy its whole text, and paste it under the two lines instead.

The agent creates your GalaxyGate server, installs Docker and builds the demo on it, creates a vision-model endpoint on RunPod under your account, deploys the demo with a public name, runs one real generation, and writes `HACKATHON.md` in your folder with every id you will need. The build and the first generation each take a few minutes. The first generation downloads the model onto the GPU and takes several minutes; later ones are much faster.

Stay with the laptop while this runs. Cursor, Claude Code and Codex all stop and wait for you to approve the commands that reach your own server, and none of them says anything while it waits. If you come back to a screen that has not moved, look for an approval prompt before you assume something broke.

Done when the agent reports that the health check and one real generation passed and gives you your URL, and that URL opens on your phone.

A note on the key. Pasting a secret into an agent chat is bad practice: it lands in the chat history, in tool-call logs, and in the app's environment on your server, where anyone in your GalaxyGate workspace can see it. For this event it is acceptable because the key only holds $15 of credit that you can revoke in the RunPod console the moment the event ends. Keep the workspace to your team, and revoke the key after the event.

## Part 2. Build

### The one rule

Your app, its data, and your RunPod key live on your GalaxyGate server. Your app's backend calls RunPod over HTTPS. Never call RunPod from browser JavaScript, and never put the key in your repository. Your public URL passes through a proxy that drops any response with no bytes for 100 seconds, so a slow GPU call must stream or send progress bytes while it waits; the demo does this.

### The demo: Sketch to Site

Open your URL on your phone. Photograph a website sketch drawn on paper or a whiteboard, add a line of notes if you like, and press Build the page. A vision model on your RunPod endpoint turns the photo into a complete web page, your server saves it, and you get a link and a QR code to the live page. Every page you build is listed at `/sites` on your server. As shipped, the app keeps its pages on the `/data` mount, so a redeploy keeps them.

### Change the demo, or start your own app

The demo running on your server is `demos/sketch` in https://github.com/GalaxyGate/philly-hackathon. Fork that repository into your GitHub account. In Cursor desktop, Claude Code desktop, or Codex, tell your agent: `Clone https://github.com/<your GitHub username>/philly-hackathon into this folder and work in demos/sketch.` On Claude Code web or a Cursor cloud agent, start a new session on your fork instead and turn both MCP connections on for it; paste the contents of `HACKATHON.md` from your first session into the new one. Edit whatever you like, or add a new app folder next to the demos. Push your changes to your fork; the server builds from there.

To put your changes on your server, tell your agent: `Fetch https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md and follow its step 12 for https://github.com/<your GitHub username>/philly-hackathon and folder demos/sketch.` The agent has your server clone your fork, build the image into a registry that runs on the server, and switch the app to it. If the agent cannot find `HACKATHON.md`, paste its contents into the chat. Ask `Show me the app logs` when something is wrong, and `Restart the app` to restart it.

### Use a GPU model from your app

Your own endpoint. Your agent already created a serverless endpoint named `hackathon-vl` running `Qwen/Qwen2.5-VL-7B-Instruct`, a vision-language model that reads images and text. Your app calls it at `https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1/chat/completions` exactly like the OpenAI chat API, with your RunPod key, and an image goes in as an `image_url` content part holding a `data:image/jpeg;base64,...` URL. To run a different Hugging Face model, tell your agent: `Using the RunPod MCP, create a serverless endpoint named hackathon-llm with image runpod/worker-v1-vllm:v2.27.0 on the ADA_24 pool, container disk 80 GB, workers min 0 max 1, idle timeout 60, env MODEL_NAME=<model> and MAX_MODEL_LEN=8192, then show me the endpoint id.` Call it from your app at `https://api.runpod.ai/v2/<that id>/openai/v1/chat/completions` the same way. The first request after a quiet period waits while the model loads; give your app's call at least fifteen minutes, as the demo does, and stream or send progress bytes while it waits.

Ready-made models, no deployment. Tell your agent: `Add a route to my app that generates an image with RunPod's Flux Schnell public endpoint using the RUNPOD_API_KEY from the environment, saves the image under /data, and shows it on a page.` The endpoint is `https://api.runpod.ai/v2/black-forest-labs-flux-1-schnell/runsync`; it takes `{"input":{"prompt":"...","width":768,"height":768}}` with the key as a bearer token, width and height between 256 and 1536 and divisible by 64, and returns the image URL at `output.image_url`. Text-to-speech, text models, and other ready-made models are listed at https://docs.runpod.io/public-endpoints/overview.

### Spending

The demo app caps itself at 20 generations per hour so a stranger cannot drain your credit; the cap is the `MAX_GENERATIONS_PER_HOUR` environment variable, and it counts every visitor together. Open `/api/usage` on your URL to see what is left, and ask your agent to raise the cap for the judging window if you used it up testing. Keep a cap in anything you build. Your endpoint scales to zero when idle. It bills for the whole time a worker is running, including the model load and the idle minute after a request. The first request after a quiet period is slow while the model loads, so send one generation through your app yourself right before a judge tries it. Check your RunPod balance in the console before you submit.

## Part 3. Submit

### Required to be judged in this track

- Your app runs on a GalaxyGate server created during the build period, and a judge can open it.
- Your app does its GPU work on RunPod, and a judge's own input produces a RunPod request you can show (the request in your RunPod console, or the `id` from the RunPod response).
- The organizers' starter code and RunPod's public models are allowed; say what you reused.
- Fabricated evidence, including a faked RunPod call, removes the project from this track.

Both integrations are the entry ticket. Having them earns nothing; how well your app uses them is what the points below measure.

### Devpost

Submit at https://coffee-and-code-agent.devpost.com/ before the deadline shown there, and select the GalaxyGate prize. Alongside the standard fields, give judges:

- Your app URL, one exact input to try, and your GalaxyGate instance id and app id (all in `HACKATHON.md`).
- Your RunPod endpoint id or the public model you used, plus one request record as above.
- Your repository, the commit you started from, the commit you submitted, and a short list of what you changed or built.
- A video under three minutes and a README that lets a stranger run it. Check both open in a browser where you are signed out.
Do not include environment screens, API keys, private keys, or credit links in anything you submit.

### Scoring, 100 points plus up to 15 extra

Judges score live, using their own inputs, not your demo input.

- **It works, 30.** The judge's first input produces the promised result (15). A second, different input also works (10). Nothing in the judge's session ends in a crash, a blank screen, or a spinner that never resolves (5); an upstream failure the app reports clearly does not count against this.
- **Simple to use, 20.** A first-time user completes the core task with no instructions (10). The screen always says what is happening: loading, GPU waking up, done, failed (5). The README gets a stranger running in one read (5).
- **Reliable, 15.** Results survive a page reload and a second run (5). A slow GPU start or an upstream error is shown to the user instead of a hang or a blank page (5). Paid routes have a cap or a login so a stranger cannot drain your credit (5).
- **Secure, 15.** Secrets exist only in the server's environment, not in the repository, logs, or screenshots (5). The browser never calls RunPod directly; only your server does (5). The key in the app's environment is no broader than the app needs, and revoking it breaks nothing else (5); the single `All` key from setup used for both setup and the app scores 2 of 5.
- **Scalable, 10.** GPU work runs on a RunPod endpoint that scales to zero and can add workers (5). App state lives outside the container (a mount or a database) so a redeploy keeps it (5).
- **Agentic, 10.** The app itself decides what to do next using model output or tools, not a single fixed call; the judge can see at least one such decision (10).

Extra credit, up to 15 points on top:

- **More of GalaxyGate, 5 each, up to 10.** A second server doing real work, private networking between servers, a floating IP, a scheduled backup or snapshot, or a load balancer, each used for a reason the judge can see.
- **More of RunPod, 5.** A second endpoint or model, a network volume, or a pod used for training or a batch job, used for a reason the judge can see.

Ties break on Simple to use, then Reliable. If your app is down when judges reach you, you have the rest of the judging window to bring it back; an app that never comes back misses the first requirement above and is not judged in this track. If it comes back, a timestamped end-to-end recording covers only the Secure, Scalable and Agentic points, because every other category is scored from a judge's own input.

## When something fails

- **An MCP server shows Needs login or a tool call is denied.** Redo that server's sign-in: Cursor desktop in Customize, MCP; Cursor web in the MCP dropdown; Claude Code desktop with `/mcp`; Claude Code web in Customize, Connectors; Codex with `codex mcp login <name>`.
- **The agent stopped in the middle, or your session ended.** Paste the block from step 5 again, with the same team name and the same key, in a new chat. The instructions find the server, the endpoint and the app you already have and carry on. Do not change your team name, and do not ask the agent to delete anything first.
- **The agent says the server never became ready.** Ask it to run `get_instance` and show the state. Bring it to the GalaxyGate table.
- **The first app deploy sticks or fails.** The agent instructions recover once on their own. If it fails twice, ask the agent for the workflow state and its failed children and bring them to the table.
- **The generation shows an error mentioning 401.** The key was not substituted or is wrong. Create a new key and ask the agent to update the app's environment, keeping every existing variable.
- **RunPod answers 402.** Your credit is gone. Check the console.
- **A generation fails or times out after a few minutes.** The first request after a quiet period loads the model onto the GPU. Wait two minutes, then send exactly one more. If that also fails, ask the agent to read the app logs and bring the error text to the GalaxyGate table.

When you ask for help, bring: your tool, the step you were on, the ids from `HACKATHON.md`, and the exact error text with your key removed.

## After the event

Delete the server from the GalaxyGate panel or ask your agent to, delete the `hackathon-vl` endpoint in the RunPod console, revoke the `hackathon-app` key there, and check that no other endpoint you created still has workers running.
