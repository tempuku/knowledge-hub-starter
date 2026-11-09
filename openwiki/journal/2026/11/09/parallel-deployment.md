---
type: diary-entry
title: Deployment foundation can be implemented independently
description: GitHub Actions CI and safe preview-site packaging can be built before the final 3D viewer is integrated.
occurred_on: "2026-11-09"
project: ivanovo-models
tags: [decision, deployment, ci-cd]
status: draft
visibility: public
sources:
  - resource: https://github.com/tempuku/ivanovo_models/issues/4
    title: Deployment issue
  - resource: https://github.com/tempuku/ivanovo_models/pull/7
    title: Merged Phase A public-demo CI
  - resource: https://github.com/tempuku/ivanovo_models/pull/20
    title: Merged private authenticated Worker transport
---

# Parallel GitHub Pages deployment

Phase A — GitHub Actions validation, portable packaging, public-artifact allowlist and synthetic-site CI — can be implemented independently. Phase B — integrating real reusable model assets and the shared viewer — follows the actual verified asset schema/viewer work. Public publishing needs explicit authorization: never deploy OpenSCAD source, private reference photographs, reports, tokens or manufacturing-only artifacts by default. **Later architecture decision:** production private viewing is an Access-protected Worker with server-side read-only GitHub retrieval; GitHub Pages is optional public-demo-only.

## Implementation check — updated 2026-11-09

- [PR #7](https://github.com/tempuku/ivanovo_models/pull/7) **merged** Phase A synthetic preview CI, strict public artifact allowlist and documentation. Validation passed; the actual public publishing job was intentionally skipped. No Ivanovo public Pages destination was created.
- [PR #20](https://github.com/tempuku/ivanovo_models/pull/20) **merged** read-only private Viewer Phase B1 code: Cloudflare Access identity/audience/email checks, server-only least-privilege GitHub credential, redacted catalogs and verified GLBs. The first four Actions runs never started any jobs and could not be retried; a new empty-tree commit triggered fresh jobs. Its [private auth test workflow](https://github.com/tempuku/ivanovo_models/actions/runs/42677163711) and the other three workflows **passed**. No Cloudflare service, Access policy, secret or production URL was provisioned.
- [Viewer PR #19](https://github.com/tempuku/ivanovo_models/pull/19) remains **draft/unmerged**. Its synthetic colored GLB browser smoke passed, but no real building-specific GLB has been accepted. [Issue #4](https://github.com/tempuku/ivanovo_models/issues/4) remains open for a real authenticated, device-tested private URL. Merely merging the Worker is not proof of access protection.

## How to verify

1. Check merged PRs [#7](https://github.com/tempuku/ivanovo_models/pull/7) and [#20](https://github.com/tempuku/ivanovo_models/pull/20), plus the current [#4 checklist](https://github.com/tempuku/ivanovo_models/issues/4).
2. Review successful GitHub runs for [private auth](https://github.com/tempuku/ivanovo_models/actions/runs/42677163711), [OpenWiki](https://github.com/tempuku/ivanovo_models/actions/runs/42677163625), [Preview CI](https://github.com/tempuku/ivanovo_models/actions/runs/42677163654) and [building tests](https://github.com/tempuku/ivanovo_models/actions/runs/42677164173).
3. From authorized `ivanovo_models` `main`, run `node --test tools/private_viewer/worker.test.mjs` and `python3 -m unittest discover -s tests -p 'test_deploy_preview.py' -v`. These are unit/fixture tests, not live authentication.
4. Only after the owner configures Cloudflare Access, all protected hostnames and a read-only GitHub secret, verify anonymous requests are denied and authorized clients can load the actual private site. Do not present a hypothetical URL as a working deployment.

The [project record](../../../../projects/ivanovo-models.md) contains the shared verification commands and links.
