---
type: guide
title: Knowledge hub conventions
status: draft
tags: [knowledge-management, okf, journal]
---

# Knowledge hub conventions

This is an OKF v0.2 bundle. Each note/idea/decision is its own Markdown concept with YAML frontmatter and references to authoritative evidence. A `project` field links a diary record to a project concept; `occurred_on` is the local calendar date and determines day/week/month browsing; `visibility: private` is the default.

`log.md` is optional per-directory summary history, **not** the database for the web UI. The web build reads atomic concepts, emits small date-sharded metadata JSON files, and lazy-loads content. Git tracks changes but does not substitute for event dates.

Keep relative concept links valid. Cite external GitHub issues by URL. Do not claim that a plan is implemented just because an issue exists. Use `status: draft` for unreviewed records.

For a new diary date, create `journal/YYYY/MM/DD/index.md` and one or more concept documents, then update year/month indexes as required. Do not create one global ever-growing timeline file.

For a record update, write a short sentence in the log's `summary` field describing what changed in the record. Write it for someone reading the diary. Avoid copying the Git commit message. The diary labels older Git imports by their record title and action.

## Web presentation style

The diary's shared web interface follows an **early iOS 5–6** application design: glossy navigation bars, subtly textured linen backgrounds, inset grouped journal rows, blue beveled controls and compact mobile spacing. Maintain a responsive, accessible version of this visual language for future Projects, Search and Timeline views. All pages use one shared CSS/JS application; no project-specific HTML duplication.

The diary opens to the Monday–Sunday week containing the latest available entry. Each day in that week opens automatically with its first page of titles. The total covers the selected date range, including additional pages. Selecting a sidebar date switches to Day view. Month view opens the newest day and loads other dates when expanded. Full entry bodies load when opened.

Dates and timestamped entries are ordered newest first. Date-only entries follow the timed entries for that day. Use `occurred_at` with a verified UTC timestamp ending in `Z` when the event time is known and its UTC date matches `occurred_on`. On a history entry, choose **Show diff** for the changed lines or **Open** for the full record at that revision.

## Architecture decisions

Read and maintain [architecture decision records](adr/) before changing how knowledge is stored, authenticated, published or edited. The accepted target architecture is [ADR 0001: public app, private records and authenticated access](adr/0001-private-records-authenticated-app.md). Its implementation is pending; do not confuse frontmatter `visibility: private` with access control when records live in a public repository.

## Phase 1: public read-only web diary

The initial four **project-planning** diary records dated 2026-11-09 are approved for public reading and marked `visibility: public`. They are available through the [hosted day/week/month diary](https://tempuku.github.io/knowledge-hub-starter/) without login. The public deployment still uses `--public-only`; future records are not automatically published. A frontmatter `visibility: private` flag does **not** protect files stored in this public Git repository. Do not add sensitive or personal notes to this repository while private storage and authenticated editing from [ADR 0001](adr/0001-private-records-authenticated-app.md) remain unimplemented.
