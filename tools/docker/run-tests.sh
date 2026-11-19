#!/bin/sh
# Task runner used by the Docker image. Mirrors the required "Validate OKF and
# diary" CI job, plus the optional local-only browser acceptance suite.
#
#   docker compose run --rm tests ci          # default: required-CI parity
#   docker compose run --rm ui ui             # Chromium + WebKit acceptance
#   tools/docker/run.sh node                  # host wrapper for the same tasks
#
# Tasks: ci | node | python | diary | projection | ui | all | help
set -eu

cd "${KH_WORKSPACE:-/workspace}"

task="${1:-ci}"
if [ "$#" -gt 0 ]; then
  shift
fi

# Reports are written relative to the repository, matching CI.
export KH_ACCEPTANCE_REPORT_DIR="${KH_ACCEPTANCE_REPORT_DIR:-$PWD/acceptance-reports}"
mkdir -p "$KH_ACCEPTANCE_REPORT_DIR"

step() { printf '\n=== %s ===\n' "$*"; }

run() {
  step "$*"
  "$@"
}

suite() {
  step "unittest discover -s $1 -p $2"
  python -m unittest discover -s "$1" -p "$2" -v
}

inventory_checks() {
  run python scripts/inventory_legacy.py \
    --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb --check
  run python scripts/validate_inventory.py \
    --manifest migration/records-v1.json \
    --report-json "$KH_ACCEPTANCE_REPORT_DIR/inventory-validation.json"
}

v1_validate() {
  step "validate v1 source records against origin/main"
  if ! base="$(git merge-base HEAD origin/main 2>/dev/null)"; then
    echo "origin/main is missing; a full clone with origin/main is required." >&2
    echo "Run: git fetch origin (do not use a shallow clone)." >&2
    exit 1
  fi
  run python tools/records/validate_v1.py --base "$base"
}

projection_smoke() {
  step "immutable projection and source-bundle smoke test"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/kh-projection.XXXXXX")"
  run python tools/projection/build.py \
    --destination "$tmp/native-private" --revision HEAD --mode private
  run python tools/projection/build.py \
    --destination "$tmp/native-public" --revision HEAD --mode public
  run python tools/projection/sourcebundle.py \
    --root "$PWD" --revision HEAD \
    --output "$tmp/native.bundle.json" --receipt-output "$tmp/native.receipt.json"
  pin="$(PIN_DIR="$tmp" python -c 'import hashlib, os, pathlib; print(hashlib.sha256((pathlib.Path(os.environ["PIN_DIR"]) / "native.receipt.json").read_bytes()).hexdigest())')"
  run python tools/projection/build.py \
    --destination "$tmp/native-bundle" \
    --bundle "$tmp/native.bundle.json" --receipt "$tmp/native.receipt.json" \
    --receipt-sha256 "$pin" --mode private
  step "diff -r native-private/g native-bundle/g"
  diff -r "$tmp/native-private/g" "$tmp/native-bundle/g"
  rm -rf "$tmp"
}

diary_build() {
  run python tools/diary/build.py
  run python tools/diary/test_build.py
}

js_syntax() {
  run node --check site/app.js
  run node --check site/sw.js
  run node --check site/v1.js
  run node --check site/v1_data.js
  run node --check site/v1_markdown.js
}

public_export() {
  run python tools/diary/build.py --output-dir dist-public --public-only
  run python tools/diary/test_build.py --output-dir dist-public --public-only
  run python tools/diary/publish_v1.py --output-dir dist-public
  run python tools/diary/test_publication.py dist-public
}

node_task() {
  run node --test tools/ci/merge-gate.test.cjs
  run node --test tools/ci/auto-ready.test.cjs
  run node --test tools/okf/knowledge-frontmatter.test.mjs
  run sh .githooks/pre-commit
  js_syntax
  run node --test site/sw.test.cjs site/v1_data.test.js
}

python_task() {
  run python scripts/check_integrated_acceptance.py
  suite tests test_integrated_acceptance.py
  suite tests test_issue37_integration.py
  suite tests test_p16_fixture.py
  inventory_checks
  suite tests test_validate_inventory.py
  suite tools/records 'test_*.py'
  suite tests test_cutover_maintenance.py
  suite tools/cutover 'test_*.py'
  suite tools/projection 'test_*.py'
  projection_smoke
  v1_validate
  suite tools/diary test_v1_reports.py
}

ui_task() {
  if ! python -c 'import playwright' >/dev/null 2>&1; then
    echo "Playwright is not installed in this image." >&2
    echo "Run the UI task on the ui image: tools/docker/run.sh ui" >&2
    exit 1
  fi
  step "local browser acceptance (Chromium + WebKit, synthetic v1 fixture)"
  KH_V1_UI=1 \
    KH_UI_ARTIFACTS="${KH_UI_ARTIFACTS:-$PWD/local-ui-artifacts}" \
    sh tools/diary/run_local_ui_checks.sh
}

ci_task() {
  node_task
  python_task
  diary_build
  public_export
}

help() {
  cat <<'EOF'
Usage: run-tests.sh [task]

Tasks:
  ci          Required-CI parity (default). Node, OKF, Python, projection,
              diary build and public-only export checks.
  node        Node/OKF/JavaScript checks only.
  python      Python unit, integration, inventory and projection checks only.
  diary       Build the diary and verify the public-only export.
  projection  Immutable projection + source-bundle smoke test.
  ui          Local browser acceptance (needs the ui image).
  all         ci + ui.
  help        Show this message.

Environment:
  KH_ACCEPTANCE_REPORT_DIR  Report output (default: <repo>/acceptance-reports).
  KH_UI_ARTIFACTS           Browser evidence (default: <repo>/local-ui-artifacts).
  KH_OKF_REFRESH=1          Refresh tools/okf dependencies from the image.
EOF
}

case "$task" in
  ci) ci_task ;;
  node) node_task ;;
  python) python_task ;;
  diary) diary_build; public_export ;;
  projection) projection_smoke; v1_validate ;;
  ui) ui_task ;;
  all) ci_task; ui_task ;;
  help | -h | --help) help ;;
  *)
    echo "Unknown task: $task" >&2
    help >&2
    exit 2
    ;;
esac

step "done: $task"
