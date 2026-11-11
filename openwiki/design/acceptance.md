---
type: guide
title: Storage and UX acceptance contract
status: draft
---

# Storage and UX acceptance contract

This is a required future verification plan, not a record of passed implementation tests. Link evidence for every row from the implementation PR/issue. A design merge checks documentation only. Use real temporary Git repositories, real writer/MCP calls, generated artifacts and browser interactions; mocks alone do not establish completion.

## A-01: Storage and writing

| ID | Scenario | Required result |
|---|---|---|
| S1 | Create in depth-eight hierarchy, update twice same second | One current record, one log, sequences 1/2/3, one diary row each, distinct IDs, correct tie ordering |
| S2 | Read current after multiple edits | Current bytes equal final after; no log replay needed for content |
| S3 | Reuse title in different areas | Distinct IDs, unambiguous area labels, valid links |
| S4 | Malformed YAML/JSON, duplicate keys, bad timestamp/offset, hash, sequence, previous ID, before-chain or head mismatch | Validation fails; no branch change or deploy |
| S5 | Edit old log bytes and recompute hashes | Trusted-base prefix comparison rejects ordinary commit |
| S6 | Duplicate event/record IDs anywhere | Full validator rejects before generation |
| S7 | Missing sibling, orphan sibling, wrong log record ID/path | Integrity error; no silent repair |
| S8 | Same command retry after successful commit and lost response | Original IDs/receipt returned, no new commit/event |
| S9 | Same key with different content/actor/expected refs | IDEMPOTENCY_CONFLICT, no mutation |
| S10 | Two independent clones write same expected head | One CAS succeeds, other conflicts, no partial file/log update |
| S11 | Failure during staging, validation, commit, CAS or response | Branch remains atomic; uncertain post-CAS retry resolves same operation |
| S12 | Clock behind last event | CLOCK_SKEW; no backdating |
| S13 | Move with inbound/outbound relative links | Both files move, affected links/indexes fixed atomically, each affected record logs once, IDs persist |
| S14 | Move cannot update an unauthorized backlink | Entire move denied, no partial relocation |
| S15 | Archive/reopen and byte-identical update | Deprecated/current status rules enforced; no-op produces no diary change |
| S16 | Traversal, symlink component, reserved name, case collision, oversized input | Reject before write |
| S17 | CLI and MCP execute same operation sequence | Same domain semantics, no journal copies, real commit and readable diff |
| S18 | Direct Git record edit without matching appended event | Required CI rejects; no auto-reconciliation or publish |
| S19 | Create new directories | Indexes generated with exact child coverage and no logs indexed as concepts |
| S20 | Public checkout receives default-private create | Denied; frontmatter flag never treated as repository security |

## A-02: Projection, migration and publication

| ID | Scenario | Required result |
|---|---|---|
| P1 | Build twice from same source/exporter/policy | Identical deterministic content hashes |
| P2 | Build after removing .git from copied source | All native current/history/diff views still generated |
| P3 | 51 changes or 128-KiB page boundary | Correct page split, totals and Load more; no duplicate/missing event |
| P4 | Current record completed, earlier snapshot draft | Current page Completed; old revision and event row Draft |
| P5 | Private-before/public-after event | No public event, before body, diff, ID or count leakage |
| P6 | Public current record but unallowlisted history | Record readable; No published history |
| P7 | Revoke current public eligibility | Next generation omits record/history/reminders/aliases; no promise of historical erasure |
| P8 | Private actor/reference in otherwise public candidate | Policy redaction/reference checks and review prevent unauthorized payload; no count leakage |
| P9 | Malformed log or failed build | Last live manifest/generation remains intact |
| P10 | Legacy independent note + native creation + duplicate update journal | Reviewed migration retains unique content, projects one event per preserved logical event, aliases work |
| P11 | Repeat migration from same base/manifest/time | Identical source tree and output; no new UUIDs or timestamps |
| P12 | Migration source changed since dry run | CAS fails; inventory/dry run repeated |
| P13 | Legacy unknown/decreasing recording timestamps | Provenance retained and explicit normalization report; no invented occurrence date |
| P14 | Reminder range across month/year and offset timestamps | Correct written-date cells, inclusive endpoints, exact time/offset preserved |
| P15 | Publication audit scans every artifact byte and metadata | No known private IDs/paths/content; public and private output sets separately recorded |
| P16 | Performance fixture in P-05 | All stated budgets measured, three-run median and runner details recorded |

## A-03: UI/UX journeys

| ID | Given / action | Required visible behavior |
|---|---|---|
| U1 | Fresh launch with historical latest change | Diary/Week containing latest event, full range label UTC, all nonempty week days open |
| U2 | Click date from sidebar/Diary control | Day selected visually and accessibly, correct input and URL, correct rows |
| U3 | Share/refresh/Back/Forward a filtered route | Query, date, mode and selected record restored; Back restores scroll/focus where available |
| U4 | Open a current record | Rendered Markdown, working links, current status; Source is secondary |
| U5 | View old revision then Changes | Historical title/status, explicit past-revision label, exact diff, Open current record available |
| U6 | Creation and pure move diff | Clear nonexistent-before/content-unchanged explanations, no misleading empty error |
| U7 | Change count spans several pages | Total reflects all filtered changes and unique records; Load more doesn't change totals |
| U8 | Same record edited three times | Three visible changes, one distinct-record count, no duplicate bare diary note |
| U9 | Search exact token AND/filter/archived combination | P-03 ranking/filter semantics; no history hits; no-result state offers Clear filters |
| U10 | Type queries rapidly and reverse network response order | Latest query remains authoritative; old response cannot replace results |
| U11 | Calendar day with reminder but no changes | Reminder visible; View changes opens separate empty Diary state |
| U12 | Select month/date, cross-month range, completed reminder | Correct agenda/grid; completed record doesn't silently lose dates |
| U13 | Today empty or with archived records | Explicit empty sections; deprecated excluded; no fabricated tasks/overdue state |
| U14 | Load failure for one day/event/reminder | Local error + Retry; other content remains; retry doesn't duplicate |
| U15 | Public offline cached/uncached page | Saved-generation banner or Not saved; no silent stale “latest” claim |
| U16 | Private offline or unauthorized record | No cached private payload; Reconnect or generic Unavailable |
| U17 | New generation during open session | Update available; switch consistently on Refresh, preserve route |
| U18 | Old path reused, old link followed | Explicit eligible record choice, never wrong silent redirect |
| U19 | Keyboard + screen reader | All navigation/actions reachable, useful labels, focus restored, live errors announced once |
| U20 | 320/390/768/1024/1440px and 200% zoom | No page overflow; targets readable, actions wrap, no hover dependency |
| U21 | Malicious Markdown HTML/URL and external image | No script execution or automatic external image request |
| U22 | Large detail >256 KiB | Explicit Load full revision/content action; complete bytes only after consent to load, no truncation claim |
| U23 | Public source link and historical title | Heading is plain; File opens current source; revision action stays internal |
| U24 | Modern Chromium/WebKit pass | Report browser versions; physical iPad status remains separately unverified until tested |

## A-04: Implementation evidence and completion

For each implementation slice record commit SHA, test command/tool call, fixture revision, expected and observed result, artifact/report path and failure notes. Reports belong in OpenWiki, machine-readable fixtures stay with tooling. For live verification record deployment URL, manifest generation/source revision, timestamp, tested routes and browser/device. Test a created record, two updates on the same day, a move, historical status, reminder, search and reload against that exact generation. Check no inaccessible/private content is requested by the public browser.

The issue cannot close on a screenshot, passing schema check, skipped CI run or documentation merge. Completion requires all applicable S/P/U rows, a real MCP session writing to a disposable repository, migration reconciliation, full build performance evidence and deployed UI verification. Physical iPad acceptance may remain a separately tracked limitation, clearly named; do not claim that device verified from desktop WebKit.
