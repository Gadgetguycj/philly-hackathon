---
theme: default
colorSchema: dark
title: GalaxyGate + RunPod track
aspectRatio: 16/9
fonts:
  provider: none
favicon: ./favicon.png
---

<div class="cover">
<div class="cover-text">

# GalaxyGate + RunPod track

<p class="sub">Scan for the guide</p>
<p class="url">runpodtrack.galaxygate.app</p>
<p class="url2">Coffee &amp; Code AI Agent Hackathon</p>

</div>
<div class="qr-tile"><img src="/qr-guide.png" /></div>
</div>

---

# Before you start

<div class="body">

<p class="cap">Do the account steps, open the section for your tool, then build.</p>

- A laptop, a GitHub account and an email inbox.
- One teammate sets up and shares the URL.
- Your team name is 3 to 32 characters, lowercase letters, digits and hyphens, starting and ending with a letter or digit.
- Setup takes a while, so stay at the laptop and watch for approval prompts.
- You are done when the health check and one generation pass and your URL opens on your phone.
- Help is at the GalaxyGate table.

</div>

---

# Accounts

<div class="body sm">

1. Register at https://dash.galaxygate.net/-/register with the coupon `PHILLYHACKATHON-60`, open the verification email, and sign in. An older account needs the coupon applied at the GalaxyGate table.
2. Sign up at https://console.runpod.io/signup, then claim your RunPod credit and enter the swag raffle at https://runpod.galaxygate.app.
3. In the RunPod console open Settings, API Keys, Create API Key. Name it `hackathon-app`, permission `All`, and copy it now, because RunPod shows it once. It belongs in your app’s environment, never in your repository.

<div class="shotwrap"><img src="/gg-coupon.png" class="shot" /></div>

</div>

---

# Using Claude Code

<div class="body sm">

<p class="cap">Open a terminal in a new empty folder named <code>hackathon</code> and connect the two MCP servers.</p>

<pre class="code tight"><span class="l"><span class="nb">claude</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">-t</span> <span class="nb">http</span> <span class="nb">galaxygate</span> <span class="nb">https://mcp.galaxygate.net/mcp</span></span>
<span class="l"><span class="nb">claude</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">-t</span> <span class="nb">http</span> <span class="nb">runpod</span> <span class="nb">https://mcp.getrunpod.io/</span></span></pre>

<p class="cap">Start <code>claude --permission-mode manual</code> there, type <code>/mcp</code>, and sign in to both servers. Always start Claude Code from this folder with that flag, so it asks you to approve each step instead of refusing one on its own.</p>

<p class="cap">Fill in your team name and key, then paste this.</p>

<pre class="code tight"><span class="l"><span class="nb">TEAM_NAME=yourteam</span></span>
<span class="l"><span class="nb">RUNPOD_API_KEY=rpa_paste-your-key-here</span></span>
<span class="l"></span>
<span class="l"><span class="nb">Fetch</span> <span class="nb">https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md</span> <span class="nb">and</span> <span class="nb">follow</span> <span class="nb">it</span> <span class="nb">step</span> <span class="nb">by</span> <span class="nb">step.</span> <span class="nb">Stop</span> <span class="nb">and</span> <span class="nb">tell</span> <span class="nb">me</span> <span class="nb">if</span> <span class="nb">it</span> <span class="nb">does</span> <span class="nb">not</span> <span class="nb">load.</span></span></pre>

</div>

<!--
Skip unless the room is on Claude Code.
-->

---

# Using Cursor

<div class="body sm">

<p class="cap">Install Cursor from https://cursor.com/download, sign in, and open a new empty folder named <code>hackathon</code>.</p>

<p class="cap">In Cursor’s Explorer click New File, type <code>.cursor/mcp.json</code> as the whole name, and paste this. If it exists, add both entries to its <code>mcpServers</code> object.</p>

<pre class="code"><span class="l"><span class="nb">{</span></span>
<span class="l">  <span class="nb">"mcpServers":</span> <span class="nb">{</span></span>
<span class="l">    <span class="nb">"galaxygate":</span> <span class="nb">{</span> <span class="nb">"url":</span> <span class="nb">"https://mcp.galaxygate.net/mcp"</span> <span class="nb">},</span></span>
<span class="l">    <span class="nb">"runpod":</span> <span class="nb">{</span> <span class="nb">"url":</span> <span class="nb">"https://mcp.getrunpod.io/"</span> <span class="nb">}</span></span>
<span class="l">  <span class="nb">}</span></span>
<span class="l"><span class="nb">}</span></span></pre>

</div>

<!--
Skip unless the room is on Cursor.
-->

---

# Using Cursor: sign in, then paste

<div class="body sm">

<p class="cap">Save, restart Cursor, open Customize, MCP, and sign in to each server that says Needs login. Check both toggles are on.</p>

<p class="cap">Fill in your team name and key, then paste this.</p>

<pre class="code tight"><span class="l"><span class="nb">TEAM_NAME=yourteam</span></span>
<span class="l"><span class="nb">RUNPOD_API_KEY=rpa_paste-your-key-here</span></span>
<span class="l"></span>
<span class="l"><span class="nb">Fetch</span> <span class="nb">https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md</span> <span class="nb">and</span> <span class="nb">follow</span> <span class="nb">it</span> <span class="nb">step</span> <span class="nb">by</span> <span class="nb">step.</span> <span class="nb">Stop</span> <span class="nb">and</span> <span class="nb">tell</span> <span class="nb">me</span> <span class="nb">if</span> <span class="nb">it</span> <span class="nb">does</span> <span class="nb">not</span> <span class="nb">load.</span></span></pre>

<p class="cap">Your team name is 3 to 32 characters, lowercase letters, digits and hyphens, starting and ending with a letter or digit.</p>

</div>

<!--
Skip unless the room is on Cursor.
-->

---

# Using Codex

<div class="body sm">

<p class="cap">Open a terminal in a new empty folder named <code>hackathon</code>. Codex on the web cannot connect MCP servers.</p>

<pre class="code tight"><span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">galaxygate</span> <span class="nb">--url</span> <span class="nb">https://mcp.galaxygate.net/mcp</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">login</span> <span class="nb">galaxygate</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">add</span> <span class="nb">runpod</span> <span class="nb">--url</span> <span class="nb">https://mcp.getrunpod.io/</span></span>
<span class="l"><span class="nb">codex</span> <span class="nb">mcp</span> <span class="nb">login</span> <span class="nb">runpod</span></span></pre>

<p class="cap">Codex blocks network access until you allow it. Put these lines in <code>~/.codex/config.toml</code>, creating it if missing, then start <code>codex</code>.</p>

<pre class="code"><span class="l"><span class="nb">sandbox_mode</span> <span class="nb">=</span> <span class="nb">"workspace-write"</span></span>
<span class="l"></span>
<span class="l"><span class="nb">[sandbox_workspace_write]</span></span>
<span class="l"><span class="nb">network_access</span> <span class="nb">=</span> <span class="nb">true</span></span></pre>

</div>

<!--
Skip unless the room is on Codex.
-->

---

# Using Codex: paste this

<div class="body sm">

<p class="cap">Fill in your team name and key, then paste this.</p>

<pre class="code tight"><span class="l"><span class="nb">TEAM_NAME=yourteam</span></span>
<span class="l"><span class="nb">RUNPOD_API_KEY=rpa_paste-your-key-here</span></span>
<span class="l"></span>
<span class="l"><span class="nb">Fetch</span> <span class="nb">https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md</span> <span class="nb">and</span> <span class="nb">follow</span> <span class="nb">it</span> <span class="nb">step</span> <span class="nb">by</span> <span class="nb">step.</span> <span class="nb">Stop</span> <span class="nb">and</span> <span class="nb">tell</span> <span class="nb">me</span> <span class="nb">if</span> <span class="nb">it</span> <span class="nb">does</span> <span class="nb">not</span> <span class="nb">load.</span></span></pre>

<p class="cap">Your team name is 3 to 32 characters, lowercase letters, digits and hyphens, starting and ending with a letter or digit.</p>

</div>

<!--
Skip unless the room is on Codex.
-->

---

# The demos: Text to Speech

<div class="body sm">

<div class="withshot">
<div class="col">

<p class="cap">Both run on GalaxyGate servers with GPU work on RunPod, and setup puts Text to Speech on yours.</p>

<p class="cap"><strong>Text to Speech</strong>, https://runpoddemo1.galaxygate.app. Paste up to 2000 words, pick a voice from 20, hear it aloud. Code: <code class="link">https://github.com/<wbr>Gadgetguycj/<wbr>philly-hackathon/<wbr>tree/<wbr>main/<wbr>demos/<wbr>tts</code></p>

</div>
<img src="/tts-top.png" class="phone" />
</div>

<pre class="code tight"><span class="l"><span class="nb">Clone</span> <span class="nb">https://github.com/Gadgetguycj/philly-hackathon</span> <span class="nb">here,</span> <span class="nb">push</span> <span class="nb">it</span> <span class="nb">to</span> <span class="nb">a</span> <span class="nb">public</span> <span class="nb">repository</span> <span class="nb">of</span> <span class="nb">mine,</span> <span class="nb">then</span> <span class="nb">follow</span> <span class="nb">the</span> <span class="nb">redeploy</span> <span class="nb">section</span> <span class="nb">of</span> <span class="nb">https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md</span> <span class="nb">for</span> <span class="nb">my</span> <span class="nb">repository</span> <span class="nb">and</span> <span class="nb">demos/tts.</span></span></pre>

</div>

---

# The demos: Bookbuilder

<div class="body sm">

<p class="cap"><strong>Bookbuilder</strong>, https://runpoddemo2.galaxygate.app. Name a subject and watch a fast mixture of experts model write a 30 page book. Code: <code class="link">https://github.com/<wbr>Gadgetguycj/<wbr>philly-hackathon/<wbr>tree/<wbr>main/<wbr>demos/<wbr>bookbuilder</code></p>

<div class="bandwrap"><img src="/bookbuilder-run.png" class="band" /></div>

<pre class="code tight"><span class="l"><span class="nb">Clone</span> <span class="nb">https://github.com/Gadgetguycj/philly-hackathon</span> <span class="nb">here,</span> <span class="nb">push</span> <span class="nb">it</span> <span class="nb">to</span> <span class="nb">a</span> <span class="nb">public</span> <span class="nb">repository</span> <span class="nb">of</span> <span class="nb">mine,</span> <span class="nb">then</span> <span class="nb">follow</span> <span class="nb">the</span> <span class="nb">redeploy</span> <span class="nb">section</span> <span class="nb">of</span> <span class="nb">https://raw.githubusercontent.com/Gadgetguycj/philly-hackathon/main/AGENT.md</span> <span class="nb">for</span> <span class="nb">my</span> <span class="nb">repository</span> <span class="nb">and</span> <span class="nb">demos/bookbuilder.</span></span></pre>

</div>

---

# Build

<div class="body">

- Your app and your key live on your server.
- Only your server calls RunPod.
- Change a demo or start your own app, push it, and redeploy with the prompt above.

<p class="cap">Optional, and worth extra credit:</p>

<pre class="code"><span class="l"><span class="nb">Using</span> <span class="nb">the</span> <span class="nb">RunPod</span> <span class="nb">MCP,</span> <span class="nb">create</span> <span class="nb">a</span> <span class="nb">serverless</span> <span class="nb">endpoint</span> <span class="nb">for</span> <span class="nb">the</span> <span class="nb">model</span> <span class="nb">I</span> <span class="nb">name,</span> <span class="nb">then</span> <span class="nb">add</span> <span class="nb">a</span> <span class="nb">route</span> <span class="nb">to</span> <span class="nb">my</span> <span class="nb">app</span> <span class="nb">that</span> <span class="nb">calls</span> <span class="nb">it.</span></span></pre>

</div>

---

# Submit, and what is required

<div class="body">

- Submit at https://coffee-and-code-agent.devpost.com/ and select the GalaxyGate prize.
- Give judges your app URL, one input to try, and the ids from `HACKATHON.md`.
- Include no keys or environment screens.

<p class="cap">Required to be judged, and neither earns points:</p>

- Your app runs on a GalaxyGate server a judge can open.
- Your app does its GPU work on RunPod and you can show the request.

</div>

<!--
Reference only. Do not present.
-->

---

# Scoring, out of 100

<div class="body sm">

<p class="cap">Judges score live with their own inputs, out of 100.</p>

- **It works, 20.** The judge’s first input produces the promised result (10). A second, different input works (5). Nothing crashes, blanks, or spins forever (5).
- **Simple to use, 20.** A first-timer finishes the core task with no instructions (10). The screen says what is happening (5). The README gets a stranger running (5).
- **Reliable, 15.** Results survive a reload and a second run (5). Upstream errors reach the user instead of a hang (5). Two people using it at once do not break it (5).
- **Secure, 10.** Secrets live only in the server’s environment (5). Only your server calls RunPod, never the browser (5).
- **Scalable, 10.** GPU work runs on an endpoint that scales to zero and adds workers (5). App state lives outside the container (5).

</div>

<!--
Reference only. Do not present.
-->

---

# Scoring, and extra credit

<div class="body sm">

- **Agentic, 10.** The app decides its next step from model output or tools instead of one fixed call, and the judge can see it (10).
- **Creativity, 15.** An idea the judge has not seen before (5). A use of the GPU that is not just a chat box (5). A moment in the demo that makes the judge react (5).

<p class="cap">Extra credit, up to 15, each for a visible reason:</p>

- **More of GalaxyGate, 5 each, up to 10.** A second server doing real work, private networking, a floating IP, a backup or snapshot, or a load balancer.
- **More of RunPod, 5.** A second endpoint or model, a network volume, or a pod for training or a batch job.

<p class="cap">Ties break on Simple to use, then Reliable.</p>

</div>

<!--
Reference only. Do not present.
-->

---

# When something fails

<div class="body">

- **A tool call is denied or says Needs login.** Redo that sign-in in your tool.
- **A tool call says `denied by auto mode` and `Blocked by classifier`, and no approval prompt appears.** Press shift+tab until Claude Code shows manual mode, then tell your agent to continue.
- **The agent stopped.** Paste the same block in a new chat, with the same team name and key.
- **A generation returns 401.** Make a new RunPod key and have your agent update the app’s environment.
- **RunPod returns 402.** Your credit is gone, so check the console.
- **Anything else.** Ask your agent for the app logs, then bring the error text and `HACKATHON.md` to the table.

</div>

<!--
Reference only. Do not present.
-->

---

# After the event

<div class="body">

- Delete your server in the GalaxyGate panel.
- Revoke the `hackathon-app` key in the RunPod console.

</div>

<!--
Reference only. Do not present.
-->
