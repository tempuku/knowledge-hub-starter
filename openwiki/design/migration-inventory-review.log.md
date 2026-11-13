# Record history

## Entry aac64224-8e62-4bab-bd0d-32575c91a3a7
```json
{
  "schema_version": 1,
  "id": "aac64224-8e62-4bab-bd0d-32575c91a3a7",
  "record_id": "41472c01-62c7-4b80-ad27-4aa1b4888fac",
  "operation_id": "1ad9db40-9fd3-42f4-9701-383c1fe24632",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-13T09:17:30Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "codex-agent",
    "kind": "agent",
    "label": "Codex"
  },
  "summary": "Register reviewed inventory evidence as a native draft record",
  "path_before": null,
  "path_after": "openwiki/design/migration-inventory-review.md",
  "before": null,
  "after": "---\nid: \"41472c01-62c7-4b80-ad27-4aa1b4888fac\"\nschema_version: 1\ntype: \"guide\"\ntitle: \"Migration inventory review\"\nstatus: \"draft\"\nvisibility: \"private\"\n---\n\n# Migration inventory review — issue #35\n\n**Frozen base:** `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` (merged #30).\n**Status:** NOT REVIEWED; NOT APPROVED FOR MIGRATION OR PUBLICATION.\n\n## Reproducible inventory\n\nRun `python3 scripts/inventory_legacy.py --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` and then the same command with `--check`. This reads exact tracked bytes from the frozen Git tree, including dated notes and directory `log.md` files. It excludes structural `index.md` files as required by M-01. Every entry carries its SHA-256 and explicit nullable fields. No random IDs are assigned on reruns, and no source files are modified.\n\n**Important:** A generated inventory is not a reviewed manifest. All disposition, stable ID, project/area, destination, visibility, provenance, and legacy event mappings remain unset until evidence-based reconciliation. The generator deliberately fails closed rather than guessing from filenames. A separate review must account for structural indexes and links.\n\n## Required reconciliation before approval\n\n- Verify each native log's final after snapshot against current source bytes; inspect GUIDE and concepts/diary-diff-demo divergence first.\n- Distinguish duplicate dated update journals from independent substantive notes using event identity and full content, not similar titles or dates.\n- Preserve uncertain/decreasing original timestamps as provenance and document any proposed normalization.\n- Allocate and persist stable record/event IDs once; resolve destination collisions, missing metadata, broken links, project identity and visibility case by case.\n- Produce a separate explicit public record/event allowlist; no imported event is public by default.\n- Record P10/P13/P15 evidence with exact SHA, commands and outcomes. Do not run cutover under #35.\n\n## Current evidence and limits\n\nThe frozen Git tree can be enumerated, and #30 is closed and merged. A reproducible inventory check at `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` passed with 45 non-index Markdown sources; the generated inventory remains pending, with every disposition and mapping unset. A direct byte comparison of each parsed final legacy `after` snapshot with its source at that revision found one mismatch: `openwiki/concepts/diary-diff-demo.md` is 625 bytes (`6e9ba9c3dc138ab1408384167d9d98741c805504cf6ae24106a77ebf95811380`), while the final after snapshot is 622 bytes (`8f8ef83e4a8f331f31d8f217088c91f4374eca8490b619cf4c29b20bb90279e4`). `openwiki/GUIDE.md` matches its final snapshot at this frozen revision (both SHA-256 `7d012e6fb6c946a17750dd2c4c5a9c3f48c1a6ec2d28e44f0c8ddf7136a19f7d`). This was a narrow snapshot comparison, not a full-content or provenance review. No reconciliation sign-off, privacy allowlist, CI result, or migration acceptance has been produced. This document must not be treated as approval. The final manifest must be committed only after a complete audit and validation, and no unresolved disposition may be accepted.\n",
  "before_sha256": null,
  "after_sha256": "e22585fb376de8bd8c1a4e8df52239c6fb9920ed8de32cdc3b60121ba204b10f",
  "previous_event_id": null,
  "idempotency_key": "1ad9db40-9fd3-42f4-9701-383c1fe24632",
  "request_sha256": "9065b8bbf2f93d9b954463f2bd81586a424c204f1948f7d82c290a764a5f58ef",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```

## Entry f7875bc2-5558-443f-aff6-d638c42b4f44
```json
{
  "schema_version": 1,
  "id": "f7875bc2-5558-443f-aff6-d638c42b4f44",
  "record_id": "41472c01-62c7-4b80-ad27-4aa1b4888fac",
  "operation_id": "9be46da9-17bb-45ca-a3f9-99cbdc655067",
  "sequence": 2,
  "action": "UPDATED",
  "recorded_at": "2026-11-13T09:18:47Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "codex-agent",
    "kind": "agent",
    "label": "Codex"
  },
  "summary": "Record reproducible frozen snapshot comparison evidence and public technical report visibility",
  "path_before": "openwiki/design/migration-inventory-review.md",
  "path_after": "openwiki/design/migration-inventory-review.md",
  "before": "---\nid: \"41472c01-62c7-4b80-ad27-4aa1b4888fac\"\nschema_version: 1\ntype: \"guide\"\ntitle: \"Migration inventory review\"\nstatus: \"draft\"\nvisibility: \"private\"\n---\n\n# Migration inventory review — issue #35\n\n**Frozen base:** `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` (merged #30).\n**Status:** NOT REVIEWED; NOT APPROVED FOR MIGRATION OR PUBLICATION.\n\n## Reproducible inventory\n\nRun `python3 scripts/inventory_legacy.py --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` and then the same command with `--check`. This reads exact tracked bytes from the frozen Git tree, including dated notes and directory `log.md` files. It excludes structural `index.md` files as required by M-01. Every entry carries its SHA-256 and explicit nullable fields. No random IDs are assigned on reruns, and no source files are modified.\n\n**Important:** A generated inventory is not a reviewed manifest. All disposition, stable ID, project/area, destination, visibility, provenance, and legacy event mappings remain unset until evidence-based reconciliation. The generator deliberately fails closed rather than guessing from filenames. A separate review must account for structural indexes and links.\n\n## Required reconciliation before approval\n\n- Verify each native log's final after snapshot against current source bytes; inspect GUIDE and concepts/diary-diff-demo divergence first.\n- Distinguish duplicate dated update journals from independent substantive notes using event identity and full content, not similar titles or dates.\n- Preserve uncertain/decreasing original timestamps as provenance and document any proposed normalization.\n- Allocate and persist stable record/event IDs once; resolve destination collisions, missing metadata, broken links, project identity and visibility case by case.\n- Produce a separate explicit public record/event allowlist; no imported event is public by default.\n- Record P10/P13/P15 evidence with exact SHA, commands and outcomes. Do not run cutover under #35.\n\n## Current evidence and limits\n\nThe frozen Git tree can be enumerated, and #30 is closed and merged. A reproducible inventory check at `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` passed with 45 non-index Markdown sources; the generated inventory remains pending, with every disposition and mapping unset. A direct byte comparison of each parsed final legacy `after` snapshot with its source at that revision found one mismatch: `openwiki/concepts/diary-diff-demo.md` is 625 bytes (`6e9ba9c3dc138ab1408384167d9d98741c805504cf6ae24106a77ebf95811380`), while the final after snapshot is 622 bytes (`8f8ef83e4a8f331f31d8f217088c91f4374eca8490b619cf4c29b20bb90279e4`). `openwiki/GUIDE.md` matches its final snapshot at this frozen revision (both SHA-256 `7d012e6fb6c946a17750dd2c4c5a9c3f48c1a6ec2d28e44f0c8ddf7136a19f7d`). This was a narrow snapshot comparison, not a full-content or provenance review. No reconciliation sign-off, privacy allowlist, CI result, or migration acceptance has been produced. This document must not be treated as approval. The final manifest must be committed only after a complete audit and validation, and no unresolved disposition may be accepted.\n",
  "after": "---\nid: \"41472c01-62c7-4b80-ad27-4aa1b4888fac\"\nschema_version: 1\ntype: \"guide\"\ntitle: \"Migration inventory review\"\nstatus: \"draft\"\nvisibility: \"public\"\n---\n\n# Migration inventory review — issue #35\n\n**Frozen base:** `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` (merged #30).\n**Status:** NOT REVIEWED; NOT APPROVED FOR MIGRATION OR PUBLICATION.\n\n## Reproducible inventory\n\nRun `python3 scripts/inventory_legacy.py --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` and then the same command with `--check`. This reads exact tracked bytes from the frozen Git tree, including dated notes and directory `log.md` files. It excludes structural `index.md` files as required by M-01. Every entry carries its SHA-256 and explicit nullable fields. No random IDs are assigned on reruns, and no source files are modified.\n\n**Important:** A generated inventory is not a reviewed manifest. All disposition, stable ID, project/area, destination, visibility, provenance, and legacy event mappings remain unset until evidence-based reconciliation. The generator deliberately fails closed rather than guessing from filenames. A separate review must account for structural indexes and links.\n\n## Required reconciliation before approval\n\n- Verify each native log's final after snapshot against current source bytes; inspect GUIDE and concepts/diary-diff-demo divergence first.\n- Distinguish duplicate dated update journals from independent substantive notes using event identity and full content, not similar titles or dates.\n- Preserve uncertain/decreasing original timestamps as provenance and document any proposed normalization.\n- Allocate and persist stable record/event IDs once; resolve destination collisions, missing metadata, broken links, project identity and visibility case by case.\n- Produce a separate explicit public record/event allowlist; no imported event is public by default.\n- Record P10/P13/P15 evidence with exact SHA, commands and outcomes. Do not run cutover under #35.\n\n## Current evidence and limits\n\nThe frozen Git tree can be enumerated, and #30 is closed and merged. A reproducible inventory check at `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` passed with 45 non-index Markdown sources; the generated inventory remains pending, with every disposition and mapping unset. Run `python3 scripts/inventory_legacy.py --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb --check-snapshots` to reproduce the paired-history byte comparison (expected exit 1 because it found one mismatch among 22 pairs). It found one mismatch: `openwiki/concepts/diary-diff-demo.md` is 625 bytes (`6e9ba9c3dc138ab1408384167d9d98741c805504cf6ae24106a77ebf95811380`), while the final after snapshot is 622 bytes (`8f8ef83e4a8f331f31d8f217088c91f4374eca8490b619cf4c29b20bb90279e4`). `openwiki/GUIDE.md` matches its final snapshot at this frozen revision (both SHA-256 `7d012e6fb6c946a17750dd2c4c5a9c3f48c1a6ec2d28e44f0c8ddf7136a19f7d`). This was a narrow snapshot comparison, not a full-content or provenance review. No reconciliation sign-off, privacy allowlist, CI result, or migration acceptance has been produced. This document must not be treated as approval. The final manifest must be committed only after a complete audit and validation, and no unresolved disposition may be accepted.\n",
  "before_sha256": "e22585fb376de8bd8c1a4e8df52239c6fb9920ed8de32cdc3b60121ba204b10f",
  "after_sha256": "aa09928cad70b18f713afdae86fd2ad386d36a8e5322e61de4a3a553808134b4",
  "previous_event_id": "aac64224-8e62-4bab-bd0d-32575c91a3a7",
  "idempotency_key": "9be46da9-17bb-45ca-a3f9-99cbdc655067",
  "request_sha256": "a0565192286b668893ec081681d991fd490499369e8e0e5f3fda24de7b0cf9a2",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
