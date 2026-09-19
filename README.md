# GalaxyGate + RunPod track

Coffee & Code Philadelphia AI Agent Hackathon.

- **Start here: [GUIDE.md](GUIDE.md)**, the step by step setup and build guide.
- [AGENT.md](AGENT.md) is what your coding agent reads to create your server. The guide tells you when to use it.
- `demos/` holds the two demo apps: [Text to Speech](demos/tts) reads up to 2000 words aloud in one of 20 voices with an open model on RunPod, [Bookbuilder](demos/bookbuilder) writes a 100 page book page by page on a fast mixture of experts model. The organizers host them at https://runpoddemo1.galaxygate.app and https://runpoddemo2.galaxygate.app.
- `scripts/` holds the server side scripts that `AGENT.md` runs through panel recipes: `prepare.sh`, `build.sh`, `check.sh` and `verify-image.sh`.
- `qr/` holds the QR codes that open this guide.
- `ci/publish.yml` builds and pushes both demo images to GHCR. It lives outside `.github/workflows` until it is pushed by a token with the workflow scope.
- `slides/` holds the intro deck as a Slidev source (`slides.md`), its exported `deck.pdf`, and the assets it uses. https://gadgetguycj.github.io/philly-hackathon/ serves that deck, not the guide; the guide is `GUIDE.md` in this repository.
- `site/` renders `GUIDE.md` into the one page website at https://runpodtrack.galaxygate.app. Build it with `docker build -f site/Dockerfile -t runpodtrack-site .` and check it with `python3 site/test.py`.
