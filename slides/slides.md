---
theme: default
colorSchema: dark
title: GalaxyGate + RunPod track
aspectRatio: 16/9
---

<div class="cover">
<div class="cover-text">

# GalaxyGate + RunPod track

<p class="sub">Scan for the written guide</p>
<p class="url">https://github.com/GalaxyGate/philly-hackathon</p>

</div>
<div class="qr-tile"><img src="/qr-guide.png" /></div>
</div>

---

# Before you start

<div class="body">

- A laptop you can install software on
- A GitHub account
- An email inbox you can open now
- If you are a team, one teammate does Part 1 and shares the resulting URL and repository with the others
- If you are following this from Discord and not at the venue, post in the Discord at https://discord.com/invite/HP4BhW3hnp and an organizer will send you the GalaxyGate coupon code and your RunPod credit link.

</div>

---

# Step 1. Make a folder, pick one tool

<div class="body sm">

- Create an empty folder on your Desktop named `hackathon`. Everything below happens in that folder.
- Pick one tool. If you have none, pick Cursor.
- **Cursor.** Download from https://cursor.com/download, sign in, then File, Open Folder, and choose `hackathon`. If you received a Cursor credit code card at the GalaxyGate table, redeem it at the link on the card before you continue.
- **Claude Code.** Needs a paid Claude plan; if you do not have one, pick Cursor.
- **Codex.** Needs a paid ChatGPT plan; if you do not have one, pick Cursor.

</div>


---

# Step 1, continued. Open a terminal

<div class="body">

- **Windows.** Right-click the `hackathon` folder, choose Open in Terminal. Also install Git for Windows from https://git-scm.com/downloads/win once with its default options; your coding agent runs the setup commands through it.
- **macOS.** Open Terminal from Spotlight, type `cd ` with a space, drag the `hackathon` folder onto the Terminal window, press Enter. The prompt now ends in `hackathon`.
- Terminal commands in this guide are typed in a terminal. Prompts are pasted into the tool's chat.

</div>


---

# Step 1, continued. Install Claude Code

<div class="body sm">

<p class="cap">In a terminal opened in <code>hackathon</code> run the installer. On macOS:</p>

<pre class="code"><span class="l"><span class="nb">curl</span> <span class="nb">-fsSL</span> <span class="nb">https://claude.ai/install.sh</span> <span class="nb">|</span> <span class="nb">bash</span></span></pre>

<p class="cap">On Windows in PowerShell:</p>

<pre class="code"><span class="l"><span class="nb">irm</span> <span class="nb">https://claude.ai/install.ps1</span> <span class="nb">|</span> <span class="nb">iex</span></span></pre>

<p class="cap">(your prompt starts with <code>PS</code> in PowerShell)</p>

<p class="cap">Open a new terminal in <code>hackathon</code>, run <code>claude</code>, and sign in when it asks.</p>

</div>

<!--
Cursor and Codex users skip this slide.
-->

---

# Step 1, continued. Install Codex

<div class="body sm">

<p class="cap">In a terminal opened in <code>hackathon</code> run the installer. On macOS:</p>

<pre class="code"><span class="l"><span class="nb">curl</span> <span class="nb">-fsSL</span> <span class="nb">https://chatgpt.com/codex/install.sh</span> <span class="nb">|</span> <span class="nb">sh</span></span></pre>

<p class="cap">On Windows in PowerShell:</p>

<pre class="code"><span class="l"><span class="nb">irm</span> <span class="nb">https://chatgpt.com/codex/install.ps1</span> <span class="nb">|</span> <span class="nb">iex</span></span></pre>

<p class="cap">Open a new terminal in <code>hackathon</code>, run <code>codex</code>, and sign in when it asks.</p>

</div>

<!--
Cursor and Claude Code users skip this slide.
-->

---

# Step 2. GalaxyGate account

<div class="body sm">

1. Open https://dash.galaxygate.net/-/register. If the coupon box is empty, type the coupon code from the GalaxyGate table or from the organizer on Discord.
2. Open the verification email and click the link. Check your spam folder if it is not there within a minute.
3. Sign in at https://dash.galaxygate.net. You should see one workspace and no servers.

<p class="cap">If you already had a GalaxyGate account before the event, sign in and ask at the GalaxyGate table to apply the coupon.</p>

<div class="shotwrap"><img src="/gg-coupon.png" class="shot" /></div>

</div>


---

# Step 3. RunPod account and one API key

<div class="body sm">

1. Sign up at https://console.runpod.io/signup.
2. Open your RunPod credit link and redeem it. Your balance should read $15.
3. In the console open Settings, expand API Keys, click Create API Key. Name it `hackathon-app`, choose the permission `All`, create it, and copy the key now. RunPod shows it only once. You paste it into the prompt in step 6.

<p class="cap">This key can spend your credit. It goes into your app’s environment on your server, never into your code or your repository. Revoke it on the same page after the event.</p>

</div>


---

# Step 4. MCP servers in Cursor

<div class="body sm">

<p class="cap">Both servers sign you in through a browser window. There is no key to paste for this step.</p>

<p class="cap">In Cursor’s Explorer sidebar click New File, type <code>.cursor/mcp.json</code> as the whole file name, press Enter, and paste this. Do not try to create the <code>.cursor</code> folder in File Explorer or Finder; they refuse names starting with a dot. If the file already exists, add the two entries inside its <code>mcpServers</code> object instead of replacing it.</p>

<pre class="code"><span class="l"><span class="nb">{</span></span>
<span class="l">&nbsp;&nbsp;<span class="nb">"mcpServers":</span> <span class="nb">{</span></span>
<span class="l">&nbsp;&nbsp;&nbsp;&nbsp;<span class="nb">"galaxygate":</span> <span class="nb">{</span> <span class="nb">"url":</span> <span class="nb">"https://mcp.galaxygate.net/mcp"</span> <span class="nb">},</span></span>
<span class="l">&nbsp;&nbsp;&nbsp;&nbsp;<span class="nb">"runpod":</span> <span class="nb">{</span> <span class="nb">"url":</span> <span class="nb">"https://mcp.getrunpod.io/"</span> <span class="nb">}</span></span>
<span class="l">&nbsp;&nbsp;<span class="nb">}</span></span>
<span class="l"><span class="nb">}</span></span></pre>

</div>

<!--
Claude Code and Codex users skip this slide.
-->

---

# Step 4. Cursor sign-in

<div class="body">

1. Save and restart Cursor.
2. Open Customize in the sidebar, then MCP.
3. Each of the two servers shows Needs login. Click it, approve in the browser tab that opens, come back.
4. Check the toggle next to each server is on.

</div>

<!--
Claude Code and Codex users skip this slide.
-->

---

# Step 4. MCP servers in Claude Code

<div class="body sm">

<p class="cap">Both servers sign you in through a browser window. There is no key to paste for this step. In a terminal opened in <code>hackathon</code>:</p>

<pre class="code tighter"><span class="l"><span class="nb">claude</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">--transport</span> <span class="nb">http</span> <span class="nb">--scope</span> <span class="nb">user</span> <span class="nb">galaxygate</span> <span class="nb">https://mcp.galaxygate.net/mcp</span></span>
<span class="l"><span class="nb">claude</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">--transport</span> <span class="nb">http</span> <span class="nb">--scope</span> <span class="nb">user</span> <span class="nb">runpod</span> <span class="nb">https://mcp.getrunpod.io/</span></span></pre>

<p class="cap">Then start <code>claude</code>, type <code>/mcp</code>, and complete the sign-in for each server.</p>

</div>

<!--
Cursor and Codex users skip this slide.
-->

---

# Step 4. MCP servers in Codex

<div class="body sm">

<p class="cap">Both servers sign you in through a browser window. There is no key to paste for this step. In a terminal opened in <code>hackathon</code>:</p>

<pre class="code"><span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">galaxygate</span> <span class="nb">--url</span> <span class="nb">https://mcp.galaxygate.net/mcp</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">login</span> <span class="nb">galaxygate</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">runpod</span> <span class="nb">--url</span> <span class="nb">https://mcp.getrunpod.io/</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">login</span> <span class="nb">runpod</span></span></pre>

</div>

<!--
Cursor and Claude Code users skip this slide.
-->

---

# Step 4. Start Codex for this project

<div class="body sm">

<p class="cap">Codex blocks network access inside its sandbox by default, and the setup prompt needs SSH. Start Codex for this project with:</p>

<pre class="code tight"><span class="l"><span class="nb">codex</span> <span class="nb">--sandbox</span> <span class="nb">workspace-write</span> <span class="nb">-c</span> <span class="nb">sandbox_workspace_write.network_access=true</span></span></pre>

<p class="cap">Codex will ask permission the first time the agent writes the SSH key and connects to your server; approve those requests. Do not turn the sandbox off.</p>

</div>

<!--
Cursor and Claude Code users skip this slide.
-->

---

# Step 4. Check the connection

<div class="body">

<pre class="code"><span class="l"><span class="nb">Call</span> <span class="nb">the</span> <span class="nb">GalaxyGate</span> <span class="nb">list_workspaces</span> <span class="nb">tool</span> <span class="nb">and</span> <span class="nb">the</span> <span class="nb">RunPod</span> <span class="nb">list-endpoints</span> <span class="nb">tool</span> <span class="nb">and</span> <span class="nb">show</span> <span class="nb">me</span> <span class="nb">both</span> <span class="nb">results.</span></span></pre>

<div>

- You should see one GalaxyGate workspace with your name on it, and a RunPod endpoint list, which may be empty
- If either call is denied, redo the sign-in for that server

</div>

</div>


---

# Step 5. Windows only: SSH

<div class="body sm">

<p class="cap">This check is for your own terminal; your agent runs its commands through Git Bash, which brings its own SSH.</p>

1. In a terminal opened in `hackathon` run `ssh -V`. If it prints a version, skip ahead.
2. Otherwise open PowerShell as administrator (Start, type PowerShell, right-click, Run as administrator), run this, wait for it to finish, close that window, and run `ssh -V` in your normal terminal again.

<pre class="code"><span class="l"><span class="nb">Add-WindowsCapability</span> <span class="nb">-Online</span> <span class="nb">-Name</span> <span class="nb">OpenSSH.Client~~~~0.0.1.0</span></span></pre>

<p class="cap">(the name contains four tildes)</p>

<p class="cap">macOS and Linux already have SSH.</p>

</div>

<!--
macOS and Linux users skip this slide.
-->

---

# Step 6. Create your server: paste this

<div class="body sm">

<pre class="code tight"><span class="l"><span class="nb">TEAM_NAME=yourteam</span></span>
<span class="l"><span class="nb">RUNPOD_API_KEY=rpa_paste-your-key-here</span></span>
<span class="l"></span>
<span class="l"><span class="nb">Read</span> <span class="nb">https://raw.githubusercontent.com/GalaxyGate/philly-hackathon/main/AGENT.md</span> <span class="nb">and</span> <span class="nb">follow</span> <span class="nb">it</span> <span class="nb">step</span> <span class="nb">by</span> <span class="nb">step.</span> <span class="nb">Stop</span> <span class="nb">and</span> <span class="nb">tell</span> <span class="nb">me</span> <span class="nb">if</span> <span class="nb">the</span> <span class="nb">page</span> <span class="nb">does</span> <span class="nb">not</span> <span class="nb">load.</span></span></pre>

<p class="cap">Replace <code>yourteam</code> with your team name: 3 to 32 characters, lowercase letters, digits, and hyphens only, starting and ending with a letter or digit. Replace the key.</p>

<p class="cap">If your tool cannot open web pages, open <span class="nb">https://github.com/GalaxyGate/philly-hackathon/blob/main/AGENT.md</span> yourself, copy its whole text, and paste it under the two lines instead.</p>

</div>

<!--
Then paste the whole block into your tool.
-->

---

# Done when

<div class="body sm">

- The agent reports that both checks passed and gives you your URL, and that URL opens in your browser and roasts a public GitHub repository when you paste one
- It writes `HACKATHON.md` in your folder with every id you will need

<div class="shotwrap"><img src="/roast-input.png" class="shot" /></div>

</div>


---

# Build: the one rule

<div class="body sm">

- Your app, its data, and your RunPod key live on your GalaxyGate server.
- Your app's backend calls RunPod over HTTPS.
- Never call RunPod from browser JavaScript, and never put the key in your repository.
- Your RunPod key is now in your agent's chat history and in the app's environment on your server, where anyone in your GalaxyGate workspace can see it. Keep the workspace to your team and revoke the key after the event.
- Your SSH key is in the `.hackathon` folder inside your project; it is listed in `.gitignore`, so it stays out of your repository.

</div>


---

# Fork and clone

<div class="body sm">

<p class="cap">The demo running on your server is <code>demos/roast</code> in <span class="nb">https://github.com/GalaxyGate/philly-hackathon</span>. Fork that repository into your GitHub account, then tell your agent:</p>

<pre class="code tight"><span class="l"><span class="nb">Clone</span> <span class="nb">https://github.com/&lt;your GitHub username&gt;/philly-hackathon</span> <span class="nb">into</span> <span class="nb">this</span> <span class="nb">folder.</span></span></pre>

<p class="cap">Edit whatever you like, or add a new app folder next to the demos.</p>

<p class="cap">As shipped, the demo forgets its roast when the page reloads; keeping results across a reload is worth 5 scoring points.</p>

</div>


---

# Redeploy your changes

<div class="body">

<p class="cap">To put your changes on your server, tell your agent:</p>

<pre class="code"><span class="l"><span class="nb">Follow</span> <span class="nb">the</span> <span class="nb">redeploy</span> <span class="nb">section</span> <span class="nb">of</span> <span class="nb">AGENT.md</span> <span class="nb">for</span> <span class="nb">demos/roast.</span></span></pre>

<p class="cap">The agent copies the folder to your server over SSH, builds the image there into a registry that runs on the server, and switches the app to it. On Windows this needs Git for Windows.</p>

<p class="cap">Ask <code>Show me the app logs</code> when something is wrong, and <code>Restart the app</code> to restart it.</p>

</div>


---

# Use a GPU model: ready-made

<div class="body sm">

<pre class="code"><span class="l"><span class="nb">Add</span> <span class="nb">a</span> <span class="nb">route</span> <span class="nb">to</span> <span class="nb">my</span> <span class="nb">app</span> <span class="nb">that</span> <span class="nb">generates</span> <span class="nb">an</span> <span class="nb">image</span> <span class="nb">with</span> <span class="nb">RunPod's</span> <span class="nb">Flux</span> <span class="nb">Schnell</span> <span class="nb">public</span> <span class="nb">endpoint</span> <span class="nb">using</span> <span class="nb">the</span> <span class="nb">RUNPOD_API_KEY</span> <span class="nb">from</span> <span class="nb">the</span> <span class="nb">environment,</span> <span class="nb">saves</span> <span class="nb">the</span> <span class="nb">image</span> <span class="nb">under</span> <span class="nb">/data,</span> <span class="nb">and</span> <span class="nb">shows</span> <span class="nb">it</span> <span class="nb">on</span> <span class="nb">a</span> <span class="nb">page.</span></span></pre>

<p class="cap">The endpoint is <code>https://api.runpod.ai/v2/black-forest-labs-flux-1-schnell/runsync</code>; it takes <code>{"input":{"prompt":"...","width":768,"height":768}}</code> with the key as a bearer token, width and height between 256 and 1536 and divisible by 64, and returns the image URL at <code>output.image_url</code>.</p>

<p class="cap">Other ready-made models, including Qwen for text, are listed at <span class="nb">https://docs.runpod.io/public-endpoints/overview</span>.</p>

</div>

---

# Use a GPU model: your Hugging Face model

<div class="body sm">

<pre class="code"><span class="l"><span class="nb">Using</span> <span class="nb">the</span> <span class="nb">RunPod</span> <span class="nb">MCP,</span> <span class="nb">call</span> <span class="nb">list-endpoints</span> <span class="nb">and</span> <span class="nb">stop</span> <span class="nb">if</span> <span class="nb">an</span> <span class="nb">endpoint</span> <span class="nb">named</span> <span class="nb">hackathon-llm</span> <span class="nb">exists.</span> <span class="nb">Otherwise</span> <span class="nb">call</span> <span class="nb">deploy-hub-repo</span> <span class="nb">with</span> <span class="nb">repo</span> <span class="nb">runpod-workers/worker-vllm,</span> <span class="nb">name</span> <span class="nb">hackathon-llm,</span> <span class="nb">gpuIds</span> <span class="nb">ADA_24,</span> <span class="nb">workersMin</span> <span class="nb">0,</span> <span class="nb">workersMax</span> <span class="nb">1,</span> <span class="nb">idleTimeout</span> <span class="nb">60,</span> <span class="nb">and</span> <span class="nb">env</span> <span class="nb">MODEL_NAME=Qwen/Qwen2.5-Coder-7B-Instruct</span> <span class="nb">and</span> <span class="nb">MAX_MODEL_LEN=8192.</span> <span class="nb">Then</span> <span class="nb">send</span> <span class="nb">one</span> <span class="nb">chat</span> <span class="nb">completion</span> <span class="nb">to</span> <span class="nb">it</span> <span class="nb">and</span> <span class="nb">show</span> <span class="nb">me</span> <span class="nb">the</span> <span class="nb">reply</span> <span class="nb">and</span> <span class="nb">the</span> <span class="nb">endpoint</span> <span class="nb">id.</span></span></pre>

<p class="cap">Your app then calls <code>https://api.runpod.ai/v2/&lt;ENDPOINT_ID&gt;/openai/v1/chat/completions</code> with your key and that model name. The first request after a quiet period waits while the model loads; keep your app’s timeout above two minutes.</p>

</div>


---

# Spending

<div class="body">

- The demo app caps itself at 25 generations per hour so a stranger cannot drain your credit.
- The cap is the `MAX_GENERATIONS_PER_HOUR` environment variable. Keep a cap in anything you build.
- The roast demo also makes two GitHub API calls per roast, and GitHub allows 60 per hour per server without a token.
- If you need more, ask your agent to add a `GITHUB_TOKEN` environment variable holding a fine&#8209;grained GitHub token with public read access, keeping every existing variable.

</div>


---

# Eligibility

<div class="body">

- Your GalaxyGate server and app were created during the build period. The organizers' starter code and RunPod's public models are allowed; say what you reused.
- Fabricated evidence, including a faked RunPod call, removes the project from this track.

</div>


---

# Submit on Devpost

<div class="body sm">

- Submit at https://coffee-and-code-agent.devpost.com/ before the deadline shown there, and select the GalaxyGate prize.
- Your app URL, GalaxyGate instance id and app id (all in `HACKATHON.md`), a screenshot of your workspace's Workflows page in the panel, and one exact input to try.
- Your RunPod endpoint id, or the public model you used, plus one request record: a screenshot of the request in your RunPod console, or the `id` field from one RunPod response.
- Your repository, the commit you started from, the commit you submitted, and a short list of what you changed or built.
- A video under three minutes and a README that lets a stranger run it. Check both open in a browser where you are signed out.
- Do not include environment screens, API keys, private keys, or credit links in anything you submit.
- Check your RunPod balance in the console before you submit.

</div>


---

# Scoring, 100 points

<div class="body sm">

- **Live app, 20.** The URL opens (5), a judge's fresh input succeeds (10), and the same result is still on screen after the judge reloads the page (5).
- **RunPod integration, 20.** A judge's fresh input produces a request visible in your RunPod console or a RunPod response `id` you show the judge (10), and your app visibly uses the model's result (10).
- **Agent-operated infrastructure, 15.** Your GalaxyGate workflow history shows an `instance.provision` (5), an `app.provision` (5), and either an `app.power` row or more `app.deploy` rows than `app.provision` rows (5), because each provision brings exactly one `app.deploy` of its own, every later redeploy adds an `app.deploy`, and every restart adds an `app.power`. All rows must fall inside the build period. The panel shows them on your workspace's Workflows page; screenshot it.

</div>


---

# Scoring, continued

<div class="body sm">

- **Agentic usefulness, 25.** A stated user task with a clear success condition (5), a page or log the judge can open that shows each model decision and each tool result and grows when the judge submits their own input (10), success on that judge-supplied input (5), and one honestly demonstrated limitation (5). A single fixed model call earns no action points.
- **Reliability, safety, cost, 15.** Secrets kept out of the repository, logs, and screenshots (5), paid routes protected by a cap or login (5), a slow start or upstream error handled visibly (5).
- **Submission, 5.** Video (2), README (2), the disclosures above (1).
- Ties break on agentic usefulness, then reliability. If your app is down when judges test it, a timestamped end-to-end recording counts for everything except the live-app points.

</div>


---

# When something fails

<div class="body">

- **An MCP server shows Needs login or a tool call is denied.** Redo that server's sign-in: Cursor in Customize, MCP; Claude Code with `/mcp`; Codex with `codex mcp login <name>`.
- **The agent says the server never became ready.** Ask it to run `get_instance` and show the state, and `cloud-init status --long` over SSH. Bring both to the GalaxyGate table.
- **The first app deploy sticks or fails.** The agent instructions recover once on their own. If it fails twice, ask the agent for the workflow state and its failed children and bring them to the table.

</div>


---

# When something fails, continued

<div class="body sm">

- **The roast shows an error mentioning 401.** The key was not substituted or is wrong. Create a new key and ask the agent to update the app's environment, keeping every existing variable.
- **RunPod answers 402.** Your credit is gone. Check the console.
- **A generation hangs.** Ask the agent to read the app logs and, for your own endpoint, the endpoint's workers in the RunPod console. Do not resend the same request repeatedly.
- Your agent can print your workflow rows with `list_workspace_workflows`, and if a row has scrolled off, with `panel_request` GET `/v1/workspaces/<id>/workflows` and params `{"name": "instance.provision"}`.
- When you ask for help, bring: your tool, the step you were on, the ids from `HACKATHON.md`, and the exact error text with your key removed.
- Help: the GalaxyGate table, or the hackathon Discord at https://discord.com/invite/HP4BhW3hnp

</div>


---

# After the event

<div class="body">

- Delete the server from the GalaxyGate panel, or ask your agent to delete it.
- Revoke the `hackathon-app` key in the RunPod console.
- Check that no RunPod endpoint you created still has workers running.

</div>

