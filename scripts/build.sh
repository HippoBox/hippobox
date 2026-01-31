#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tag="${1:-local}"

if command -v hatch >/dev/null 2>&1; then
  ( cd "$root/src/backend" && hatch build )
elif command -v python >/dev/null 2>&1; then
  ( cd "$root/src/backend" && python -m hatch build )
else
  echo "Python is not installed or not found in PATH." >&2
  exit 1
fi

docker build -f "$root/docker/Dockerfile" -t "hippobox:${tag}" "$root"
