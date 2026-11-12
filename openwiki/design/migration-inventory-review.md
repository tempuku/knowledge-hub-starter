# Migration inventory review — issue #35

**Frozen base:** `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` (merged #30).
**Status:** NOT REVIEWED; NOT APPROVED FOR MIGRATION OR PUBLICATION.

## Reproducible inventory

Run `python3 scripts/inventory_legacy.py --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` and then the same command with `--check`. This reads exact tracked bytes from the frozen Git tree, including dated notes and directory `log.md` files. It excludes structural `index.md` files as required by M-01. Every entry carries its SHA-256 and explicit nullable fields. No random IDs are assigned on reruns, and no source files are modified.

**Important:** A generated inventory is not a reviewed manifest. All disposition, stable ID, project/area, destination, visibility, provenance, and legacy event mappings remain unset until evidence-based reconciliation. The generator deliberately fails closed rather than guessing from filenames. A separate review must account for structural indexes and links.

## Required reconciliation before approval

- Verify each native log's final after snapshot against current source bytes; inspect GUIDE and concepts/diary-diff-demo divergence first.
- Distinguish duplicate dated update journals from independent substantive notes using event identity and full content, not similar titles or dates.
- Preserve uncertain/decreasing original timestamps as provenance and document any proposed normalization.
- Allocate and persist stable record/event IDs once; resolve destination collisions, missing metadata, broken links, project identity and visibility case by case.
- Produce a separate explicit public record/event allowlist; no imported event is public by default.
- Record P10/P13/P15 evidence with exact SHA, commands and outcomes. Do not run cutover under #35.

## Current evidence and limits

The frozen Git tree can be enumerated, and #30 is closed and merged. No full-content review, SHA-256 manifest output, reconciliation sign-off, privacy allowlist, CI result, or migration acceptance has yet been produced in this branch. This document must not be treated as approval. The final manifest must be committed only after a complete audit and validation, and no unresolved disposition may be accepted.
