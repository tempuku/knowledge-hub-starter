---
id: "41472c01-62c7-4b80-ad27-4aa1b4888fac"
schema_version: 1
type: "guide"
title: "Migration inventory review"
status: "draft"
visibility: "public"
---

# Migration inventory review — issue #35

**Frozen source:** `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb` (merged #30). **Decision:** reviewed for deterministic dry run, not approval to cut over or publish. The machine-readable source of individual decisions is [`migration/records-v1.json`](https://github.com/tempuku/knowledge-hub-starter/blob/main/migration/records-v1.json). Its UUIDs and paths are persistent allocations, not values to regenerate.

## Scope and disposition

The frozen Git tree has 45 non-index Markdown sources: 22 canonical records with sibling logs, 22 sibling history logs, and one directory `log.md` with unique prose. The 22 canonical sources remain independent records; nine dated journal pages contain substantive project notes, evidence and links and become topic-filed `note` records. Their native creation entries are already represented in sibling logs, so each logical change projects once. No dated note is classified as a duplicate update solely from its subject or date. The directory summary records November initialization and the Ivanovo link; it becomes a private note. All 22 sibling logs are archived byte-for-byte as historical evidence and are not independent Diary records. Structural `index.md` files remain navigation, outside M-01 source enumeration.

The manifest records each source hash, disposition and destination, and maps 23 retained record IDs, 52 original log event IDs, 61 old UI aliases (52 event-detail and nine dated-record keys), 23 normalization event allocations, one imported baseline for the directory summary, and two evidence-backed Git repairs. Every transformed legacy wrapper has its own fixed event, operation and idempotency UUIDv4 allocation. Root GUIDE and CI stay in place. Existing status values are preserved, including `stable` and `completed`; the directory summary lacking status is reviewed as draft. Legacy `diary-entry` becomes `note`, project slugs map to the two known project UUIDs, and the Legacy Chat slug stays as legacy metadata because no project record exists in this source. Original `occurred_on` and supplied `occurred_at` remain separate factual fields. Git commit times do not become occurrence times.

## History reconciliation and exact repairs

Original JSON entries, causal order, actor, summary, before/after snapshots and timestamp are retained. The 52 event mappings carry stable UUIDs and source references. CI has a four-line gap between its second after snapshot (3,995 bytes) and third before snapshot (4,899 bytes); Git commit `f69def479f23778722547c8310be728e7af9ec35` supplies the exact transition. The allocated `git-backfill` event joins these snapshots, with `original_time: null`, not a fabricated recording or occurrence time.

Of 22 final after snapshots, 21 equal frozen source bytes. The exception is `openwiki/concepts/diary-diff-demo.md`: final log after is 622 bytes, SHA-256 `8f8ef83e4a8f331f31d8f217088c91f4374eca8490b619cf4c29b20bb90279e4`; frozen head is 625 bytes, SHA-256 `6e9ba9c3dc138ab1408384167d9d98741c805504cf6ae24106a77ebf95811380`. Commit `00e0a432208010d2bed2a18cfa4797f13aea949e` supplies the exact `status: stable` to `status: completed` change. Its allocated `git-backfill` event connects the head with null original time. GUIDE already equals its final log snapshot at this revision; its earlier reconciliation remains evidence.

Original timestamps remain provenance. For unknown or decreasing recording timestamps, the importer uses fixed migration UTC recording time for the entire affected chain, preserves original values, and keeps causal sequence. No factual occurrence timestamp is synthesized for either Git repair or the unlogged directory summary. Each of the 22 paired histories begins with null before; no extra baseline is needed. The directory summary has no sibling history, so its separate allocated `IMPORTED` baseline starts from null and records exact frozen source bytes at fixed migration UTC, followed by its distinct normalization event. Target normalization events are allocated after preserved histories, with before equal to the repaired head and after equal to canonical target bytes. Their target sequences are fixed in the manifest.

## Publication decision

The separate `publication_eligibility` object is a reviewed proposal, not deployment authorization. Its only eligible current record is the public Diary diff demo, with its two public-to-public legacy events. It allows no actor labels. Every other imported record/event, both repairs, and all normalization events remain excluded from the public candidate until complete snapshots, references, aliases and generated artifacts pass privacy review in #36. Existing `visibility: public` on a dated note does not grant publication of private project history linked through it. The manifest retains source visibility facts without promising exposure. Unknown visibility is treated private.

## Verification boundary

M-01 review covers all frozen source bytes and dispositions. M-02 has a reproducible transform plan, including two exact snapshot repairs and byte archive. M-03 supplies aliases and restricted eligibility. #36 must run the same-base twice dry run with a fixed timestamp; compare source tree and generated bytes; resolve links and old paths; prove expected event identities; scan public/private candidate artifact bytes and metadata (P15); and build without `.git`. P10 exercises independent note, native creation and duplicate-update fixture; P13 exercises unknown/decreasing timestamps and provenance. These are dry-run acceptance checks, not claims of live migration or publication.
