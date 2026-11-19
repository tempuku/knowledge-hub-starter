# Docker test environment

The Docker `tests` image provides a pinned, disposable toolchain matching required `validate-openwiki` CI: Python 3.12, Node 22.18.0 and Python packages installed via `uv.lock`. The optional larger `ui` image has Playwright Chromium and WebKit installed **for agent-driven browser inspection**, not for a hardcoded UI acceptance suite.

## Prerequisites and fast tests

Use Docker Compose v2 and a full repository checkout with `origin/main`. Required tests work without browser installation:

```sh
docker compose build tests
tools/docker/run.sh             # required-CI parity
tools/docker/run.sh node        # Node/OKF/JS checks
tools/docker/run.sh python      # integrity, projections, etc.
tools/docker/run.sh diary       # build + public publication check
```

Required CI remains the merge authority. `knowledge-merge-gate` is a separate advisory (non-blocking) status and is unchanged.

## Browser-capable shell (optional)

```sh
docker compose build ui
tools/docker/run.sh browser-shell
```

The shell includes Playwright browser binaries but **does not automatically run UI tests, take screenshots, or provide an AI agent**. A browser-capable agent can use it as an environment, provided the agent can access the application it needs to inspect. To prepare a safe public-only local preview in the checkout, follow [the short browser review instructions](../acceptance/ipad-local.md). Serve only `dist-public`, never private records.

The old scripted legacy/v1 Chromium/WebKit browser suites, synthetic v1 fixture generator, engine report validator and `ui`/`all` test tasks were removed to reduce brittle acceptance-test maintenance. Preserve the meaningful distinction between **observed** UI behavior and unverified acceptance.

## Reports and artifacts

Required CI-parity tasks write privacy-safe projection/inventory reports into `acceptance-reports/`, and builds into `dist/` and `dist-public/` (all git-ignored). Agent browser screenshots are optional and should only be attached to issues when they contain no private content. Keep the tested URL, commit/generation and any observations beside the screenshot.

The repository is bind-mounted at `/workspace`; `tools/docker/entrypoint.sh` refreshes pinned OKF tooling when missing. Use `KH_OKF_REFRESH=1` when its dependencies need refreshing. The test image is built from `pyproject.toml` + `uv.lock`; the optional `ui` group installs browser tooling only. Rebuild images after dependency updates.

An original iPad Air running Safari 12 still needs a physical-device check; desktop WebKit is not equivalent.
