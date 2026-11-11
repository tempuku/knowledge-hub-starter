---
type: guide
title: Knowledge hub conventions
status: draft
tags: [knowledge-management, okf, journal]
---

# Knowledge hub conventions

Start with the [implementation design](design/overview.md). The owner selected hierarchical records plus per-record history, and requested a complete UI/UX design. Merging that documentation establishes the target contract; the current application remains transitional until its implementation and migration checks pass.

## Target authoring model

Keep each knowledge item once, under its subject area with optional deeper hierarchy. Keep a sibling append-only `.log.md`. The current record and its log form one atomic aggregate. Stable IDs survive renaming and moving. The diary is generated from log events; do not design a second authored diary copy or required year/month/day source directory. Generated date indexes are still required for efficient browsing.

The exact fields, enum values, limits, paths, reminder tuples, concurrency and retry behavior are in [Records and writes](design/records-and-writes.md). Generated indexes, publication and performance are in [Projections](design/projections.md). Do not invent extra status fields, timestamp semantics or fallback writers. The single status field is draft/stable/completed/deprecated; completed means finished and deprecated is the archived presentation.

Every new concept belongs in its directory index. Each new directory has an index and parent entry. Structural indexes have no record logs or diary rows. Keep evidence references and valid relative links until migration converts appropriate links to stable IDs. Do not claim plans are implemented because an issue or design exists.

## Current implementation boundary

At audited revision `e68270c`, the builder accepts both dated journal notes and sibling native logs. The app is public/read-only. The local MCP adapter imports the legacy journal writer; it does not yet implement the target shared writer. Existing files in `journal/YYYY/MM/DD/` and existing logs must be preserved until the [reviewed migration](design/migration.md). Do not move records ad hoc or claim the new schema is supported by current tools.

The current diary opens the week containing its latest entry, loads daily pages and opens full bodies lazily. Its heading is plain text; a separate File link opens the current canonical GitHub file; Open shows a stored revision and Show diff shows changes. Earlier instructions saying the heading itself opens a record are obsolete. The current raw-Markdown viewer is not the target readable record page.

## UI/UX contract

Preserve early iOS 5–6 CSS styling and one shared responsive app. Target primary navigation is Today, Projects, Records, Diary, Calendar; Search is in Records. The [UI/UX specification](design/ui-ux.md) fixes routes, labels, filters, count semantics, record/history/diff actions, calendar behavior, breakpoints, keyboard/focus handling and loading/error/offline states. The diary displays changes, not an ambiguous count of notes plus revisions. It clearly separates current content from historical snapshots. Source files remain a secondary explicit link, as requested by the owner.

Important dates remain `[date-or-range, text]` tuples, not push notifications. The target preserves timestamp offsets and links every calendar item to its current record. The existing exporter currently reduces timestamps to dates; this is an implementation gap, not the target rule.

## Privacy and architecture

Read [ADR 0001](adr/0001-private-records-authenticated-app.md) for private repository and authenticated hosting requirements; that rollout remains pending. A visibility flag cannot secure source files in a public repository. No private personal material belongs here. Public exports require explicit approval and target snapshot-level rules in the design; do not infer historical publication consent from a current visibility flag.

## Feature workflow

Before implementing a feature, create an issue with user problem, behavior, non-goals and checklist. Resolve UI, schemas, privacy, edge cases and acceptance in its design. The owner authorized merging the documentation for [issue #24](https://github.com/tempuku/knowledge-hub-starter/issues/24); link the merged revision there as the implementation baseline. New deviations require an explicit amendment before code. Implement through reviewable PRs, validate representative data and the deployed UI, and retain unchecked acceptance items until verified. A passing build is not a working deployment.

History is for inspection; [diff issue #21](https://github.com/tempuku/knowledge-hub-starter/issues/21) excludes restoration. Do not add restore/rollback controls. Before every commit, stage intended changes and run `sh .githooks/pre-commit`; fix and restage errors. Implementation requires the additional source/event validators specified in the design, not only today's OKF checker.
