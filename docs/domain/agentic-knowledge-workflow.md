# Agentic knowledge updates — domain model

Status: proposed, 2026-11-10.

## Purpose
Authorized humans and agents publish traceable knowledge updates. Every successful semantic change produces a concise diary entry, an inspectable full diff, and a permanent link to its original OKF record.

## Bounded contexts
- **Knowledge**: KnowledgeRecord aggregate (stable ID, source path, visibility, version, content, provenance). Owns validation and version transitions.
- **Change Journal**: ChangeEntry aggregate (event ID, summary, actor, source record ID, before/after refs, occurred_at, visibility). Owns chronological browsing and diff navigation.
- **Authorization & Publication**: Actor identity, scopes, public export policy. Private content must never enter public Pages artifacts.
- **Agent Gateway**: MCP/API command adapter, idempotency, permission checks, validation, audit trail. It does not bypass domain rules.

## Ubiquitous language
**Knowledge update**: a committed semantic change to an OKF record. **Change entry**: immutable journal representation of an update. **Original record**: canonical OKF file at a stable path/ID. **Diff**: exact before/after version comparison. **Actor**: authenticated human or agent identity. **Publication**: authorized projection of records to a reader.

## Commands and events
Commands: ProposeKnowledgeUpdate(record_id, expected_version, patch, summary, idempotency_key); CommitKnowledgeUpdate; ReadChangeDiff.
Events: KnowledgeRecordCreated, KnowledgeRecordUpdated, KnowledgeRecordDeleted; ChangeEntryRecorded.
Use optimistic concurrency and stable idempotency keys. Preserve actor identity and evidence references.

## Invariants
1. A successful semantic update has exactly one discoverable journal event per logical operation; retries do not duplicate it.
2. Journal event links resolve to the original record and exact before/after versions, even after rename or deletion.
3. A failed or rejected update is not presented as a committed change.
4. No public metadata, summary, record, or diff may reveal private content.
5. Agents use the same validation and authorization rules as humans; no direct-write bypass.
6. Git-direct changes must be reconciled into the journal, or rejected by CI until represented.
7. Multi-file logical operations yield one grouped diary entry with per-record diffs.
8. Journal integrity is validated by a working MCP/API end-to-end test, not merely a draft PR or mock.

## Workflow
Agent authenticates → fetches record and version → proposes patch with summary and source evidence → gateway authorizes → validates OKF and references → applies versioned update plus journal entry → commits atomically where possible → publishes appropriate projections → returns canonical record URL, journal URL, and diff URL.

Git repository updates and journal creation should be in one commit when possible. For distributed implementations, use a durable outbox and idempotent reconciliation with explicit pending status; never claim publication before confirmation.

## Open architectural choices
- Whether to enforce journaling at a Git pre-receive/CI gate or reconcile direct commits asynchronously.
- Private repository and authenticated hosting architecture per ADR 0001.
- MCP tool contract and stable canonical URL scheme.
