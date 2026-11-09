---
type: diary-entry
title: Decide to reuse 3D model assets in one dynamic viewer
description: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.
occurred_on: "2026-11-09"
project: ivanovo-models
tags: [decision, dry, viewer]
status: draft
visibility: public
sources:
  - resource: https://github.com/tempuku/ivanovo_models/issues/3
    title: Unified viewer implementation issue
  - resource: https://github.com/tempuku/ivanovo_models/pull/15
    title: Viewer-state implementation
  - resource: https://github.com/tempuku/ivanovo_models/pull/19
    title: Draft unified viewer implementation
  - resource: https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md
    title: Viewer implementation and verification guide
---

# One viewer, many buildings

House-Ship establishes the visual language; Horseshoe contributes real-part hide/show and explode/assemble. The planned shared app loads independently colored master geometry and actual manufacturing-part assets dynamically from declarative manifests, rather than embedding duplicate mesh data in separate model-specific HTML apps. Legacy standalone viewers remain usable during migration.

## Implementation check — 2026-11-09

[Issue #3](https://github.com/tempuku/ivanovo_models/issues/3) is **closed**, and [PR #15](https://github.com/tempuku/ivanovo_models/pull/15) merged `viewer/state.mjs` with five Node state tests. This proves *presentation-state logic only*: verified-path gating, five print-variant states, and disassembly transforms limited to real manufacturing parts. It **does not** mean the root HTML viewer, browser renderer or live 3D inspection page exists on `main`. The [repository's viewer guide](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md) explicitly lists unfinished acceptance checks.

**Later same-day update:** [Draft PR #19](https://github.com/tempuku/ivanovo_models/pull/19) now implements the single catalog interface, independent colored-GLB renderer, SHA-256 verification and sanitized private dry-run packaging. Its [GitHub-hosted synthetic GLB/Chrome smoke](https://github.com/tempuku/ivanovo_models/actions/runs/42666004602) passed. It remains **unmerged**, and the real building-specific portable masters and actual building visual/browser acceptance are still missing. The new [PR #20](https://github.com/tempuku/ivanovo_models/pull/20), which adds read-only authenticated delivery, has merged separately; it does not imply the viewer itself is live.

## How to verify

```sh
# From an authorized local checkout of tempuku/ivanovo_models on main:
node --test viewer/tests/state.test.mjs
python3 -m tools.building.catalog --check
```

Confirm `viewer/state.mjs` and `viewer/catalog.json` exist, and inspect the catalog's explicit missing/legacy-only states. Do **not** interpret this as a successful 3D browser test. Viewer completion requires a working HTTP-served root page with real colored assets, four-building navigation, camera/model controls, actual multipart explosion, absent-asset handling, and browser smoke tests. See the [full verification checklist](../../../../projects/ivanovo-models.md).
