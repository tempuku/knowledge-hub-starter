---
type: decision
title: Hierarchical records with per-record logs and a projected diary
visibility: public
status: draft
---
# ADR: Hierarchical records, per-record logs and a projected diary

Decision status: owner-selected direction; this merged documentation establishes the implementation baseline. Implementation and migration remain pending. Tracking: [issue #24](https://github.com/tempuku/knowledge-hub-starter/issues/24).

## Context
The application currently combines date-folder notes and native sibling logs. The MCP adapter still invokes the older journal writer. Keeping both authoring paths permits missing or duplicated activity and makes record discovery depend on dates. The owner requested one record in its subject hierarchy and per-record logs projected into the diary, with a complete UI/UX contract.

## Decision
One canonical Markdown record under a nested subject area and one sibling append-only log form a single aggregate. Current content equals the final log snapshot. Stable IDs survive moves. No new independently authored diary copies or required source date directories remain after migration. Structural indexes are not knowledge events. Generated date shards remain useful and disposable.

All human/CLI/MCP writes use one validated atomic transaction with optimistic branch concurrency and durable idempotency. Direct unlogged edits fail required validation. Full snapshots are retained; no history restore or hard delete is introduced. The diary shows recorded changes in UTC; factual occurrence dates remain separate metadata. Current record, historical revision and diff have distinct UI routes/actions. The single status field retains draft/stable/completed/deprecated.

## Normative implementation specification
The [design baseline](../design/overview.md), [source/write contract](../design/records-and-writes.md), [read models and publication](../design/projections.md), [UI/UX contract](../design/ui-ux.md), [migration plan](../design/migration.md) and [acceptance matrix](../design/acceptance.md) define the exact observable behavior. They replace the earlier open alternatives in this ADR and the older domain/use-case notes. Unspecified product behavior requires an explicit design amendment; implementers may not infer a second authoring model or silent reconciliation.

## Consequences
Full snapshots consume space proportional to edits and record size; v1 measures this and keeps full rebuilds as the correctness baseline. Browser reads stay paginated and lazy. Search and subject navigation operate on generated current-record indexes. Atomic moves may update several records' relative links in one transaction; each changed record gets its own event. Visibility is not repository access control: ADR 0001 remains authoritative for private hosting, and public historical snapshots require explicit eligibility and review.

## Supersession and rollout
The previous proposed history ADR allowed legacy journal coexistence and left concurrency open. Coexistence is now migration-only, with a native-only cutover. Date-folder source storage from ADR 0001 section 6 is superseded by this design; its security requirements are unchanged. Existing history is preserved through the reviewed migration, not moved in this documentation change.

## Acceptance
All S/P/U scenarios in the acceptance matrix are implementation requirements, not passed checks. Completion requires real writer/MCP transactions, migration reconciliation, public-export audit, measured performance and live UI verification. A merged design does not complete issue #24.
