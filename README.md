# GalaxyGate + RunPod track

Coffee & Code Philadelphia AI Agent Hackathon.

- **Start here: [GUIDE.md](GUIDE.md)**, the step by step setup and build guide.
- [AGENT.md](AGENT.md) is what your coding agent reads to create your server. The guide tells you when to use it.
- `demos/` holds the two demo apps: [Sketch to Site](demos/sketch) turns a phone photo of a website sketch into a hosted web page with a vision model on RunPod, [The Sticker Wall](demos/stickerwall) draws team stickers with Flux onto a shared wall.
- `qr/` holds the QR codes that open this guide.
- `ci/publish.yml` builds and pushes both demo images to GHCR. It lives outside `.github/workflows` until it is pushed by a token with the workflow scope.
- `slides/` holds the intro deck as a Slidev source (`slides.md`), its exported `deck.pdf`, and the assets it uses. https://galaxygate.github.io/philly-hackathon/ serves that deck, not the guide; the guide is `GUIDE.md` in this repository.
- `site/` renders `GUIDE.md` into the one page website at https://runpodtrack.galaxygate.app. Build it with `docker build -f site/Dockerfile -t runpodtrack-site .` and check it with `python3 site/test.py`.
