# UC-AGENT-001: Agent publishes a knowledge update

**Primary actor:** authorized AI agent. **Goal:** safely change an OKF record with a short diary entry and exact diff.

**Preconditions:** actor authenticated with scoped write permission; record ID and expected version known; destination privacy policy known.

**Main flow**
1. Agent reads canonical record, current version, provenance and allowed scopes.
2. Agent proposes a patch, short human-readable summary, evidence links and idempotency key.
3. Gateway checks authorization, expected version, OKF schema, evidence and visibility.
4. Domain service persists the change and associated journal event as one logical operation.
5. Service returns stable source-record URL, journal-entry URL, before/after version IDs and diff URL.
6. Reader sees short diary summary; full diff is loaded on click, and original source is navigable.

**Alternatives:** invalid OKF → reject without successful diary entry; stale version → conflict with current version; repeated idempotency key → return existing result; missing permission → deny and avoid leaking private existence; journal failure → fail the logical operation or keep it pending and block success until reconciliation; deletion → link to last version/tombstone.

**Postconditions:** one traceable logical change, no duplicate entries, no private data in public export.

**Acceptance:** executable Gherkin scenarios in `features/agent-knowledge-updates.feature`; working MCP/API integration against a temporary repository with real commits and diff resolution.
