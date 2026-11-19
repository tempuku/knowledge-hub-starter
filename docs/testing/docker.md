# Docker test environment

Pinned, disposable test runs that mirror required CI without installing Python,
Node or browser dependencies on the host. The image uses the same runtimes as
`.github/workflows/validate-openwiki.yml`: **Python 3.12** and **Node 22.18.0**.
Python packages are installed with `uv` from the committed `uv.lock`.

Docker is a local developer convenience only. The required `validate-openwiki`
check still runs natively on GitHub Actions and remains the merge authority.

## Prerequisites

- Docker Engine/Desktop, OrbStack or Colima with Compose v2 (`docker compose`).
- A full Git clone with `origin/main` and full history. Tests use
  `git merge-base HEAD origin/main` and historical fixture commits; shallow
  clones fail closed.
- No uncommitted requirement changes are needed: the image installs
  `pyproject.toml` + `uv.lock`, and builds the pinned OKF validator from
  `tools/okf/package-lock.json`.

## Quick start

```sh
docker compose build tests
tools/docker/run.sh
```

`tools/docker/run.sh` is a thin wrapper around
`docker compose run --rm tests`. The default task is `ci`.

| Task | Runs | Image |
| --- | --- | --- |
| `ci` (default) | Required-CI parity: Node/OKF/JS checks, Python unit and integration suites, inventory checks, projection + source-bundle smoke, v1 validation against `origin/main`, diary build and public-only export. | `tests` |
| `node` | Node/OKF/JavaScript checks only. | `tests` |
| `python` | Python unit, integration, inventory and projection checks only. | `tests` |
| `diary` | Diary build and public-only publication checks. | `tests` |
| `projection` | Immutable projection + source-bundle smoke test and v1 validation. | `tests` |
| `ui` | `run_local_ui_checks.sh` with `KH_V1_UI=1`: iOS 12 static checks plus Chromium and WebKit browser suites. | `ui` |
| `all` | `ci` then `ui`. | `ui` |
| `shell` | Interactive `bash` in the test image. | `tests` |

Examples:

```sh
tools/docker/run.sh node
tools/docker/run.sh ui
docker compose run --rm tests help
```

The UI image is much larger because `playwright install --with-deps` adds
Chromium, WebKit and their system libraries. Build it only when needed:

```sh
docker compose build ui
tools/docker/run.sh ui
```

## Reports and artifacts

| Output | Location |
| --- | --- |
| Projection/privacy and inventory reports | `acceptance-reports/` |
| Browser screenshots and engine reports | `local-ui-artifacts/` |
| Built diaries | `dist/`, `dist-public/` |
| Synthetic v1 fixture | inside the container's temporary directory (removed by the script) |

All are generated and Git-ignored. Override report paths with
`KH_ACCEPTANCE_REPORT_DIR` or `KH_UI_ARTIFACTS`. Browser evidence is local-only
and is not device acceptance: modern WebKit cannot prove Safari 12 behaviour,
and physical iPad acceptance remains the manual checklist in
[`ipad-local.md`](acceptance/ipad-local.md).

## How the mount works

The repository is bind-mounted at `/workspace` so tests read the working tree,
its Git history and `origin/main` from the host. The entrypoint then:

1. copies the image's pinned `tools/okf/node_modules` and `frontmatter.ts` into
   the checkout when they are missing (both are Git-ignored);
2. runs the requested task as the container user (root by default).

Set `KH_OKF_REFRESH=1` if `tools/okf/package-lock.json` changed and the host
checkout already has stale `tools/okf/node_modules`.

On Linux hosts, files created through the bind mount can be owned by root. Use
`sudo chown -R "$(id -u):$(id -g)" dist dist-public acceptance-reports
local-ui-artifacts` afterwards, or run Compose with a matching `user:` override.

## Updating dependencies

```sh
uv lock                    # after editing pyproject.toml
docker compose build tests # rebuild the pinned Python layer
```

`tools/diary/requirements.txt` and `requirements-ui.txt` remain the source used
by required CI and the host instructions; keep them in sync with
`pyproject.toml` when versions change.

## Keeping runs fast

- Image layers are cached; only changed `pyproject.toml`, `uv.lock`,
  `tools/okf` or `tools/docker` files trigger rebuilds.
- `docker compose build tests` is enough for normal work; `ui` is separate.
- Reports and builds are written to the bind mount, so a fresh container does
  not rebuild them.

## Current UI status

The `ci` task passes in Docker. The optional `ui` task runs the full local
suite, but on the current `main` the generated-v1 browser tests report
failures that are independent of Docker: fixture counts changed (9 records /
62 events) while several assertions still hard-code the older 7 records /
61 changes, and some assertions expect UI text or cache behaviour that is not
implemented or is only valid on a returning visit. The legacy Chromium/WebKit
suite passes. These are acceptance-test gaps for owner review; do not copy
failed or partial runs into issue #69 as passing evidence.
