#!/bin/sh
# Host wrapper around docker compose run. Picks the ui image automatically for
# browser tasks so callers do not need to remember the service name.
#
#   tools/docker/run.sh            # required-CI parity
#   tools/docker/run.sh node       # Node/OKF/JS checks only
#   tools/docker/run.sh ui         # Chromium + WebKit acceptance
#   tools/docker/run.sh shell      # interactive bash in the test image
set -eu

cd "$(dirname "$0")/../.."

task="${1:-ci}"
case "$task" in
  ui | all) service=ui ;;
  *) service=tests ;;
esac

exec docker compose run --rm "$service" "$@"
