#!/bin/sh
# Clone a repository on the server and build one app folder into the loopback registry.
# usage: build.sh <repo_url> <app_dir> <tag>
set -e
REPO_URL="$1"
APP_DIR="$2"
TAG="$3"
if [ -z "$REPO_URL" ] || [ -z "$APP_DIR" ] || [ -z "$TAG" ]; then
  echo "usage: build.sh <repo_url> <app_dir> <tag>" >&2
  exit 2
fi
IMAGE="127.0.0.1:5000/hackathon:$TAG"
docker start registry >/dev/null 2>&1 || docker run -d --restart always --name registry -p 127.0.0.1:5000:5000 registry:2
rm -rf /opt/build
git clone --depth 1 "$REPO_URL" /opt/build
test -f "/opt/build/$APP_DIR/Dockerfile"
docker build -t "$IMAGE" "/opt/build/$APP_DIR"
docker push "$IMAGE"
docker image rm "$IMAGE"
docker pull "$IMAGE"
echo "built $IMAGE"
