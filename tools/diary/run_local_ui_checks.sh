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
