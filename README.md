# GalaxyGate + RunPod track

Coffee & Code Philadelphia AI Agent Hackathon.

- **Start here: [GUIDE.md](GUIDE.md)**, the step by step setup and build guide.
- [AGENT.md](AGENT.md) is what your coding agent reads to create your server. The guide tells you when to use it.
- `demos/` holds the two demo apps: [Roast My Repo](demos/roast) streams a code roast and can propose a patch, [The Sticker Wall](demos/stickerwall) draws team stickers with Flux onto a shared wall.
- `qr/` holds the QR codes that open this guide.
- `ci/publish.yml` builds and pushes both demo images to GHCR. It lives outside `.github/workflows` until it is pushed by a token with the workflow scope.
- `slides/` holds the intro deck as a Slidev source (`slides.md`), its exported `deck.pdf`, and the assets it uses. The live version is at https://galaxygate.github.io/philly-hackathon/.
