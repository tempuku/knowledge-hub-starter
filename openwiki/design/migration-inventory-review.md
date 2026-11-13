---
id: "41472c01-62c7-4b80-ad27-4aa1b4888fac"
schema_version: 1
type: "guide"
title: "Migration inventory review"
status: "draft"
visibility: "public"
---

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

The frozen Git tree can be enumerated, and #30 is closed and merged. A reproducible inventory check at `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` passed with 45 non-index Markdown sources; the generated inventory remains pending, with every disposition and mapping unset. Run `python3 scripts/inventory_legacy.py --revision de749bed9053dd4bc9f96fee3cb7f816e5bdebcb --check-snapshots` to reproduce the paired-history byte comparison (expected exit 1 because it found one mismatch among 22 pairs). It found one mismatch: `openwiki/concepts/diary-diff-demo.md` is 625 bytes (`6e9ba9c3dc138ab1408384167d9d98741c805504cf6ae24106a77ebf95811380`), while the final after snapshot is 622 bytes (`8f8ef83e4a8f331f31d8f217088c91f4374eca8490b619cf4c29b20bb90279e4`). `openwiki/GUIDE.md` matches its final snapshot at this frozen revision (both SHA-256 `7d012e6fb6c946a17750dd2c4c5a9c3f48c1a6ec2d28e44f0c8ddf7136a19f7d`). This was a narrow snapshot comparison, not a full-content or provenance review. No reconciliation sign-off, privacy allowlist, CI result, or migration acceptance has been produced. This document must not be treated as approval. The final manifest must be committed only after a complete audit and validation, and no unresolved disposition may be accepted.
