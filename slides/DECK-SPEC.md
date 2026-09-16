# Deck spec: the GalaxyGate + RunPod track

Source of truth: `/opt/claude/projects/philly-hackathon/GUIDE.md` and `AGENT.md` at commit **76712b4**.

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
present." Nothing else. Inline code chips carry an absolute 19 px so no text on any face falls below
34 px in the render.

Assets in `public/`: `qr-guide.png` (copied from `philly-hackathon/qr/guide-direct.png`, decodes
to the GUIDE.md page), `gg-coupon.png`, `sketch-upload-top.png`, all captured at device pixel ratio 2.

## Running order, 24 slides

P = present in the six-minute slot. S = skip unless the room is on that tool. R = reference
only, left up after the talk.

| # | P/S/R | Slide |
|---|---|---|
| 1 | P | Cover. Title, "Scan for the guide, or open the repository", the repository URL, and the QR to GUIDE.md. |
| 2 | P | Before you start. Laptop, GitHub, email, the team note, and the three tools with their desktop and web paths, each with the folder or repository it opens in. |
| 3 | P | Step 2. GalaxyGate account. Register with the coupon, verify, sign in, plus a crop of the coupon field. |
| 4 | P | Step 3. RunPod account and one API key. Sign up, redeem and check the balance reads $15, create `hackathon-app`, where the key lives, and the second narrower key. |
| 5 | S | Step 4. Cursor: MCP servers. The two addresses, creating `.cursor/mcp.json` from inside Cursor, and the JSON. |
| 6 | S | Step 4. Cursor: sign in. Restart, Customize in the sidebar, MCP, approve each server, and the Cursor web path. |
| 7 | S | Step 4. Claude Code: MCP servers. The two `claude mcp add -t http` commands, starting Claude Code from the same folder, and the web connector path. |
| 8 | S | Step 4. Codex: MCP servers. Terminal only. The four `codex mcp` commands and the `config.toml` sandbox block. |
| 9 | P | Step 4. Check the connection. The check prompt and the two results to expect. |
| 10 | P | Step 5. Create your server: paste this. The team-name rule first, then the paste block, then the manual fallback. |
| 11 | P | Step 5. What the agent does. Server, Docker build, GPU endpoint, demo, the two waits, staying with the laptop for approvals, and the done condition. |
| 12 | P | The one rule, and spending. Where the key lives, no browser calls, the 100-second proxy, the shared cap and `/api/usage`, how the endpoint bills, the warm-up generation, and the balance check. |
| 13 | P | The demo: Sketch to Site. What it does, with a phone screenshot of the upload screen. |
| 14 | P | Fork and clone. The repository and `demos/sketch`, the clone prompt, and the web-session variant. |
| 15 | P | Redeploy your changes. The redeploy prompt, the `HACKATHON.md` fallback, logs and restart. |
| 16 | R | Use a GPU model: your endpoint. `hackathon-vl`, the chat-completions URL, and the fifteen-minute call. |
| 17 | R | Use a GPU model: ready-made. The Flux Schnell prompt, its request shape and size rules, and the docs URL. |
| 18 | P | Required to be judged in this track. The two integrations, reuse disclosure, fabricated evidence, and that having them earns nothing. |
| 19 | R | Submit on Devpost. Where to submit, which prize, and what judges need. |
| 20 | R | Scoring, 100 points plus up to 15 extra. It works 30, Simple to use 20, Reliable 15, with every split and the upstream-failure carve-out. |
| 21 | R | Scoring, continued, and ties. Secure 15, Scalable 10, Agentic 10, extra credit with its qualifiers, the tie-break and what a down app loses. |
| 22 | R | When something fails. Sign-in, a stopped agent or ended session, and a server that never became ready. |
| 23 | R | When something fails, continued. The first deploy, 401, 402, a failed generation, and what to bring to the table. |
| 24 | R | After the event. Delete the server, delete the endpoint, revoke the key, check for running workers. |

Slide 24 is a deliberate closing slide and is left short.
