#!/bin/sh
# Container entrypoint: prepare the bind-mounted checkout, then dispatch to the
# task runner. Commands are documented in tools/docker/run-tests.sh.
set -eu

workspace="${KH_WORKSPACE:-/workspace}"

if [ "${1:-}" = "shell" ]; then
  shift
  exec /bin/bash "$@"
fi

if [ ! -d "$workspace/.git" ]; then
  echo "No Git checkout mounted at $workspace." >&2
  echo "Run this image through compose.yaml or mount the repository at $workspace." >&2
  exit 1
fi

cd "$workspace"

# The image ships the pinned OKF validator (npm ci + verified frontmatter.ts).
# Copy it into the bind mount when the host checkout does not have it yet, so
# the same checker runs inside and outside Docker. Set KH_OKF_REFRESH=1 to
# force a refresh after tools/okf/package-lock.json changes.
if [ -d /opt/okf ]; then
  if [ ! -d tools/okf/node_modules/yaml ] || [ "${KH_OKF_REFRESH:-0}" = "1" ]; then
    echo "Preparing pinned OKF validator in $workspace/tools/okf"
    rm -rf tools/okf/node_modules
    mkdir -p tools/okf/node_modules
    cp -R /opt/okf/node_modules/. tools/okf/node_modules/
  fi
  if [ ! -f tools/okf/frontmatter.ts ]; then
    cp /opt/okf/frontmatter.ts tools/okf/frontmatter.ts
  fi
fi

exec /usr/local/bin/run-tests.sh "$@"
