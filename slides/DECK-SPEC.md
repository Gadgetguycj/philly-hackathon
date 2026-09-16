# Deck spec: the GalaxyGate + RunPod track

Source of truth: `/opt/claude/projects/philly-hackathon/GUIDE.md` and `AGENT.md` at commit **c2dffa3**.

Rules. A slide exists only if a participant needs it to finish. Prose is compressed to the
instruction; every fenced block is verbatim from GUIDE.md and is checked by script at build
time. No dates, weekdays, pricing, timings the guide does not state, or trivia. No em dashes.
Titles are eight words or fewer.

Type. Two body sizes, 22 px and 18 px CSS, which are 44 px and 36 px in the 1960 px render.
Nothing on a slide face is below 34 px. Code blocks are one size, 21 px CSS, except `.tight`
at 17 px, used only where the longest unbreakable token would overflow the block: the step 5
paste block, the clone prompt and the redeploy prompt. There is no `.tighter`.

Fonts are bundled in `public/fonts` and served by `@font-face`, so the deck does not depend on
venue Wi-Fi. Inline code uses the bundled mono with `!important` so the theme's Fira Code
cannot win.

Speaker notes carry only two kinds of line: a tool-path skip cue, and "Reference only. Do not
present." Nothing else.

Assets in `public/`: `qr-guide.png` (copied from `philly-hackathon/qr/guide-direct.png`, decodes
to the GUIDE.md page), `gg-coupon.png`, `sketch-upload-top.png`, all captured at device pixel ratio 2.

## Running order, 21 slides

P = present in the six-minute slot. S = skip unless the room is on that tool. R = reference
only, left up after the talk.

| # | P/S/R | Slide |
|---|---|---|
| 1 | P | Cover. Title, "Scan for the guide", the repository URL, and the QR to GUIDE.md. |
| 2 | P | Before you start. Laptop, GitHub, email, the team note, the three tools with their desktop and web paths, and the `hackathon` folder. |
| 3 | P | Step 2. GalaxyGate account. Register with the coupon, verify, sign in, plus a crop of the coupon field. |
| 4 | P | Step 3. RunPod account and one API key. Sign up, redeem and check the balance, create `hackathon-app`, and where the key lives. |
| 5 | S | Cursor: MCP servers. The two addresses, creating `.cursor/mcp.json` from inside Cursor, and the JSON. |
| 6 | S | Cursor: sign in. Restart, Customize, MCP, approve each server, approve the agent's commands as they appear, stay at the laptop, and the Cursor web path. |
| 7 | S | Claude Code: MCP servers. The two `claude mcp add` commands, `/mcp`, and the web connector path. |
| 8 | S | Codex: MCP servers. Terminal only. The four `codex mcp` commands and the `config.toml` network-access block. |
| 9 | P | Step 4. Check the connection. The check prompt and the two results to expect. |
| 10 | P | Step 5. Create your server: paste this. The team-name rule first, then the paste block, then the manual fallback. |
| 11 | P | Step 5. What the agent does. Server, Docker build, GPU endpoint, demo, the two waits, and the done condition. |
| 12 | P | The one rule, and spending. Where the key lives, no browser calls, the 100-second proxy, the shared generation cap and `/api/usage`, and how the endpoint bills. |
| 13 | P | The demo: Sketch to Site. What it does, with a phone screenshot of the upload screen. |
| 14 | P | Change the demo and redeploy. Fork, the clone prompt, the web-session variant, the redeploy prompt, logs and restart. |
| 15 | R | Use a GPU model. `hackathon-vl`, the chat-completions URL, and the Flux Schnell prompt with its request shape. |
| 16 | P | Required to be judged in this track. The two integrations, reuse disclosure, fabricated evidence, and that the gates earn no points. |
| 17 | R | Submit on Devpost. Where to submit, which prize, and what judges need. |
| 18 | P | Scoring, 100 points plus 15 extra. It works 30, Simple to use 20, Reliable 15, with every point split. |
| 19 | R | Scoring, continued, and ties. Secure 15, Scalable 10, Agentic 10, extra credit up to 15, the tie-break, and what a down app loses. |
| 20 | R | When something fails. Six failure rows and what to bring to the table. |
| 21 | P | After the event. Delete the server, delete the endpoint, revoke the key, check for running workers. |
