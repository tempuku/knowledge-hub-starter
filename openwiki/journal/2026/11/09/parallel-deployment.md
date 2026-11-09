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
    title: Phase A preview CI proposal
---

# Parallel GitHub Pages deployment

Phase A — GitHub Actions validation, portable packaging, public-artifact allowlist and synthetic-site CI — can be implemented independently. Phase B — integrating real reusable model assets and the shared viewer — follows the actual verified asset schema/viewer work. Public publishing needs explicit authorization: never deploy OpenSCAD source, private reference photographs, reports, tokens or manufacturing-only artifacts by default.

## Implementation check — 2026-11-09

[PR #7](https://github.com/tempuku/ivanovo_models/pull/7) contains Phase A's workflow, packager, privacy validator, synthetic fixture and tests. GitHub recorded **successful validation and OpenWiki checks** on its PR commit, but the public `publish` job was **skipped by design**. At the check, PR #7 was **open and not mergeable until conflicts are resolved**. Consequently the new CI code is not yet on `main`.

The [deployment issue #4](https://github.com/tempuku/ivanovo_models/issues/4) is still open. No separate authorized public preview repository or publicly working Ivanovo Pages site was verified. Do not confuse this with the distinct, already deployed Knowledge Hub diary site.

## How to verify

- Open [PR #7](https://github.com/tempuku/ivanovo_models/pull/7): inspect merge conflicts, Checks and changed files; verify whether it has since merged. Green fixture tests do not establish that an actual model viewer is published.
- Confirm [issue #4](https://github.com/tempuku/ivanovo_models/issues/4) remains open until both phases meet acceptance, including a real preview URL and browser inspection.
- Once Phase A merges, use `tools/deploy/package_site.py`, `tools/deploy/validate_dist.py` and `tests/test_deploy_preview.py` per the PR's instructions. These tools are **not** asserted to exist on the current `main`.
- For Phase B, confirm owner-approved publication, a strict vetted preview allowlist, a real Pages deployment, model navigation and colored-asset loading. A successful GitHub Actions artifact upload alone is insufficient.

The [project record](../../../../projects/ivanovo-models.md) contains the shared verification commands and links.
