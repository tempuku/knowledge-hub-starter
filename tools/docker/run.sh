#!/bin/sh
# Host wrapper around docker compose run. CI parity is default;
# browser-shell starts an optional Playwright-equipped environment.
#
#   tools/docker/run.sh            # required-CI parity
#   tools/docker/run.sh node       # Node/OKF/JS checks only
#   tools/docker/run.sh browser-shell  # shell with Chromium/WebKit available
#   tools/docker/run.sh shell      # interactive bash in the test image
set -eu

cd "$(dirname "$0")/../.."

task="${1:-ci}"
case "$task" in
  browser-shell) service=ui ;;
  *) service=tests ;;
esac

exec docker compose run --rm "$service" "$@"
