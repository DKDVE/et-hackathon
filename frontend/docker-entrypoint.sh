#!/bin/sh
set -e
# Fresh-laptop path: install deps inside the container (NFR-6). Skip when the
# bind-mounted node_modules volume already has a matching lockfile install.
if [ ! -f node_modules/.package-lock.json ] || ! cmp -s package-lock.json node_modules/.package-lock.json 2>/dev/null; then
  echo "Installing frontend dependencies (npm ci)…"
  npm ci
  cp package-lock.json node_modules/.package-lock.json
fi
exec npm run dev -- --host 0.0.0.0
