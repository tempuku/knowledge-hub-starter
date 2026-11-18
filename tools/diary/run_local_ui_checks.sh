#!/bin/sh
# Local-only responsive browser and iOS 12 compatibility acceptance checks.
# One-time setup: install requirements-ui.txt and Playwright Chromium/WebKit.
set -eu

cd "$(dirname "$0")/../.."
PYTHON="${PYTHON:-python3}"

"$PYTHON" tools/diary/build.py
"$PYTHON" tools/diary/test_ios12.py
"$PYTHON" tools/diary/test_ui.py
DIARY_BROWSER=webkit "$PYTHON" tools/diary/test_ui.py

# The native-v1 suite uses synthetic committed records and a disposable source.
# Opt in to the larger fixture; keep all browser/device checks out of CI.
if [ "${KH_V1_UI:-0}" = 1 ]; then
  CHECK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/kh-local-v1.XXXXXX")"
  trap 'rm -rf "$CHECK_DIR"' EXIT HUP INT TERM
  "$PYTHON" tools/diary/generate_v1_ui_fixture.py \
    --source-dir "$CHECK_DIR/source" --dist-dir "$CHECK_DIR/dist"
  export V1_DIST="$CHECK_DIR/dist" V1_SOURCE_DIR="$CHECK_DIR/source"
  export V1_UI_ARTIFACTS="${KH_UI_ARTIFACTS:-$PWD/local-ui-artifacts}"
  mkdir -p "$V1_UI_ARTIFACTS"
  rm -f "$V1_UI_ARTIFACTS/chromium-report.json" "$V1_UI_ARTIFACTS/webkit-report.json" "$V1_UI_ARTIFACTS/local-v1-acceptance-summary.json"
  V1_STATUS=0
  V1_BROWSER=chromium "$PYTHON" tools/diary/test_v1_ui.py || V1_STATUS=1
  V1_BROWSER=webkit "$PYTHON" tools/diary/test_v1_ui.py || V1_STATUS=1
  "$PYTHON" tools/diary/validate_v1_reports.py --reports-dir "$V1_UI_ARTIFACTS" --head "$(git rev-parse HEAD)" || V1_STATUS=1
  if [ "$V1_STATUS" -ne 0 ]; then
    echo "Generated-v1 browser acceptance NOT VERIFIED. Inspect local engine logs and reports." >&2
    exit 1
  fi
fi
