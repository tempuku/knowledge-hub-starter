---
type: project
title: Ivanovo architectural 3D models
status: draft
project_id: ivanovo-models
tags: [architecture, openscad, 3d-printing, viewer]
visibility: private
sources:
  - resource: https://github.com/tempuku/ivanovo_models
    title: Source repository
  - resource: https://github.com/tempuku/ivanovo_models/pull/17
    title: Colored master implementation
  - resource: https://github.com/tempuku/ivanovo_models/pull/18
    title: Mesh and slicer evidence implementation
  - resource: https://github.com/tempuku/ivanovo_models/pull/15
    title: Viewer-state groundwork
  - resource: https://github.com/tempuku/ivanovo_models/pull/7
    title: Deployment Phase A proposal
---

# Ivanovo architectural 3D models

Canonical development source: [tempuku/ivanovo_models](https://github.com/tempuku/ivanovo_models) (private; requires GitHub repository access). This note is a **manual snapshot from 2026-11-09**, not an automatically synchronized status feed. For current state, consult the linked issues, merged PRs, CI and repository files.

## Architecture and production contract

- One detailed, material-colored architectural master independent of HTML; printable geometry should derive directly from the master where practical (master-first, without automatic detail loss).
- Five mandatory print configurations: Big (~200 mm) single-color, four-color, LED; Small (~100–120 mm) single-color and four-color. **No Small LED.** Optional separate-per-floor Big LED is experimental.
- Preserve real XYZ proportions; choose a 1:N architectural scale with denominator stepped by 10, and flag unverified reference dimensions as provisional.
- The current example printer profile is Bambu Lab P2S, but printer, nozzle, process and installed multicolor equipment must be configured/verified independently.
- A shared DRY root viewer should load reusable preview geometry/metadata; House-Ship is the look-and-feel reference, Horseshoe provides real multipart explode/assemble behavior.
- Generated assets, slicer evidence, test prints, assembly and physical signoff are **different acceptance stages**.

## Implementation snapshot — 2026-11-09

| Work | Evidence | What is actually verified |
| --- | --- | --- |
| [#1 Standards](https://github.com/tempuku/ivanovo_models/issues/1) | [PR #5 merged](https://github.com/tempuku/ivanovo_models/pull/5) | OpenWiki standards and ADR; not manufacturing evidence. |
| [#2 Template foundation](https://github.com/tempuku/ivanovo_models/issues/2) | [PR #8 merged](https://github.com/tempuku/ivanovo_models/pull/8) | Scaffold, configurable printer/process profiles, manifests; **foundation-only**. |
| [#9 Independent colored master](https://github.com/tempuku/ivanovo_models/issues/9) | [PR #17 merged](https://github.com/tempuku/ivanovo_models/pull/17) | Reproducible OpenSCAD-to-colored-GLB **starter fixture** and hash/material verification. This does not approve real buildings. |
| [#12 Mesh/slicer evidence gates](https://github.com/tempuku/ivanovo_models/issues/12) | [PR #18 merged](https://github.com/tempuku/ivanovo_models/pull/18) | Deterministic mesh/bed checks and an explicit *manual* slicer-evidence protocol; no claim of an actual Bambu print. |
| [#14 Legacy inventory](https://github.com/tempuku/ivanovo_models/issues/14) | [PR #16 merged](https://github.com/tempuku/ivanovo_models/pull/16) | Immutable legacy references and `viewer/catalog.json` with missing/blocked states rather than invented assets. |
| [#3 Unified viewer](https://github.com/tempuku/ivanovo_models/issues/3) | [PR #15 merged](https://github.com/tempuku/ivanovo_models/pull/15) | **Issue closed, but only viewer state/assembly groundwork merged.** No working shared root HTML/3D renderer or browser acceptance yet. |
| [#4 GitHub Pages deployment](https://github.com/tempuku/ivanovo_models/issues/4) | [PR #7 open](https://github.com/tempuku/ivanovo_models/pull/7) | Phase A synthetic fixture/allowlist CI passed, but PR has merge conflicts and is not merged. The publish job was skipped; no authorized live Ivanovo preview. |

Open work: [#10 four-color manufacturing](https://github.com/tempuku/ivanovo_models/issues/10), [#11 serviceable Big LED](https://github.com/tempuku/ivanovo_models/issues/11), [#13 resumable production workflow](https://github.com/tempuku/ivanovo_models/issues/13), real root viewer integration under #3, and deployment Phase B under #4. Physical test printing, installed P2S accessories and any claims of final release remain unverified.

## How to check — GitHub evidence

1. Open the [issue list](https://github.com/tempuku/ivanovo_models/issues) and [pull requests](https://github.com/tempuku/ivanovo_models/pulls?q=is%3Apr) while signed in. Confirm `merged_at` for PRs #5, #8, #16, #17, #18 and #15; don't infer full scope from closed-issue badges.
2. Check [building pipeline CI](https://github.com/tempuku/ivanovo_models/actions/workflows/building-tests.yml), [real OpenSCAD colored-master CI](https://github.com/tempuku/ivanovo_models/actions/workflows/openscad-master-ci.yml), and [OpenWiki validation](https://github.com/tempuku/ivanovo_models/actions/workflows/validate-openwiki.yml) **at the current `main` commit**; a green run only validates that workflow's scope.
3. For deployment, inspect [PR #7](https://github.com/tempuku/ivanovo_models/pull/7) (mergeability, checks and changed files) and [issue #4](https://github.com/tempuku/ivanovo_models/issues/4). A green fixture CI or skipped `publish` job is **not** a public live-site check.
4. Read [OpenWiki viewer verification](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md) and [building pipeline guide](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/BUILDING_PIPELINE.md) for the current limitations and evidence contract.

## How to check — from a local checkout

Requires access to the private repository, Python 3.11+ and Node; the real geometry test additionally requires the OpenSCAD CLI.

```sh
git clone https://github.com/tempuku/ivanovo_models.git
cd ivanovo_models
git switch main
git pull --ff-only

# Unit checks and independent catalog integrity:
python3 -m unittest discover -s tests -p 'test_building_*.py' -v
python3 -m unittest discover -s tests -p 'test_printer_profiles.py' -v
python3 -m tools.building.catalog --check
node --test viewer/tests/state.test.mjs

# Actual OpenSCAD -> independent colored GLB starter export:
python3 -m tools.building.ci_verify_colored_master \
  --openscad openscad --output-dir /tmp/ivanovo-colored-master-check
```

Inspect `/tmp/ivanovo-colored-master-check/verification.json`, `preview/master.glb` and `preview/catalog.json` after the real export. These prove a **starter fixture** works, not that every historical building has a verified colored master.

The checked-in `viewer/state.mjs` and `viewer/catalog.json` are **not** a functioning root 3D viewer. To accept #3, an HTTP-served shared viewer must load actual verified assets and pass browser controls, per-part explode/assemble and four-building navigation. To accept #4, require an actual authorized Pages URL and browser navigation, not a generated artifact or CI badge. For a physical manufacturing release, require the actual printer/slicer profile and recorded test print, assembly and LED evidence; none is inferred from the commands above.

**Privacy:** This Knowledge Hub source repository is public, including notes marked `visibility: private`. Do not add confidential model references, unpublished photographs, credentials or private manufacturing assets here. This summary only points back to authoritative GitHub sources.
