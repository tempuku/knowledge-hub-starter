---
id: "1e26b8e8-cc64-46dd-923b-ea0163480012"
schema_version: 1
type: "project"
title: "Ivanovo Models — public project"
description: "Canonical Ivanovo public project: production contract,\
  \ viewer status and evidence links."
status: "in_progress"
visibility: "public"
tags:
  - "architecture"
  - "openscad"
  - "3d-printing"
  - "viewer"
---


# Ivanovo Models — public project

Canonical development source: the private Ivanovo repository (private; requires GitHub repository access). This note is a **manual snapshot from 2026-11-09**, not an automatically synchronized status feed. For current state, consult the linked issues, merged PRs, CI and repository files.

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
| #1 Standards | PR #5 merged | OpenWiki standards and ADR; not manufacturing evidence. |
| #2 Template foundation | PR #8 merged | Scaffold, configurable printer/process profiles, manifests; **foundation-only**. |
| #9 Independent colored master | PR #17 merged | Reproducible OpenSCAD-to-colored-GLB **starter fixture** and hash/material verification. This does not approve real buildings. |
| #12 Mesh/slicer evidence gates | PR #18 merged | Deterministic mesh/bed checks and an explicit *manual* slicer-evidence protocol; no claim of an actual Bambu print. |
| #14 Legacy inventory | PR #16 merged | Immutable legacy references and `viewer/catalog.json` with missing/blocked states rather than invented assets. |
| #3 Unified viewer | PR #15 merged; PR #19 draft | Groundwork is on `main`. Draft #19 adds the shared catalog UI and GLB renderer; its synthetic, hash-verified WebGL browser smoke passed, **not** real-building acceptance. #19 is not merged. |
| #4 Delivery: private production, optional public demo | PR #7 merged; PR #20 merged | Phase A public-demo-only CI and Phase B1 read-only Cloudflare Access gateway code are on `main`. All four PR #20 rerun workflows passed. **No Cloudflare live site, credential provisioning or public Pages publishing has occurred.** |

**Privacy-first delivery update:** The canonical `the private Ivanovo repository` repository remains **private**. A shared private viewer should require verified identity on every HTML, JavaScript, catalog, Markdown and GLB request; its GitHub read credential belongs server-side only. PR #20 supplies the read-only Worker transport and tests, but configuring Access for all Worker/preview hostnames, setting a least-privilege read token, verifying anonymous denial at a live HTTPS URL and testing real building exports remain outstanding. The optional GitHub Pages path may publish **only** a separately approved synthetic/public payload; it is not a private-record gateway. See [Knowledge Hub ADR 0001](https://github.com/knowledge-hub-starter/blob/main/openwiki/adr/0001-private-records-authenticated-app.md) for the shared security principle; the Knowledge Hub private diary itself is a different, still-unimplemented product.

Open work: #10 four-color manufacturing, #11 serviceable Big LED, #13 resumable production workflow, real root viewer integration under #3, and private production deployment/verification under #4. Physical test printing, installed P2S accessories and any claims of final release remain unverified.

## How to check — GitHub evidence

1. Open the issue list and pull requests while signed in. Confirm merges for PRs #5, #8, #16, #17, #18, #15, #7 and #20. Confirm PR #19 is still **draft/open**; do not infer full scope from closed-issue badges.
2. Check building pipeline CI, real OpenSCAD colored-master CI, and OpenWiki validation **at the current `main` commit**; a green run only validates that workflow's scope.
3. For delivery, inspect merged PR #7, merged PR #20, issue #4 and the successful rerun of the private auth workflow. The original PR #20 runs failed with zero jobs (no job logs); the new commit triggered jobs that passed. Neither successful CI nor skipped public `publish` establishes a live private or public site.
4. Read OpenWiki viewer verification and building pipeline guide for the current limitations and evidence contract.

## How to check — from a local checkout

Requires access to the private repository, Python 3.11+ and Node; the real geometry test additionally requires the OpenSCAD CLI.

```sh
git clone https://github.com.git
cd the private Ivanovo repository
git switch main
git pull --ff-only

# Unit checks and independent catalog integrity:
python3 -m unittest discover -s tests -p 'test_building_*.py' -v
python3 -m unittest discover -s tests -p 'test_printer_profiles.py' -v
python3 -m tools.building.catalog --check
node --test viewer/tests/state.test.mjs
node --test tools/private_viewer/worker.test.mjs
python3 -m unittest discover -s tests -p 'test_deploy_preview.py' -v

# Actual OpenSCAD -> independent colored GLB starter export:
python3 -m tools.building.ci_verify_colored_master \
  --openscad openscad --output-dir /tmp/ivanovo-colored-master-check
```

Inspect `/tmp/ivanovo-colored-master-check/verification.json`, `preview/master.glb` and `preview/catalog.json` after the real export. These prove a **starter fixture** works, not that every historical building has a verified colored master.

The checked-in `viewer/state.mjs` and `viewer/catalog.json` are **not** a functioning root 3D viewer. PR #19 contains the still-unmerged renderer and browser smoke tests. To accept #3, an HTTP-served shared viewer must load actual verified building assets and pass visual/browser controls, legitimate multipart explode/assemble and four-building navigation. To accept #4, require a **real authenticated private HTTPS URL** with anonymous GET/HEAD denial and approved-user access, not a generated artifact or CI badge. Public Pages is optional and requires separate explicit owner approval. For a physical manufacturing release, require the actual printer/slicer profile and recorded test print, assembly and LED evidence; none is inferred from the commands above.

**Privacy:** This Knowledge Hub source repository is public, including notes marked `visibility: private`. Do not add confidential model references, unpublished photographs, credentials or private manufacturing assets here. This summary only points back to authoritative GitHub sources.
