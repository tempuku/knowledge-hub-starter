---
type: guide
title: Hierarchical Knowledge Hub — implementation design baseline
status: draft
description: Normative storage, history, UI, migration and acceptance contracts; implementation pending.
---

# Hierarchical Knowledge Hub — implementation design baseline

Design owner: repository owner. Tracking: [issue #24](https://github.com/tempuku/knowledge-hub-starter/issues/24).
Source audit baseline: `e68270c2d1dc4c3195eaab4590a74677108f999d`.
The owner requested this design, including UI/UX, and authorized merging the documentation after checks. Merge establishes the implementation baseline; it is not evidence of implementation, migration, deployment or device validation. Frontmatter remains `draft` until the documentation review is recorded. Requirement words MUST, MUST NOT and SHOULD below are normative; SHOULD requires an explicit recorded exception in issue #24.

## D-01: One source model

Each knowledge item has one current Markdown record in a subject hierarchy and one sibling append-only log. The diary is a projection of the logs. There are no separately authored diary copies and no required year/month/day directories for records. Generated date indexes are permitted and required. A personal diary note is a `note` record organized by subject; its creation and edits appear through its log.

Example target paths (illustrative names, not instructions to migrate a particular record):

```text
openwiki/projects/knowledge-hub/storage/record-layout.md
openwiki/projects/knowledge-hub/storage/record-layout.log.md
openwiki/projects/knowledge-hub/storage/index.md
openwiki/ideas/architecture/modular-buildings.md
openwiki/ideas/architecture/modular-buildings.log.md
```

The current file is authoritative for current content; the log is authoritative for revision history. Both form one aggregate and MUST agree at the log head. Neither silently wins if inconsistent: writes and publication stop with an integrity error. Generated JSON, search indexes, counts and calendars are disposable. Git stores and transports the aggregate; Git commit dates are not business-event dates.

## D-02: Domain boundaries

| Context | Owns | Does not own |
|---|---|---|
| Knowledge | Record identity, content, revision chain, lifecycle, invariants | Separate diary documents |
| Writing | Authorization adapter, validation, transaction, concurrency, retry receipt | A second source model for agents |
| Projection | Record catalog, diary, search, reminders, publication filtering | Editing source files or inventing events |
| Reading | Navigation and presentation of a published generation | Reconstructing history from Git |
| Hosting | Authentication and delivery under ADR 0001 | Treating frontmatter as access control |

A record and its events are one `KnowledgeRecord` aggregate. One command changes one record. A move may rewrite links in other records; those are separate record events sharing an operation ID in one atomic repository transaction. The diary still shows one row per record event, with a shared-operation label. No independent `ChangeEntry` aggregate or asynchronous reconciliation queue is introduced.

## D-03: Scope and priority

This contract covers source schemas, trusted CLI/MCP writes, generated read models and a shared read-only browser application. UI views are Today, Projects, Records, Diary and Calendar, plus record/history/diff routes. Global Search is part of Records. It preserves the early-iOS aesthetic and the single `status` field. It introduces no editing controls in the public browser. Authenticated browser editing remains a separate implementation under ADR 0001 and MUST reuse this writer.

Not included: history restore, destructive deletion, collaborative cursors, attachments upload, push notifications, recurring alerts, an SQL database, history compaction, custom user timezones, incremental indexing, or silent AI classification. No implementation may add these as an incidental convenience. Open a new design amendment first.

## D-04: Baseline discrepancies that implementation must fix

| Current source behavior | Required target |
|---|---|
| MCP imports legacy `publish.py`; native writer is separate | One writer, one persisted log format |
| Builder reads dated notes and sibling logs | Post-migration diary reads sibling logs only |
| Log IDs and links depend on paths | Stable record/event UUIDs and ID routes |
| History cards borrow current status/title | Revision metadata is historical; current record is explicitly separate |
| Open displays raw Markdown | Sanitized rendered Markdown; raw source is optional |
| Calendar discards time and does not link records | Preserve supplied time/offset and link canonical record |
| Date click can leave Week visually selected | One route state updates every control |
| Snapshot hashes checked, complete chain not enforced | Complete chain, uniqueness and baseline-prefix validation |

## D-05: Reading order and precedence

Read [records and writes](records-and-writes.md), [projections](projections.md), [UI/UX](ui-ux.md), [migration](migration.md), then [acceptance](acceptance.md). The revised [history ADR](../adr/okf-record-history.md) records the decision. ADR 0001 continues to govern private hosting. This bundle supersedes older target instructions requiring dated source folders, independently authored update journals, optional atomicity, grouped diary rows and mandatory Git-based diff lookup.

Current commands are transitional until migration completes. Historical dated notes and evidence are retained unchanged during this documentation PR. No claim about a live UI follows from this design. Where a case is not covered, implementation MUST report it as a design gap and amend this bundle and issue #24 before adding behavior; it MUST NOT select an undocumented fallback. Local variable names, module boundaries and equivalent algorithms are implementation choices only if every observable contract remains unchanged.
