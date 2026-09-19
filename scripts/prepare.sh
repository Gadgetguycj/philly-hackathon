#!/bin/sh
# Install Docker, git and socat, start the loopback registry, and make the /data folders.
set -e
export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
fi
if ! command -v git >/dev/null 2>&1 || ! command -v socat >/dev/null 2>&1; then
  apt-get -o DPkg::Lock::Timeout=300 update -q
  apt-get -o DPkg::Lock::Timeout=300 install -y -q git socat
fi
systemctl enable --now docker
install -d -o 1000 -g 1000 /data/tts /data/tts-2
docker start registry >/dev/null 2>&1 || docker run -d --restart always --name registry -p 127.0.0.1:5000:5000 registry:2
echo "prepare ok"
