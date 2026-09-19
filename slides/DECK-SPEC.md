# Deck spec: the GalaxyGate + RunPod track

Source of truth: `/opt/claude/projects/philly-hackathon/GUIDE.md` at commit **da666f6**.

Rules. A slide exists only if a participant needs it to finish. Prose is compressed to the
instruction. Every fenced block in the guide appears on a slide character for character and is
checked by `check-verbatim.py`. No dates, weekdays, times, prices, or durations the guide does
not state. Bullets and steps follow the guide's order. One idea per slide. No em dashes.
Titles are eight words or fewer.

The deck says nothing the guide does not say. Three sentences move position. The guide's
team name rule and its two expectation sentences sit at the end of the Accounts section; on
the deck they lead, on slide 2, because a participant needs them before the first paste. The
team name rule is repeated on the two standalone paste slides, where it is typed.

Type. Two body sizes, 22 px and 18 px CSS, which are 44 px and 36 px in the 1960 px render.
Nothing on a slide face is below 36 px in that render, measured in a browser across all
sixteen slides. Code blocks are 21 px CSS, except `.tight` at 18 px, used where a line would
otherwise wrap or overflow the block: the paste block on every tool slide, both clone prompts,
and the Claude Code and Codex command blocks.

Contrast. Every text colour clears 7 to 1 on its own background. Body `#e6e9f2` on `#0b1020`
is 15.6 to 1, code `#ddd6c8` on `#121a33` is 11.9 to 1, and the slide number `#9aa2bb` is
7.45 to 1.

Fonts are bundled in `public/fonts` and served by `@font-face`, so the deck does not depend on
venue Wi-Fi. Inline code uses the bundled mono with `!important` so the theme's Fira Code
cannot win. The favicon is local, so the built page makes no external request at all.

Speaker notes carry only two kinds of line: a tool-path skip cue, and "Reference only. Do not
present." Nothing else.

Assets in `public/`.

- `qr-guide.png`, generated with python qrcode at error correction M, box size 12, border 4.
  It encodes `https://runpodtrack.galaxygate.app` and decodes to that string from the PNG, from
  the rendered slide, and from page 1 of `deck.pdf`.
- `gg-coupon.png`, the coupon field on the GalaxyGate register page.
- `tts-top.png`, the top of `philly-hackathon/demos/tts/docs/04-after.png`, the Text to Speech
  app at phone width after a run.
- `bookbuilder-run.png`, the top band of
  `philly-hackathon/demos/bookbuilder/docs/browser-2-midrun.png`, Bookbuilder mid run at 1280
  wide. That capture came from a run against the stand-in endpoint the demo is tested with, so
  the crop stops above the page text that says so, and keeps the header, the page counter and
  the words per second.
- `favicon.png`.

## Running order, 16 slides

P = present. S = skip unless the room is on that tool. R = reference only, left up after the
talk.

| # | P/S/R | Slide |
|---|---|---|
| 1 | P | Cover. Title, "Scan for the guide", `runpodtrack.galaxygate.app`, the event name, and the QR to the guide site. |
| 2 | P | Before you start. What you need, who sets up, the team name rule, the two expectation sentences, and where help is. |
| 3 | P | Accounts. The three numbered steps with the coupon code, plus the coupon field crop. |
| 4 | S | Using Claude Code. The folder, the two `claude mcp add` commands, `/mcp`, and the paste block. |
| 5 | S | Using Cursor. Install, creating `.cursor/mcp.json` from inside Cursor, and the JSON. |
| 6 | S | Using Cursor: sign in, then paste. Restart and sign in, the paste block, the team name rule. |
| 7 | S | Using Codex. Terminal only, the four `codex mcp` commands, and the `config.toml` network block. |
| 8 | S | Using Codex: paste this. The paste block and the team name rule. |
| 9 | P | The demos: Text to Speech. What both demos are, the URL, what this one does, the phone screenshot, and its clone prompt. |
| 10 | P | The demos: Bookbuilder. The URL, what it does, the mid run screenshot, and its clone prompt. |
| 11 | P | Build. Where the app and the key live, redeploying, and the optional endpoint prompt. |
| 12 | R | Submit, and what is required. Where to submit, what judges get, and the two entry requirements that earn no points. |
| 13 | R | Scoring, out of 100. Judges score live. It works 20, Simple to use 20, Reliable 15, Secure 10, Scalable 10. |
| 14 | R | Scoring, and extra credit. Agentic 10, Creativity 15, both extra credit lines, and the tie break. |
| 15 | R | When something fails. The five failures in the guide's order. |
| 16 | R | After the event. Delete the server, revoke the key. |

Slide 16 is a deliberate closing slide and is left short. Every other slide is at least half
full.

Sixteen slides is one over the twelve to fifteen aim. The guide's three tool sections are self
contained and two of them need a second slide for the paste block, which is what pushes the
count past fifteen.

## Checks

- `python3 check-verbatim.py` extracts every `<pre class="code">` block from `slidev/slides.md`,
  turns it back into plain text, and requires each one to equal a fenced block in `GUIDE.md`.
  It also fails on a curly apostrophe, a curly quote, an en or em dash, or a non-breaking space
  inside a code block, and on an em dash or non-breaking space anywhere in `slides.md`.
- `npx slidev export slides.md --format png --scale 2 --output render` writes one 1960 by 1104
  PNG per slide.
- `npx slidev export slides.md --output deck.pdf` writes the PDF. `pdffonts deck.pdf` must show
  only subset Inter and JetBrains Mono, all embedded.
- `npx slidev build slides.md --base /philly-hackathon/ --out dist` builds the static site.
  Loading every slide of that build in a browser must record zero requests off the local host.
