# UC-DAILY-001 — Persistent cross-repository morning stand-up (proposed)

**Status:** design amendment; not deployed or enabled. Tracking: [#72](https://github.com/tempuku/knowledge-hub-starter/issues/72), under [#24](https://github.com/tempuku/knowledge-hub-starter/issues/24). Read with the canonical [record contract](../../openwiki/design/records-and-writes.md), [projection contract](../../openwiki/design/projections.md), [UI contract](../../openwiki/design/ui-ux.md), and [privacy ADR](../../openwiki/adr/0001-private-records-authenticated-app.md). Their current conflicting status/schema requirements remain authoritative until a reviewed amendment updates them; this document identifies the change, not a silent new implementation rule.

## Goal and actors

**Actor:** authorized owner or trusted agent. **Trigger:** owner asks for the morning stand-up or explicitly scheduled authorized automation runs. **Outcome:** an accurate, evidence-linked overview of *all still-active* personal and project records, regardless of their latest modification time. The diary is a history of changes, not the list of open work.

## Source-of-truth boundaries

1. Production OKF data lives in a genuinely **private** source repository. The public app repository holds code and non-sensitive design, not production private records or confidential project snapshots. A frontmatter visibility label never prevents GitHub source exposure.
2. Within the private repository use subject folders `openwiki/private/` and `openwiki/projects/` (with optional subfolders). Every actual record has one sibling append-only log and stable ID; structural `index.md` pages are not records. No date-folder copies or manually authored stand-up duplicates.
3. Project records reference authoritative external repositories, specific issues/PRs, acceptance criteria and other canonical OKF records. External links are evidence, not replacement identity. Support **multiple repositories**, not just the Knowledge Hub app. Initial inventory: Knowledge Hub, Ivanovo Models, Personal Finance. Other active projects must be addable without code edits.
4. Sensitive document attachments must be stored behind independently verified access controls. Until an authenticated attachment model exists, a record may only contain a protected reference. Never embed private files/URLs in public generated content.
5. Any private-project or private-life item must be excluded from public builds, public logs, previews, CI artifacts, indexes, counts and caches. Authorized private projections can combine both areas.

## Lifecycle invariants

A record explicitly marked `in_progress` remains active for days, months or years, until a deliberate authorized status change. An activity timer does not remove it. Project status belongs to the parent record and is not inferred from a PR merge or child record's completion. For Ivanovo, a finished building variant is a finished workstream, **not** automatic completion of the entire modeling project.

The existing single `status` field currently permits `draft`, `stable`, `completed`, `deprecated`. Adding `in_progress` requires an explicit schema/validation/migration amendment: define record-type eligibility, valid transitions, how existing draft project records are mapped (manual review, no speculative auto-migration), and how old snapshots remain readable. Do not add an overlapping `project_status` field.

Use separate derived *read-model attributes* for activity and attention, not a second status:
- `last_activity_at` is the latest **verified** relevant source event or record-log timestamp. Do not mistake a fetch time for an event time.
- `days_inactive` is calculated relative to the stand-up date, preserving timezone provenance.
- `needs_attention` is a computed display hint (e.g., unchanged since an explicit configurable age threshold), never a deletion or completion rule.
- `source_checked_at` and `source_freshness` distinguish current verified evidence from an older cached snapshot and an unavailable external source.

Do not assert a project is blocked, completed, or accepted merely because GitHub has no recent events.

## Use case flow

1. Authenticate and authorize reading both `private` and `projects` areas. Reject unauthorized readers before counting or projecting private records.
2. Load the canonical current snapshot and log head of all authorized active records, paginated without filtering by activity date. Deduplicate by immutable record ID, not file path or repository alias.
3. Fetch/correlate authoritative project sources when available and authorized. Check open issues/PRs, recent merged work, acceptance checklists and CI *within their actual scope*. Unavailable sources remain visible with **stale/unavailable** evidence indicators.
4. Group into Personal and Projects with a single **In progress** lens across both, and a visible section for active items without recent events.
5. Display per project: title; explicit status; last verified change time; linked source records/issues/PRs; achieved since previous stand-up if a previous snapshot exists; incomplete acceptance; blockers/waiting evidence; and actionable next step. Label unverified assumptions.
6. Generate no new authored diary entry merely because someone opened the stand-up. Only a real persisted semantic update through the atomic writer creates a record event/log/diary projection.
7. Allow an authorized agent to propose/write updates via the canonical writer, with idempotency, validation and coherent source provenance. Reading alone never modifies lifecycle state.

## UI

- Main Today view and Projects/Records catalog offer an explicit **In progress** lens that shows both source areas for authorized readers, with persistent items even if not mentioned in yesterday's diary.
- Display unmodified older items under **Still in progress — no recent activity** rather than hiding them. Allow sort by age, last activity, source area and next action without changing canonical status.
- A `#/today?view=standup` route is proposed for design review; implement it only after amending the canonical U-01 route table. Include labels for insufficient evidence and private-source failures.
- The public demo must not leak existence, counts or identifiers for private items.

## Dependencies and acceptance

1. Complete the private-repository and authenticated reader boundary from ADR 0001; no health or confidential project data can be written until proven private.
2. Amend S-01/S-02, P-01/P-03, U-01/U-05/U-06 and migration/acceptance documents before executable implementation. Explicitly resolve previous single-status semantics.
3. Build and verify projections and browser UI for hundreds/thousands of records, using staged immutable generations. No independent stand-up store.
4. Exercise the [Gherkin scenarios](../../features/daily-standup.feature): persistent old work; independent parent and child; multi-repo aggregation; source outage; private/public access; idempotent write and no write on read.
5. Validate current actual project state from external repos and update canonical project records with logged, dated evidence. Old manual snapshots are **not live state**.

**Personal information note:** This public design deliberately contains no personal medical timeline, clinical documents or other private record content. Such material belongs only in private production data after the boundary is verified.
