---
okf_version: "0.2"
---
# ADR: Append-only OKF record logs and day-by-day knowledge history

Status: Proposed (implementation in progress)
Date: 2026-11-10

## Context
The diary currently depends on separately authored journal pages and, for some changes, Git diffs. Users need to see what happened on any concrete day, including multiple updates to the same record. The browser must not parse thousands of Markdown files.

## Decision
Each managed record `openwiki/<area>/<name>.md` has a sibling `<name>.log.md`. Creating a record creates its log and appends a CREATED entry. Updating a record appends an UPDATED entry. The author (human or agent) supplies a meaningful summary and the writer stores complete before/after content as self-contained log entry data. A record and its log are written together by the trusted writer. Logs are authoritative; Git is transport and optional audit evidence, not the source of history.

Each entry has a unique ID, UTC ISO-8601 timestamp, actor, action, summary and complete snapshots. Multiple entries on the same day remain distinct. Existing journal records remain readable during migration. Operational CI logs are not knowledge diary events.

A build-time indexer projects log entries into per-day paginated JSON and per-entry detail JSON. The UI fetches only selected days and opens full entries lazily. It offers internal record navigation. Generated indexes can be rebuilt from OKF logs and are not authoritative. A full rebuild is the correctness baseline; incremental processing is a later optimization, not a prerequisite for correct daily browsing.

## Invariants
1. Create => record + log + CREATED entry; update => record + appended UPDATED entry.
2. An existing log entry cannot be rewritten by the supported writer.
3. A successful write publishes the record and log in one commit; no partial success is reported.
4. Each log entry has a stable unique ID and timestamp; the diary groups by timestamp date, not filename.
5. Snapshots are complete, including frontmatter; their SHA-256 hashes are validated.
6. An update's before snapshot equals the existing record content.
7. The diary exposes all dates, including several changes to one record on one day.
8. Public builds exclude nonpublic records and logs; visibility cannot be escalated by the indexer.
9. Existing journal pages remain compatible.
10. Generated read models are disposable and may be rebuilt from logs.

## Tradeoffs
Full snapshots consume more storage but keep the history portable without Git. Initial builds scan logs; browsers never do. Future hash-manifest indexing may reduce build work. Concurrent writers require serialization or optimistic revision checking.

## Acceptance
- Create, update twice on one date, build, and see three separate entries for that date.
- Expand an entry to read the full change content and open the canonical record within Knowledge Hub.
- Build without Git history; daily log entries remain readable.
- Reject malformed timestamps, duplicate entry IDs, modified history and mismatched snapshot hashes.
- Verify public-only builds never emit private log contents.
