#!/bin/sh
set -eu

APP_DIR=${APP_DIR:-/opt/azurpilot-gg}
BRANCH=${BRANCH:-alasgg-features}
IMAGE=${IMAGE:-alas:py314}
CONTAINER=${CONTAINER:-alas}
TAILSCALE_IP=${TAILSCALE_IP:-100.88.23.89}
OLD_SHA=$(git -C "$APP_DIR" rev-parse HEAD)
BACKUP_DIR="$APP_DIR/.deploy-backup"

mkdir -p "$BACKUP_DIR"
cp -f "$APP_DIR/config/deploy.yaml" "$BACKUP_DIR/deploy.yaml" 2>/dev/null || true
cp -f "$APP_DIR/config/alas.json" "$BACKUP_DIR/alas.json" 2>/dev/null || true

git -C "$APP_DIR" fetch origin "$BRANCH"
NEW_SHA=$(git -C "$APP_DIR" rev-parse "origin/$BRANCH")
[ "$OLD_SHA" = "$NEW_SHA" ] && { echo "already up to date: $OLD_SHA"; exit 0; }

git -C "$APP_DIR" reset --hard "$NEW_SHA"
cp -f "$BACKUP_DIR/deploy.yaml" "$APP_DIR/config/deploy.yaml" 2>/dev/null || true
cp -f "$BACKUP_DIR/alas.json" "$APP_DIR/config/alas.json" 2>/dev/null || true

if ! docker build --pull -t "$IMAGE.new" -f "$APP_DIR/deploy/docker/Dockerfile" "$APP_DIR"; then
  git -C "$APP_DIR" reset --hard "$OLD_SHA"
  exit 1
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker volume rm alas-venv >/dev/null 2>&1 || true
docker volume create alas-venv >/dev/null
docker run -d --name "$CONTAINER" --restart unless-stopped --init --network host \
  -e TZ=Asia/Shanghai -e PYTHONUNBUFFERED=1 -e PYTHONDONTWRITEBYTECODE=1 \
  -e ALASGG_ADB=/usr/bin/adb \
  -e ALASGG_FRIDA_PYTHON=/app/AzurPilot/.venv/bin/python \
  -v "$APP_DIR:/app/AzurPilot" -v alas-venv:/app/AzurPilot/.venv \
  "$IMAGE.new" .venv/bin/python gui.py >/dev/null

sleep 15
if ! docker exec "$CONTAINER" .venv/bin/python -c "import socket; s=socket.create_connection(('$TAILSCALE_IP',25548),5); s.close()"; then
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  git -C "$APP_DIR" reset --hard "$OLD_SHA"
  docker run -d --name "$CONTAINER" --restart unless-stopped --init --network host \
    -e TZ=Asia/Shanghai -e PYTHONUNBUFFERED=1 -e PYTHONDONTWRITEBYTECODE=1 \
    -e ALASGG_ADB=/usr/bin/adb \
    -e ALASGG_FRIDA_PYTHON=/app/AzurPilot/.venv/bin/python \
    -v "$APP_DIR:/app/AzurPilot" -v alas-venv:/app/AzurPilot/.venv \
    "$IMAGE" .venv/bin/python gui.py >/dev/null
  exit 1
fi

docker tag "$IMAGE.new" "$IMAGE"
echo "updated: $OLD_SHA -> $NEW_SHA"
