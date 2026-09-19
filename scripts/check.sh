#!/bin/sh
# Poll the marker files a detached script writes, so the panel sees one short recipe.
# usage: check.sh <name>   exit 0 done, exit 1 failed or still running
NAME="$1"
if [ -z "$NAME" ]; then
  echo "usage: check.sh <name>" >&2
  exit 2
fi
i=0
while [ "$i" -lt 35 ]; do
  if [ -f "/opt/hackathon-$NAME.done" ]; then echo "$NAME done"; exit 0; fi
  if [ -f "/opt/hackathon-$NAME.failed" ]; then echo "$NAME failed" >&2; exit 1; fi
  i=$((i + 1))
  sleep 1
done
echo "$NAME still running" >&2
exit 1
