#!/bin/sh
# Application lifecycle only: the HTTPS overlay is deliberately not included.
set -eu
BLUEPRINT_ROOT=${BLUEPRINT_ROOT:-/home/ubuntu/B4FastAPI}
BLUEPRINT_PROJECT=${BLUEPRINT_PROJECT:-docker}
PROXY_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec docker compose \
  --project-name "$BLUEPRINT_PROJECT" \
  --project-directory "$BLUEPRINT_ROOT/docker" \
  --env-file "$BLUEPRINT_ROOT/docker/.env" \
  -f "$BLUEPRINT_ROOT/docker/docker-compose.yml" \
  -f "$PROXY_DIR/blueprint-app.override.yml" "$@"
