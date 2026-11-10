# OKF Record Change Log

## Entry git-727f862f2664ec06
```json
{
  "id": "git-727f862f2664ec06",
  "timestamp": "2026-11-09T15:26:09Z",
  "actor": "tempuku",
  "action": "CREATED",
  "summary": "Initial import",
  "record": "openwiki/journal/2026/11/09/shared-viewer.md",
  "visibility": "private",
  "before": null,
  "after": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: private\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n---\n\n# One viewer, many buildings\n\nThe House-Ship viewer establishes the desired visual language. Horseshoe contributes the ability to hide/show parts and explode/assemble actual multipart models. The app loads reusable independently colored master geometry and variant assets dynamically, with no normal per-building HTML duplication.\n\n[Implementation checklist and status](https://github.com/tempuku/ivanovo_models/issues/3).\n",
  "before_sha256": null,
  "after_sha256": "3b76947ca4478bd4f734e0c6f4300b0e0a74dff4f3a3727869a390d722f80219",
  "source_commit": "727f862f2664ec068c172a05ccd35c350a47acc3",
  "provenance": "git-backfill"
}
```

## Entry git-2ef2bcf51641c7b3
```json
{
  "id": "git-2ef2bcf51641c7b3",
  "timestamp": "2026-11-09T17:23:58Z",
  "actor": "tempuku",
  "action": "UPDATED",
  "summary": "Publish approved OKF project notes through live diary",
  "record": "openwiki/journal/2026/11/09/shared-viewer.md",
  "visibility": "public",
  "before": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: private\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n---\n\n# One viewer, many buildings\n\nThe House-Ship viewer establishes the desired visual language. Horseshoe contributes the ability to hide/show parts and explode/assemble actual multipart models. The app loads reusable independently colored master geometry and variant assets dynamically, with no normal per-building HTML duplication.\n\n[Implementation checklist and status](https://github.com/tempuku/ivanovo_models/issues/3).\n",
  "after": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: public\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n---\n\n# One viewer, many buildings\n\nThe House-Ship viewer establishes the desired visual language. Horseshoe contributes the ability to hide/show parts and explode/assemble actual multipart models. The app loads reusable independently colored master geometry and variant assets dynamically, with no normal per-building HTML duplication.\n\n[Implementation checklist and status](https://github.com/tempuku/ivanovo_models/issues/3).\n",
  "before_sha256": "3b76947ca4478bd4f734e0c6f4300b0e0a74dff4f3a3727869a390d722f80219",
  "after_sha256": "b164ee303f58851424c6b0d12b6a3ada8c782a02755a4ded3cfb08510850e056",
  "source_commit": "2ef2bcf51641c7b3b10de60fee6f9a1db20790a8",
  "provenance": "git-backfill"
}
```

## Entry git-cc380ce2d6cf3289
```json
{
  "id": "git-cc380ce2d6cf3289",
  "timestamp": "2026-11-09T18:45:52Z",
  "actor": "tempuku",
  "action": "UPDATED",
  "summary": "docs: record verified Ivanovo and Knowledge Hub progress with check steps (#6)",
  "record": "openwiki/journal/2026/11/09/shared-viewer.md",
  "visibility": "public",
  "before": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: public\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n---\n\n# One viewer, many buildings\n\nThe House-Ship viewer establishes the desired visual language. Horseshoe contributes the ability to hide/show parts and explode/assemble actual multipart models. The app loads reusable independently colored master geometry and variant assets dynamically, with no normal per-building HTML duplication.\n\n[Implementation checklist and status](https://github.com/tempuku/ivanovo_models/issues/3).\n",
  "after": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: public\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n  - resource: https://github.com/tempuku/ivanovo_models/pull/15\n    title: Viewer-state implementation\n  - resource: https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md\n    title: Viewer implementation and verification guide\n---\n\n# One viewer, many buildings\n\nHouse-Ship establishes the visual language; Horseshoe contributes real-part hide/show and explode/assemble. The planned shared app loads independently colored master geometry and actual manufacturing-part assets dynamically from declarative manifests, rather than embedding duplicate mesh data in separate model-specific HTML apps. Legacy standalone viewers remain usable during migration.\n\n## Implementation check — 2026-11-09\n\n[Issue #3](https://github.com/tempuku/ivanovo_models/issues/3) is **closed**, and [PR #15](https://github.com/tempuku/ivanovo_models/pull/15) merged `viewer/state.mjs` with five Node state tests. This proves *presentation-state logic only*: verified-path gating, five print-variant states, and disassembly transforms limited to real manufacturing parts. It **does not** mean the root HTML viewer, browser renderer or live 3D inspection page exists. The [repository's viewer guide](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md) explicitly lists unfinished acceptance checks.\n\n## How to verify\n\n```sh\n# From an authorized local checkout of tempuku/ivanovo_models on main:\nnode --test viewer/tests/state.test.mjs\npython3 -m tools.building.catalog --check\n```\n\nConfirm `viewer/state.mjs` and `viewer/catalog.json` exist, and inspect the catalog's explicit missing/legacy-only states. Do **not** interpret this as a successful 3D browser test. Viewer completion requires a working HTTP-served root page with real colored assets, four-building navigation, camera/model controls, actual multipart explosion, absent-asset handling, and browser smoke tests. See the [full verification checklist](../../../../projects/ivanovo-models.md).\n",
  "before_sha256": "b164ee303f58851424c6b0d12b6a3ada8c782a02755a4ded3cfb08510850e056",
  "after_sha256": "ec9f8a25d9922793673b94d88027249fa1bbaf55237620fa5155e50f2e216cfa",
  "source_commit": "cc380ce2d6cf328929390945302dcf4e98e463a4",
  "provenance": "git-backfill"
}
```

## Entry baseline-a7fcf8ce9e83401f
```json
{
  "id": "baseline-a7fcf8ce9e83401f",
  "timestamp": "2026-11-09T18:51:55Z",
  "actor": "history-migration",
  "action": "BASELINED",
  "summary": "Current record snapshot; earlier Git history incomplete",
  "record": "openwiki/journal/2026/11/09/shared-viewer.md",
  "visibility": "private",
  "before": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: public\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n  - resource: https://github.com/tempuku/ivanovo_models/pull/15\n    title: Viewer-state implementation\n  - resource: https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md\n    title: Viewer implementation and verification guide\n---\n\n# One viewer, many buildings\n\nHouse-Ship establishes the visual language; Horseshoe contributes real-part hide/show and explode/assemble. The planned shared app loads independently colored master geometry and actual manufacturing-part assets dynamically from declarative manifests, rather than embedding duplicate mesh data in separate model-specific HTML apps. Legacy standalone viewers remain usable during migration.\n\n## Implementation check — 2026-11-09\n\n[Issue #3](https://github.com/tempuku/ivanovo_models/issues/3) is **closed**, and [PR #15](https://github.com/tempuku/ivanovo_models/pull/15) merged `viewer/state.mjs` with five Node state tests. This proves *presentation-state logic only*: verified-path gating, five print-variant states, and disassembly transforms limited to real manufacturing parts. It **does not** mean the root HTML viewer, browser renderer or live 3D inspection page exists. The [repository's viewer guide](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md) explicitly lists unfinished acceptance checks.\n\n## How to verify\n\n```sh\n# From an authorized local checkout of tempuku/ivanovo_models on main:\nnode --test viewer/tests/state.test.mjs\npython3 -m tools.building.catalog --check\n```\n\nConfirm `viewer/state.mjs` and `viewer/catalog.json` exist, and inspect the catalog's explicit missing/legacy-only states. Do **not** interpret this as a successful 3D browser test. Viewer completion requires a working HTTP-served root page with real colored assets, four-building navigation, camera/model controls, actual multipart explosion, absent-asset handling, and browser smoke tests. See the [full verification checklist](../../../../projects/ivanovo-models.md).\n",
  "after": "---\ntype: diary-entry\ntitle: Decide to reuse 3D model assets in one dynamic viewer\ndescription: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.\noccurred_on: \"2026-11-09\"\nproject: ivanovo-models\ntags: [decision, dry, viewer]\nstatus: draft\nvisibility: public\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models/issues/3\n    title: Unified viewer implementation issue\n  - resource: https://github.com/tempuku/ivanovo_models/pull/15\n    title: Viewer-state implementation\n  - resource: https://github.com/tempuku/ivanovo_models/pull/19\n    title: Draft unified viewer implementation\n  - resource: https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md\n    title: Viewer implementation and verification guide\n---\n\n# One viewer, many buildings\n\nHouse-Ship establishes the visual language; Horseshoe contributes real-part hide/show and explode/assemble. The planned shared app loads independently colored master geometry and actual manufacturing-part assets dynamically from declarative manifests, rather than embedding duplicate mesh data in separate model-specific HTML apps. Legacy standalone viewers remain usable during migration.\n\n## Implementation check — 2026-11-09\n\n[Issue #3](https://github.com/tempuku/ivanovo_models/issues/3) is **closed**, and [PR #15](https://github.com/tempuku/ivanovo_models/pull/15) merged `viewer/state.mjs` with five Node state tests. This proves *presentation-state logic only*: verified-path gating, five print-variant states, and disassembly transforms limited to real manufacturing parts. It **does not** mean the root HTML viewer, browser renderer or live 3D inspection page exists on `main`. The [repository's viewer guide](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md) explicitly lists unfinished acceptance checks.\n\n**Later same-day update:** [Draft PR #19](https://github.com/tempuku/ivanovo_models/pull/19) now implements the single catalog interface, independent colored-GLB renderer, SHA-256 verification and sanitized private dry-run packaging. Its [GitHub-hosted synthetic GLB/Chrome smoke](https://github.com/tempuku/ivanovo_models/actions/runs/42666004602) passed. It remains **unmerged**, and the real building-specific portable masters and actual building visual/browser acceptance are still missing. The new [PR #20](https://github.com/tempuku/ivanovo_models/pull/20), which adds read-only authenticated delivery, has merged separately; it does not imply the viewer itself is live.\n\n## How to verify\n\n```sh\n# From an authorized local checkout of tempuku/ivanovo_models on main:\nnode --test viewer/tests/state.test.mjs\npython3 -m tools.building.catalog --check\n```\n\nConfirm `viewer/state.mjs` and `viewer/catalog.json` exist, and inspect the catalog's explicit missing/legacy-only states. Do **not** interpret this as a successful 3D browser test. Viewer completion requires a working HTTP-served root page with real colored assets, four-building navigation, camera/model controls, actual multipart explosion, absent-asset handling, and browser smoke tests. See the [full verification checklist](../../../../projects/ivanovo-models.md).\n",
  "before_sha256": "ec9f8a25d9922793673b94d88027249fa1bbaf55237620fa5155e50f2e216cfa",
  "after_sha256": "a7fcf8ce9e83401fab296f352606d341103fd38d1490d91fc2c17f1c5befafec",
  "source_commit": null,
  "provenance": "unmatched-current-baseline"
}
```
