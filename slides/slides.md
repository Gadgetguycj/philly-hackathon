---
theme: default
colorSchema: dark
title: GalaxyGate + RunPod track
aspectRatio: 16/9
---

<div class="cover">
<div class="cover-text">

# GalaxyGate + RunPod track

<p class="sub">Scan for the guide</p>
<p class="url">https://github.com/GalaxyGate/philly-hackathon</p>
<p class="url2">Coffee &amp; Code AI Agent Hackathon</p>

</div>
<div class="qr-tile"><img src="/qr-guide.png" /></div>
</div>

---

# Before you start

<div class="body sm">

- A laptop, a GitHub account, and an email inbox you can open now.
- One teammate does Part 1 and shares the URL and repository with the rest.
- **Cursor.** Desktop from https://cursor.com/download, or web at https://cursor.com/agents with a paid plan. Redeem a Cursor credit card from our table first.
- **Claude Code.** Desktop app or terminal, or web at https://claude.ai/code on a repository of yours.
- **Codex.** Terminal, opened in that folder; step 4 is written for the terminal. Codex on the web cannot connect MCP servers.
- Work in an empty folder named `hackathon`.

<p class="cap">If you have none of these, use Cursor.</p>

</div>

---

# Step 2. GalaxyGate account

<div class="body sm">

1. Open https://dash.galaxygate.net/-/register. If the coupon box is empty, type the coupon code from the GalaxyGate table.
2. Open the verification email and click the link. Check spam if it does not arrive within a minute.
3. Sign in at https://dash.galaxygate.net. You should see one workspace and no servers.

<p class="cap">If you already had a GalaxyGate account before the event, sign in and ask at the GalaxyGate table to apply the coupon.</p>

<div class="shotwrap"><img src="/gg-coupon.png" class="shot" /></div>

</div>

---

# Step 3. RunPod account and one API key

<div class="body sm">

1. Sign up at https://console.runpod.io/signup.
2. Open the RunPod credit link from your check-in email, redeem it, and check the balance.
3. Settings, API Keys, Create API Key. Name it `hackathon-app`, permission `All`, and copy it now. RunPod shows it once. It goes into the prompt in step 5.

<p class="cap">The key lives in your app’s environment on your server, never in your code or repository. It also lands in the chat history and in tool-call logs, so keep the workspace to your team.</p>

<p class="cap">The agent needs <code>All</code> once, to create your endpoint. A second, narrower key for the app scores better on Secure.</p>

</div>

---

# Cursor: MCP servers

<div class="body sm">

<p class="cap">Both servers sign you in through a browser window. There is no key to paste. The two addresses are <code>https://mcp.galaxygate.net/mcp</code> and <code>https://mcp.getrunpod.io/</code>.</p>

<p class="cap">Desktop. In Cursor’s Explorer sidebar click New File, type <code>.cursor/mcp.json</code> as the whole file name, press Enter, and paste this. File Explorer and Finder refuse names starting with a dot. If the file already exists, add the two entries inside its <code>mcpServers</code> object.</p>

<pre class="code"><span class="l"><span class="nb">{</span></span>
<span class="l">  <span class="nb">"mcpServers":</span> <span class="nb">{</span></span>
<span class="l">    <span class="nb">"galaxygate":</span> <span class="nb">{</span> <span class="nb">"url":</span> <span class="nb">"https://mcp.galaxygate.net/mcp"</span> <span class="nb">},</span></span>
<span class="l">    <span class="nb">"runpod":</span> <span class="nb">{</span> <span class="nb">"url":</span> <span class="nb">"https://mcp.getrunpod.io/"</span> <span class="nb">}</span></span>
<span class="l">  <span class="nb">}</span></span>
<span class="l"><span class="nb">}</span></span></pre>

</div>

<!--
Skip if the room has already picked a tool.
-->

---

# Cursor: sign in

<div class="body">

- Save, restart Cursor, open Customize, then MCP.
- Each server shows Needs login. Click it, approve in the browser tab, and check its toggle is on.
- While the agent works, Cursor asks you to approve commands that reach your server. Approve them as they appear.
- Setup has long waits, so stay at the laptop. If you walk away, Cursor stops at the first prompt and waits without saying so.
- Web. At https://cursor.com/agents add each address as an HTTP server in the MCP dropdown, and sign in.

</div>

<!--
Skip if the room has already picked a tool.
-->

---

# Claude Code: MCP servers

<div class="body sm">

<p class="cap">Desktop or terminal. In a terminal opened in <code>hackathon</code>:</p>

<pre class="code"><span class="l"><span class="nb">claude</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">--transport</span> <span class="nb">http</span> <span class="nb">--scope</span> <span class="nb">user</span> <span class="nb">galaxygate</span> <span class="nb">https://mcp.galaxygate.net/mcp</span></span>
<span class="l"><span class="nb">claude</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">--transport</span> <span class="nb">http</span> <span class="nb">--scope</span> <span class="nb">user</span> <span class="nb">runpod</span> <span class="nb">https://mcp.getrunpod.io/</span></span></pre>

<p class="cap">Then start <code>claude</code>, type <code>/mcp</code>, and complete the sign-in for each server.</p>

<p class="cap">Web. At https://claude.ai open Customize, Connectors, Add custom connector; add each address and sign in. Then start a session on your repository at https://claude.ai/code, turn both connectors on, and set network access to Full.</p>

</div>

<!--
Skip if the room has already picked a tool.
-->

---

# Codex: MCP servers

<div class="body sm">

<p class="cap">In a terminal opened in <code>hackathon</code>:</p>

<pre class="code"><span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">galaxygate</span> <span class="nb">--url</span> <span class="nb">https://mcp.galaxygate.net/mcp</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">login</span> <span class="nb">galaxygate</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">runpod</span> <span class="nb">--url</span> <span class="nb">https://mcp.getrunpod.io/</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">login</span> <span class="nb">runpod</span></span></pre>

<p class="cap">Codex blocks network access from commands unless you allow it. Add these two lines to <code>~/.codex/config.toml</code>, creating the file if it is missing, then start <code>codex</code>:</p>

<pre class="code"><span class="l"><span class="nb">[sandbox_workspace_write]</span></span>
<span class="l"><span class="nb">network_access</span> <span class="nb">=</span> <span class="nb">true</span></span></pre>

</div>

<!--
Skip if the room has already picked a tool.
-->

---

# Step 4. Check the connection

<div class="body">

<pre class="code"><span class="l"><span class="nb">Call</span> <span class="nb">the</span> <span class="nb">GalaxyGate</span> <span class="nb">list_workspaces</span> <span class="nb">tool</span> <span class="nb">and</span> <span class="nb">the</span> <span class="nb">RunPod</span> <span class="nb">list-endpoints</span> <span class="nb">tool</span> <span class="nb">and</span> <span class="nb">show</span> <span class="nb">me</span> <span class="nb">both</span> <span class="nb">results.</span></span></pre>

<div>

- One GalaxyGate workspace with your name on it, and a RunPod endpoint list, which may be empty.
- If either call is denied, redo the sign-in for that server.

</div>

</div>

---

# Step 5. Create your server: paste this

<div class="body sm">

<p class="cap">Replace <code>yourteam</code> with your team name: 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. Replace the key. Then paste the whole block into your tool.</p>

<pre class="code tight"><span class="l"><span class="nb">TEAM_NAME=yourteam</span></span>
<span class="l"><span class="nb">RUNPOD_API_KEY=rpa_paste-your-key-here</span></span>
<span class="l"></span>
<span class="l"><span class="nb">Fetch</span> <span class="nb">https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md,</span> <span class="nb">with</span> <span class="nb">curl</span> <span class="nb">if</span> <span class="nb">you</span> <span class="nb">have</span> <span class="nb">no</span> <span class="nb">tool</span> <span class="nb">for</span> <span class="nb">web</span> <span class="nb">pages,</span> <span class="nb">and</span> <span class="nb">follow</span> <span class="nb">it</span> <span class="nb">step</span> <span class="nb">by</span> <span class="nb">step.</span> <span class="nb">Stop</span> <span class="nb">and</span> <span class="nb">tell</span> <span class="nb">me</span> <span class="nb">if</span> <span class="nb">it</span> <span class="nb">does</span> <span class="nb">not</span> <span class="nb">load.</span></span></pre>

<p class="cap">If your tool cannot open web pages, open <span class="nb">https://github.com/GalaxyGate/philly-hackathon/blob/main/AGENT.md</span> yourself, copy its whole text, and paste it under the two lines instead.</p>

</div>

---

# Step 5. What the agent does

<div class="body sm">

- It creates your server, installs Docker and builds the demo on it, creates a vision-model endpoint on RunPod under your account, deploys the demo with a public name, runs one real generation, and writes `HACKATHON.md` with every id you need.
- The build and the first generation each take a few minutes. The first generation downloads the model onto the GPU; later ones take seconds.
- Done when the agent reports the health check and one real generation passed, and your URL opens on your phone.

</div>

---

# The one rule, and spending

<div class="body sm">

- Your app, its data, and your RunPod key live on your GalaxyGate server. Your app's backend calls RunPod over HTTPS.
- Never call RunPod from browser JavaScript, and never put the key in your repository.
- The proxy in front of your URL drops any response with no bytes for 100 seconds, so a slow GPU call must stream or send progress bytes. The demo does this.
- The demo caps itself at 20 generations per hour, in `MAX_GENERATIONS_PER_HOUR`, and the cap counts every visitor together. Open `/api/usage` on your URL to see what is left, and ask your agent to raise the cap for the judging window if you used it up testing. Keep a cap in anything you build.
- Your endpoint scales to zero, and bills for the whole time a worker runs, including the model load and the idle minute after a request.

</div>

---

# The demo: Sketch to Site

<div class="body">

<div class="withshot">
<div class="col">

- Open your URL on your phone. Photograph a sketch on paper or a whiteboard, add a line of notes, and press Build the page.
- A vision model on your RunPod endpoint turns the photo into a web page. You get a link and a QR code to the live page.
- Every page is listed at `/sites`, kept on the `/data` mount, so a redeploy keeps them.

</div>
<img src="/sketch-upload-top.png" class="phone" />
</div>

</div>

---

# Change the demo and redeploy

<div class="body sm">

<p class="cap">Fork the repository. In Cursor desktop, Claude Code desktop, or Codex:</p>

<pre class="code tight"><span class="l"><span class="nb">Clone</span> <span class="nb">https://github.com/&lt;your GitHub username&gt;/philly-hackathon</span> <span class="nb">into</span> <span class="nb">this</span> <span class="nb">folder</span> <span class="nb">and</span> <span class="nb">work</span> <span class="nb">in</span> <span class="nb">demos/sketch.</span></span></pre>

<p class="cap">On Claude Code web or a Cursor cloud agent, start a session on your fork, turn both MCP connections on, and paste in <code>HACKATHON.md</code>. Edit, push, then:</p>

<pre class="code tight"><span class="l"><span class="nb">Fetch</span> <span class="nb">https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md</span> <span class="nb">and</span> <span class="nb">follow</span> <span class="nb">its</span> <span class="nb">step</span> <span class="nb">12</span> <span class="nb">for</span> <span class="nb">https://github.com/&lt;your GitHub username&gt;/philly-hackathon</span> <span class="nb">and</span> <span class="nb">folder</span> <span class="nb">demos/sketch.</span></span></pre>

<p class="cap">Ask <code>Show me the app logs</code> when something is wrong, and <code>Restart the app</code> to restart it.</p>

</div>

---

# Use a GPU model

<div class="body sm">

<p class="cap">Your endpoint <code>hackathon-vl</code> runs <code>Qwen/Qwen2.5-VL-7B-Instruct</code>. Call <code>https://api.runpod.ai/v2/&lt;ENDPOINT_ID&gt;/openai/v1/chat/completions</code> like the OpenAI chat API, with the image as an <code>image_url</code> part holding a <code>data:image/jpeg;base64,...</code> URL. Keep your timeout above two minutes.</p>

<p class="cap">For a ready-made model with no deployment, tell your agent:</p>

<pre class="code"><span class="l"><span class="nb">Add</span> <span class="nb">a</span> <span class="nb">route</span> <span class="nb">to</span> <span class="nb">my</span> <span class="nb">app</span> <span class="nb">that</span> <span class="nb">generates</span> <span class="nb">an</span> <span class="nb">image</span> <span class="nb">with</span> <span class="nb">RunPod's</span> <span class="nb">Flux</span> <span class="nb">Schnell</span> <span class="nb">public</span> <span class="nb">endpoint</span> <span class="nb">using</span> <span class="nb">the</span> <span class="nb">RUNPOD_API_KEY</span> <span class="nb">from</span> <span class="nb">the</span> <span class="nb">environment,</span> <span class="nb">saves</span> <span class="nb">the</span> <span class="nb">image</span> <span class="nb">under</span> <span class="nb">/data,</span> <span class="nb">and</span> <span class="nb">shows</span> <span class="nb">it</span> <span class="nb">on</span> <span class="nb">a</span> <span class="nb">page.</span></span></pre>

<p class="cap">It posts <code>{"input":{"prompt":"...","width":768,"height":768}}</code> to <span class="nb">https://api.runpod.ai/v2/black-forest-labs-flux-1-schnell/runsync</span> and returns <code>output.image_url</code>. More: <span class="nb">https://docs.runpod.io/public-endpoints/overview</span></p>

</div>

<!--
Reference only. Do not present.
-->

---

# Required to be judged in this track

<div class="body sm">

- Your app runs on a GalaxyGate server created during the build period, and a judge can open it.
- Its GPU work runs on RunPod, and a judge's own input produces a request you can show: the RunPod console entry, or the `id` from the response.
- Starter code and RunPod's public models are allowed; say what you reused.
- Fabricated evidence, including a faked RunPod call, removes the project from this track.

<p class="cap">Both integrations are the entry ticket. They earn no points by themselves.</p>

</div>

---

# Submit on Devpost

<div class="body sm">

<p class="cap">Submit at <span class="nb">https://coffee-and-code-agent.devpost.com/</span> before the deadline shown there, select the GalaxyGate prize, and alongside the standard fields give judges:</p>

- Your app URL, one exact input to try, and the instance id and app id from `HACKATHON.md`.
- Your RunPod endpoint id or public model, plus one request record as above.
- Your repository, the commit you started from, the commit you submitted, and what you changed.
- A video under three minutes and a README that lets a stranger run it. Check both open signed out.

<p class="cap">Check your RunPod balance first. Do not include environment screens, API keys, private keys, or credit links.</p>

</div>

<!--
Reference only. Do not present.
-->

---

# Scoring, 100 points plus 15 extra

<div class="body sm">

<p class="cap">Judges score live, on their own inputs.</p>

- **It works, 30.** Their first input produces the promised result (15). A second, different input also works (10). No crash, blank screen, or endless spinner (5).
- **Simple to use, 20.** A first-timer completes the core task with no instructions (10). The screen always says what is happening (5). The README gets a stranger running in one read (5).
- **Reliable, 15.** Results survive a page reload and a second run (5). A slow start or upstream error is shown, not hidden (5). Paid routes have a cap or a login (5).

</div>

---

# Scoring, continued, and ties

<div class="body sm">

- **Secure, 15.** Secrets only in the server's environment (5). Only your server calls RunPod (5). The app's key is no broader than it needs (5); one `All` key for both setup and app scores 2 of 5.
- **Scalable, 10.** GPU work on an endpoint that scales to zero and can add workers (5). State outside the container, so a redeploy keeps it (5).
- **Agentic, 10.** The app decides what to do next from model output or tools, not one fixed call (10).
- **Extra credit, up to 15.** GalaxyGate, 5 each up to 10: a second server, private networking, a floating IP, a backup, a load balancer. RunPod, 5: a second endpoint, a network volume, or a pod.
- **Ties.** Simple to use, then Reliable. If your app is down when judges reach you, you have the rest of the judging window to bring it back; an app that never comes back is not judged in this track. If it comes back, a timestamped recording covers only the Secure, Scalable and Agentic points.

</div>

<!--
Reference only. Do not present.
-->

---

# When something fails

<div class="body sm">

- **Needs login, or a tool call denied.** Redo that server's sign-in: Cursor desktop in Customize, MCP; Cursor web in the MCP dropdown; Claude Code desktop with `/mcp`; Claude Code web in Customize, Connectors; Codex with `codex mcp login <name>`.
- **The server never became ready.** Ask the agent to run `get_instance` and show the state.
- **The first deploy sticks or fails.** The instructions recover once. If it fails twice, ask for the workflow state and its failed children.
- **An error mentioning 401.** The key was not substituted or is wrong. Create a new key and ask the agent to update the app's environment, keeping every existing variable.
- **402.** Your credit is gone. Check the console.
- **A generation fails after a few minutes.** The first request loads the model onto the GPU. Wait two minutes, then send exactly one more.

<p class="cap">Bring your tool, your step, the ids from <code>HACKATHON.md</code>, and the error text with your key removed. Help is at the GalaxyGate table.</p>

</div>

---

# After the event

<div class="body">

- Delete the server from the GalaxyGate panel or ask your agent to.
- Delete the `hackathon-vl` endpoint in the RunPod console.
- Revoke the `hackathon-app` key there.
- Check that no other endpoint you created still has workers running.

</div>
