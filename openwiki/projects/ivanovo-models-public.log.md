# Record history

## Entry 1e26b8e8-cc64-46dd-923b-ea0163481012
```json
{
  "schema_version": 1,
  "id": "1e26b8e8-cc64-46dd-923b-ea0163481012",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "1e26b8e8-cc64-46dd-923b-ea0163482012",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-18T19:13:33Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "public-demo-fixture",
    "kind": "agent",
    "label": "Public Demo"
  },
  "summary": "Create explicitly public demonstration record",
  "path_before": null,
  "path_after": "openwiki/projects/ivanovo-models-public.md",
  "before": null,
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n",
  "before_sha256": null,
  "after_sha256": "c07f8b2e83a1a26f65174a580e5bdb7362b32c7d16daf009d894b181723ab27d",
  "previous_event_id": null,
  "idempotency_key": "1e26b8e8-cc64-46dd-923b-ea0163483012",
  "request_sha256": "48ac449d1ac3f3a042c5387be0e871a966171918423e16af57362738875c2fbc",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry 16fb991b-86f3-437b-a4c5-28b3f7af6e92
```json
{
  "schema_version": 1,
  "id": "16fb991b-86f3-437b-a4c5-28b3f7af6e92",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "eca4ba9d-6a89-479c-af7e-5f5075f6b104",
  "sequence": 2,
  "action": "UPDATED",
  "recorded_at": "2026-11-19T18:32:58Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "chatgpt-agent",
    "kind": "agent",
    "label": "Knowledge Hub evidence links"
  },
  "summary": "Link related project record and evidence graph",
  "path_before": "openwiki/projects/ivanovo-models-public.md",
  "path_after": "openwiki/projects/ivanovo-models-public.md",
  "before": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n",
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "before_sha256": "c07f8b2e83a1a26f65174a580e5bdb7362b32c7d16daf009d894b181723ab27d",
  "after_sha256": "c28e85eb7fb174507986965ded0bbaa22b420e3bffc12d044bbcbf24f064d2a3",
  "previous_event_id": "1e26b8e8-cc64-46dd-923b-ea0163481012",
  "idempotency_key": "17efbb1f-b32c-4307-a5ae-77eb403d1350",
  "request_sha256": "19bfa015bc4652d2ab6605d24bc2cec0d73326ade32e36d8934bc3a1047f47a6",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry dc3c6a9f-5719-4071-bce0-850b6b8058eb
```json
{
  "schema_version": 1,
  "id": "dc3c6a9f-5719-4071-bce0-850b6b8058eb",
  "record_id": "1e26b8e8-cc64-46dd-923b-ea0163480012",
  "operation_id": "361bfa8a-505a-4e0d-806a-0fd99144f3be",
  "sequence": 3,
  "action": "UPDATED",
  "recorded_at": "2026-11-21T21:09:24Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Publish the canonical Ivanovo project record as the public project",
  "path_before": "openwiki/projects/ivanovo-models-public.md",
  "path_after": "openwiki/projects/ivanovo-models-public.md",
  "before": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo Models (public demo)\"\ndescription: \"Public demo project card for architectural model tracking.\"\nstatus: in_progress\nvisibility: public\ntags: [demo, architecture, three-d-printing]\n---\n\n# Ivanovo Models - public demo\n\nTrack architectural model planning and 3D printing work here. This demo project has no private repository artifacts, printer files, or unpublished references.\n\n## Linked records and evidence\n\n- [Knowledge Hub public project overview](record:9a2f68b9-a1a9-40c6-ae1c-6224e1630011) - the parent knowledge-system project explaining shared record/log and visibility principles.\n- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/ivanovo-models-public.log.md) - this public demo's own recorded changes.\n- [Knowledge Hub traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - public documentation for related-record discovery.\n\nNo private model sources, files or manufacturing evidence are included in this public overview. The authoritative private project may provide additional evidence only to authorized readers.\n",
  "after": "---\nid: \"1e26b8e8-cc64-46dd-923b-ea0163480012\"\nschema_version: 1\ntype: project\ntitle: \"Ivanovo architectural 3D models\"\ndescription: \"Canonical Ivanovo architectural 3D models project: production contract, viewer status and evidence links.\"\nstatus: in_progress\nvisibility: public\ntags: [architecture, openscad, 3d-printing, viewer]\nsources:\n  - resource: https://github.com/tempuku/ivanovo_models\n    title: Source repository\n  - resource: https://github.com/tempuku/ivanovo_models/pull/17\n    title: Colored master implementation\n  - resource: https://github.com/tempuku/ivanovo_models/pull/18\n    title: Mesh and slicer evidence implementation\n  - resource: https://github.com/tempuku/ivanovo_models/pull/15\n    title: Viewer-state groundwork\n  - resource: https://github.com/tempuku/ivanovo_models/pull/7\n    title: Merged optional-public-demo CI foundation\n  - resource: https://github.com/tempuku/ivanovo_models/pull/19\n    title: Open draft shared GLB viewer integration\n  - resource: https://github.com/tempuku/ivanovo_models/pull/20\n    title: Merged read-only authenticated viewer gateway\n---\n\n\n# Ivanovo architectural 3D models\n\nCanonical development source: [tempuku/ivanovo_models](https://github.com/tempuku/ivanovo_models) (private; requires GitHub repository access). This note is a **manual snapshot from 2026-11-09**, not an automatically synchronized status feed. For current state, consult the linked issues, merged PRs, CI and repository files.\n\n## Architecture and production contract\n\n- One detailed, material-colored architectural master independent of HTML; printable geometry should derive directly from the master where practical (master-first, without automatic detail loss).\n- Five mandatory print configurations: Big (~200 mm) single-color, four-color, LED; Small (~100–120 mm) single-color and four-color. **No Small LED.** Optional separate-per-floor Big LED is experimental.\n- Preserve real XYZ proportions; choose a 1:N architectural scale with denominator stepped by 10, and flag unverified reference dimensions as provisional.\n- The current example printer profile is Bambu Lab P2S, but printer, nozzle, process and installed multicolor equipment must be configured/verified independently.\n- A shared DRY root viewer should load reusable preview geometry/metadata; House-Ship is the look-and-feel reference, Horseshoe provides real multipart explode/assemble behavior.\n- Generated assets, slicer evidence, test prints, assembly and physical signoff are **different acceptance stages**.\n\n## Implementation snapshot — 2026-11-09\n\n| Work | Evidence | What is actually verified |\n| --- | --- | --- |\n| [#1 Standards](https://github.com/tempuku/ivanovo_models/issues/1) | [PR #5 merged](https://github.com/tempuku/ivanovo_models/pull/5) | OpenWiki standards and ADR; not manufacturing evidence. |\n| [#2 Template foundation](https://github.com/tempuku/ivanovo_models/issues/2) | [PR #8 merged](https://github.com/tempuku/ivanovo_models/pull/8) | Scaffold, configurable printer/process profiles, manifests; **foundation-only**. |\n| [#9 Independent colored master](https://github.com/tempuku/ivanovo_models/issues/9) | [PR #17 merged](https://github.com/tempuku/ivanovo_models/pull/17) | Reproducible OpenSCAD-to-colored-GLB **starter fixture** and hash/material verification. This does not approve real buildings. |\n| [#12 Mesh/slicer evidence gates](https://github.com/tempuku/ivanovo_models/issues/12) | [PR #18 merged](https://github.com/tempuku/ivanovo_models/pull/18) | Deterministic mesh/bed checks and an explicit *manual* slicer-evidence protocol; no claim of an actual Bambu print. |\n| [#14 Legacy inventory](https://github.com/tempuku/ivanovo_models/issues/14) | [PR #16 merged](https://github.com/tempuku/ivanovo_models/pull/16) | Immutable legacy references and `viewer/catalog.json` with missing/blocked states rather than invented assets. |\n| [#3 Unified viewer](https://github.com/tempuku/ivanovo_models/issues/3) | [PR #15 merged](https://github.com/tempuku/ivanovo_models/pull/15); [PR #19 draft](https://github.com/tempuku/ivanovo_models/pull/19) | Groundwork is on `main`. Draft #19 adds the shared catalog UI and GLB renderer; its synthetic, hash-verified WebGL browser smoke passed, **not** real-building acceptance. #19 is not merged. |\n| [#4 Delivery: private production, optional public demo](https://github.com/tempuku/ivanovo_models/issues/4) | [PR #7 merged](https://github.com/tempuku/ivanovo_models/pull/7); [PR #20 merged](https://github.com/tempuku/ivanovo_models/pull/20) | Phase A public-demo-only CI and Phase B1 read-only Cloudflare Access gateway code are on `main`. All four PR #20 rerun workflows passed. **No Cloudflare live site, credential provisioning or public Pages publishing has occurred.** |\n\n**Privacy-first delivery update:** The canonical `ivanovo_models` repository remains **private**. A shared private viewer should require verified identity on every HTML, JavaScript, catalog, Markdown and GLB request; its GitHub read credential belongs server-side only. PR #20 supplies the read-only Worker transport and tests, but configuring Access for all Worker/preview hostnames, setting a least-privilege read token, verifying anonymous denial at a live HTTPS URL and testing real building exports remain outstanding. The optional GitHub Pages path may publish **only** a separately approved synthetic/public payload; it is not a private-record gateway. See [Knowledge Hub ADR 0001](../adr/0001-private-records-authenticated-app.md) for the shared security principle; the Knowledge Hub private diary itself is a different, still-unimplemented product.\n\nOpen work: [#10 four-color manufacturing](https://github.com/tempuku/ivanovo_models/issues/10), [#11 serviceable Big LED](https://github.com/tempuku/ivanovo_models/issues/11), [#13 resumable production workflow](https://github.com/tempuku/ivanovo_models/issues/13), real root viewer integration under #3, and private production deployment/verification under #4. Physical test printing, installed P2S accessories and any claims of final release remain unverified.\n\n## How to check — GitHub evidence\n\n1. Open the [issue list](https://github.com/tempuku/ivanovo_models/issues) and [pull requests](https://github.com/tempuku/ivanovo_models/pulls?q=is%3Apr) while signed in. Confirm merges for PRs #5, #8, #16, #17, #18, #15, #7 and #20. Confirm PR #19 is still **draft/open**; do not infer full scope from closed-issue badges.\n2. Check [building pipeline CI](https://github.com/tempuku/ivanovo_models/actions/workflows/building-tests.yml), [real OpenSCAD colored-master CI](https://github.com/tempuku/ivanovo_models/actions/workflows/openscad-master-ci.yml), and [OpenWiki validation](https://github.com/tempuku/ivanovo_models/actions/workflows/validate-openwiki.yml) **at the current `main` commit**; a green run only validates that workflow's scope.\n3. For delivery, inspect merged [PR #7](https://github.com/tempuku/ivanovo_models/pull/7), merged [PR #20](https://github.com/tempuku/ivanovo_models/pull/20), [issue #4](https://github.com/tempuku/ivanovo_models/issues/4) and [the successful rerun of the private auth workflow](https://github.com/tempuku/ivanovo_models/actions/runs/42677163711). The original PR #20 runs failed with zero jobs (no job logs); the new commit triggered jobs that passed. Neither successful CI nor skipped public `publish` establishes a live private or public site.\n4. Read [OpenWiki viewer verification](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/VIEWER.md) and [building pipeline guide](https://github.com/tempuku/ivanovo_models/blob/main/openwiki/BUILDING_PIPELINE.md) for the current limitations and evidence contract.\n\n## How to check — from a local checkout\n\nRequires access to the private repository, Python 3.11+ and Node; the real geometry test additionally requires the OpenSCAD CLI.\n\n```sh\ngit clone https://github.com/tempuku/ivanovo_models.git\ncd ivanovo_models\ngit switch main\ngit pull --ff-only\n\n# Unit checks and independent catalog integrity:\npython3 -m unittest discover -s tests -p 'test_building_*.py' -v\npython3 -m unittest discover -s tests -p 'test_printer_profiles.py' -v\npython3 -m tools.building.catalog --check\nnode --test viewer/tests/state.test.mjs\nnode --test tools/private_viewer/worker.test.mjs\npython3 -m unittest discover -s tests -p 'test_deploy_preview.py' -v\n\n# Actual OpenSCAD -> independent colored GLB starter export:\npython3 -m tools.building.ci_verify_colored_master \\\n  --openscad openscad --output-dir /tmp/ivanovo-colored-master-check\n```\n\nInspect `/tmp/ivanovo-colored-master-check/verification.json`, `preview/master.glb` and `preview/catalog.json` after the real export. These prove a **starter fixture** works, not that every historical building has a verified colored master.\n\nThe checked-in `viewer/state.mjs` and `viewer/catalog.json` are **not** a functioning root 3D viewer. PR #19 contains the still-unmerged renderer and browser smoke tests. To accept #3, an HTTP-served shared viewer must load actual verified building assets and pass visual/browser controls, legitimate multipart explode/assemble and four-building navigation. To accept #4, require a **real authenticated private HTTPS URL** with anonymous GET/HEAD denial and approved-user access, not a generated artifact or CI badge. Public Pages is optional and requires separate explicit owner approval. For a physical manufacturing release, require the actual printer/slicer profile and recorded test print, assembly and LED evidence; none is inferred from the commands above.\n\n**Privacy:** This Knowledge Hub source repository is public, including notes marked `visibility: private`. Do not add confidential model references, unpublished photographs, credentials or private manufacturing assets here. This summary only points back to authoritative GitHub sources.\n",
  "before_sha256": "c28e85eb7fb174507986965ded0bbaa22b420e3bffc12d044bbcbf24f064d2a3",
  "after_sha256": "3a0c5feb11a8f5e464e8a8c64cbf693615dcdb051eb4b198769952aab34b9438",
  "previous_event_id": "16fb991b-86f3-437b-a4c5-28b3f7af6e92",
  "idempotency_key": "565b5bcd-1ae1-4660-986e-bcbbf464efb1",
  "request_sha256": "0b882742d05040b38975d1886b8a1b2fe63b9e2d7a4c7a09cab40119b703e883",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
