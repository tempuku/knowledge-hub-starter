---
type: guide
title: Knowledge Hub CI validation and troubleshooting
status: draft
tags: [ci, validation, knowledge-hub]
---

# CI validation and troubleshooting

The `Validate OKF and diary` workflow must run on pull requests, pushes to `main`, and manual dispatch. Keep the `validate-openwiki` job enabled. Its checks cover staged OKF pages and links, diary exports, JavaScript syntax, iOS 12 source compatibility, Chromium and WebKit interactions, and the public export allowlist. Browser checks use a local server and do not publish records.

## Repair of the paused pipeline

The workflow had a temporary unconditional `if: false` on its only job. GitHub reported those runs as skipped, so they provided no validation. The [last failed validation run before the pause](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42869097404) expected the old `records` counter text while the app displayed `changes`. Later changes updated the counter tests to the current `entries` label, but two additional regressions remained on the current main branch:

- The history interaction test still rejected all GitHub links and expected a clickable title. The current app provides a canonical **File:** source link and explicit **Open** / **Show diff** buttons. The test now checks that link and exercises the explicit controls.
- `index.html` loaded version 9 of the JavaScript and stylesheet, while the service worker precached version 8. Updating the cache name and shell URLs to version 9 restores precaching of the files actually loaded. Keep these versions synchronized when changing the app shell.

The repair removes the unconditional validation skip. Build, publication, and browser assertions remain required; a skipped run is not a passing result. Chromium and WebKit both remain in the workflow. Source and browser checks do not establish physical iPad acceptance.

The staged checker also exposed a newer schema mismatch: [the guide](GUIDE.md) and current demo record use `status: completed`, but the pinned upstream OKF validator accepts only `draft`, `stable`, and `deprecated`. A local adapter explicitly accepts `completed` as a Knowledge Hub extension while retaining all other upstream checks and rejecting unknown statuses. The downloaded upstream validator remains unchanged and hash-verified. Regression tests cover accepted statuses, invalid YAML and other invalid metadata, and run in CI before the staged checker. This is a local compatibility extension, not a claim that upstream OKF defines `completed`.

## CI completion handoff

The separate `Return to PR when CI completes` workflow handles completed validation runs. It needs `pull-requests: write` to create or update its PR conversation comment; `issues: write` with `pull-requests: read` returned `403 Resource not accessible by integration` in [this handoff run](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42975069303).

Keep its existing same-repository, current-head and open-PR checks. This privileged workflow must never check out or run PR code. Its comment records a CI result; a reviewer still evaluates the current changes and checks before merging.

## Verification

Run the commands in the [repository README](../README.md), including the staged OKF checker before every commit. Build `dist/` before browser tests, and separately build and audit `dist-public/` with `--public-only`. Inspect the real GitHub Actions result for the exact commit after pushing; local macOS checks alone do not establish that the Ubuntu runner passes.
