#!/bin/sh
# Wait for a container to be running one exact image, so a redeploy is proved on the server.
# usage: verify-image.sh <container> <image>
CONTAINER="$1"
IMAGE="$2"
if [ -z "$CONTAINER" ] || [ -z "$IMAGE" ]; then
  echo "usage: verify-image.sh <container> <image>" >&2
  exit 2
fi
i=0
while [ "$i" -lt 35 ]; do
  if [ "$(docker inspect -f '{{.Config.Image}}' "$CONTAINER" 2>/dev/null)" = "$IMAGE" ]; then
    echo "$CONTAINER runs $IMAGE"
    exit 0
  fi
  i=$((i + 1))
  sleep 1
done
echo "$CONTAINER does not run $IMAGE" >&2
exit 1
