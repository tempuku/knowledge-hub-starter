# OKF Record Change Log

## Entry git-727f862f2664ec06
```json
{
  "id": "git-727f862f2664ec06",
  "timestamp": "2026-11-09T15:26:09Z",
  "actor": "tempuku",
  "action": "CREATED",
  "summary": "Initial import",
  "record": "openwiki/GUIDE.md",
  "visibility": "private",
  "before": null,
  "after": "---\ntype: guide\ntitle: Knowledge hub conventions\nstatus: draft\ntags: [knowledge-management, okf, journal]\n---\n\n# Knowledge hub conventions\n\nThis is an OKF v0.2 bundle. Each note/idea/decision is its own Markdown concept with YAML frontmatter and references to authoritative evidence. A `project` field links a diary record to a project concept; `occurred_on` is the local calendar date and determines day/week/month browsing; `visibility: private` is the default.\n\n`log.md` is optional per-directory summary history, **not** the database for the web UI. The web build reads atomic concepts, emits small date-sharded metadata JSON files, and lazy-loads content. Git tracks changes but does not substitute for event dates.\n\nKeep relative concept links valid. Cite external GitHub issues by URL. Do not claim that a plan is implemented just because an issue exists. Use `status: draft` for unreviewed records.\n\nFor a new diary date, create `journal/YYYY/MM/DD/index.md` and one or more concept documents, then update year/month indexes as required. Do not create one global ever-growing timeline file.\n\n## Web presentation style\n\nThe diary's shared web interface follows an **early iOS 5–6** application design: glossy navigation bars, subtly textured linen backgrounds, inset grouped journal rows, blue beveled controls and compact mobile spacing. Maintain a responsive, accessible version of this visual language for future Projects, Search and Timeline views. All pages use one shared CSS/JS application; no project-specific HTML duplication.\n",
  "before_sha256": null,
  "after_sha256": "ff666e3ebb4cc441388cdeb3a4417c6af842c29604b8eceb9c2b4f6928706995",
  "source_commit": "727f862f2664ec068c172a05ccd35c350a47acc3",
  "provenance": "git-backfill"
}
```

## Entry git-0f91054a8ecb6685
```json
{
  "id": "git-0f91054a8ecb6685",
  "timestamp": "2026-11-09T17:11:58Z",
  "actor": "tempuku",
  "action": "UPDATED",
  "summary": "Link accepted security ADR from OKF catalog and working guidance",
  "record": "openwiki/GUIDE.md",
  "visibility": "private",
  "before": "---\ntype: guide\ntitle: Knowledge hub conventions\nstatus: draft\ntags: [knowledge-management, okf, journal]\n---\n\n# Knowledge hub conventions\n\nThis is an OKF v0.2 bundle. Each note/idea/decision is its own Markdown concept with YAML frontmatter and references to authoritative evidence. A `project` field links a diary record to a project concept; `occurred_on` is the local calendar date and determines day/week/month browsing; `visibility: private` is the default.\n\n`log.md` is optional per-directory summary history, **not** the database for the web UI. The web build reads atomic concepts, emits small date-sharded metadata JSON files, and lazy-loads content. Git tracks changes but does not substitute for event dates.\n\nKeep relative concept links valid. Cite external GitHub issues by URL. Do not claim that a plan is implemented just because an issue exists. Use `status: draft` for unreviewed records.\n\nFor a new diary date, create `journal/YYYY/MM/DD/index.md` and one or more concept documents, then update year/month indexes as required. Do not create one global ever-growing timeline file.\n\n## Web presentation style\n\nThe diary's shared web interface follows an **early iOS 5–6** application design: glossy navigation bars, subtly textured linen backgrounds, inset grouped journal rows, blue beveled controls and compact mobile spacing. Maintain a responsive, accessible version of this visual language for future Projects, Search and Timeline views. All pages use one shared CSS/JS application; no project-specific HTML duplication.\n",
  "after": "---\ntype: guide\ntitle: Knowledge hub conventions\nstatus: draft\ntags: [knowledge-management, okf, journal]\n---\n\n# Knowledge hub conventions\n\nThis is an OKF v0.2 bundle. Each note/idea/decision is its own Markdown concept with YAML frontmatter and references to authoritative evidence. A `project` field links a diary record to a project concept; `occurred_on` is the local calendar date and determines day/week/month browsing; `visibility: private` is the default.\n\n`log.md` is optional per-directory summary history, **not** the database for the web UI. The web build reads atomic concepts, emits small date-sharded metadata JSON files, and lazy-loads content. Git tracks changes but does not substitute for event dates.\n\nKeep relative concept links valid. Cite external GitHub issues by URL. Do not claim that a plan is implemented just because an issue exists. Use `status: draft` for unreviewed records.\n\nFor a new diary date, create `journal/YYYY/MM/DD/index.md` and one or more concept documents, then update year/month indexes as required. Do not create one global ever-growing timeline file.\n\n## Web presentation style\n\nThe diary's shared web interface follows an **early iOS 5–6** application design: glossy navigation bars, subtly textured linen backgrounds, inset grouped journal rows, blue beveled controls and compact mobile spacing. Maintain a responsive, accessible version of this visual language for future Projects, Search and Timeline views. All pages use one shared CSS/JS application; no project-specific HTML duplication.\n\n## Architecture decisions\n\nRead and maintain [architecture decision records](adr/) before changing how knowledge is stored, authenticated, published or edited. The accepted target architecture is [ADR 0001: public app, private records and authenticated access](adr/0001-private-records-authenticated-app.md). Its implementation is pending; do not confuse frontmatter `visibility: private` with access control when records live in a public repository.\n",
  "before_sha256": "ff666e3ebb4cc441388cdeb3a4417c6af842c29604b8eceb9c2b4f6928706995",
  "after_sha256": "42fc2dbf9d268b0b23033261d5e3e44ce3959d8af313c8f4f2210d35edd05e53",
  "source_commit": "0f91054a8ecb668559311520aec9ba7a56a1fcdd",
  "provenance": "git-backfill"
}
```

## Entry git-2ef2bcf51641c7b3
```json
{
  "id": "git-2ef2bcf51641c7b3",
  "timestamp": "2026-11-09T17:23:58Z",
  "actor": "tempuku",
  "action": "UPDATED",
  "summary": "Publish approved OKF project notes through live diary",
  "record": "openwiki/GUIDE.md",
  "visibility": "private",
  "before": "---\ntype: guide\ntitle: Knowledge hub conventions\nstatus: draft\ntags: [knowledge-management, okf, journal]\n---\n\n# Knowledge hub conventions\n\nThis is an OKF v0.2 bundle. Each note/idea/decision is its own Markdown concept with YAML frontmatter and references to authoritative evidence. A `project` field links a diary record to a project concept; `occurred_on` is the local calendar date and determines day/week/month browsing; `visibility: private` is the default.\n\n`log.md` is optional per-directory summary history, **not** the database for the web UI. The web build reads atomic concepts, emits small date-sharded metadata JSON files, and lazy-loads content. Git tracks changes but does not substitute for event dates.\n\nKeep relative concept links valid. Cite external GitHub issues by URL. Do not claim that a plan is implemented just because an issue exists. Use `status: draft` for unreviewed records.\n\nFor a new diary date, create `journal/YYYY/MM/DD/index.md` and one or more concept documents, then update year/month indexes as required. Do not create one global ever-growing timeline file.\n\n## Web presentation style\n\nThe diary's shared web interface follows an **early iOS 5–6** application design: glossy navigation bars, subtly textured linen backgrounds, inset grouped journal rows, blue beveled controls and compact mobile spacing. Maintain a responsive, accessible version of this visual language for future Projects, Search and Timeline views. All pages use one shared CSS/JS application; no project-specific HTML duplication.\n\n## Architecture decisions\n\nRead and maintain [architecture decision records](adr/) before changing how knowledge is stored, authenticated, published or edited. The accepted target architecture is [ADR 0001: public app, private records and authenticated access](adr/0001-private-records-authenticated-app.md). Its implementation is pending; do not confuse frontmatter `visibility: private` with access control when records live in a public repository.\n",
  "after": "---\ntype: guide\ntitle: Knowledge hub conventions\nstatus: draft\ntags: [knowledge-management, okf, journal]\n---\n\n# Knowledge hub conventions\n\nThis is an OKF v0.2 bundle. Each note/idea/decision is its own Markdown concept with YAML frontmatter and references to authoritative evidence. A `project` field links a diary record to a project concept; `occurred_on` is the local calendar date and determines day/week/month browsing; `visibility: private` is the default.\n\n`log.md` is optional per-directory summary history, **not** the database for the web UI. The web build reads atomic concepts, emits small date-sharded metadata JSON files, and lazy-loads content. Git tracks changes but does not substitute for event dates.\n\nKeep relative concept links valid. Cite external GitHub issues by URL. Do not claim that a plan is implemented just because an issue exists. Use `status: draft` for unreviewed records.\n\nFor a new diary date, create `journal/YYYY/MM/DD/index.md` and one or more concept documents, then update year/month indexes as required. Do not create one global ever-growing timeline file.\n\n## Web presentation style\n\nThe diary's shared web interface follows an **early iOS 5–6** application design: glossy navigation bars, subtly textured linen backgrounds, inset grouped journal rows, blue beveled controls and compact mobile spacing. Maintain a responsive, accessible version of this visual language for future Projects, Search and Timeline views. All pages use one shared CSS/JS application; no project-specific HTML duplication.\n\n## Architecture decisions\n\nRead and maintain [architecture decision records](adr/) before changing how knowledge is stored, authenticated, published or edited. The accepted target architecture is [ADR 0001: public app, private records and authenticated access](adr/0001-private-records-authenticated-app.md). Its implementation is pending; do not confuse frontmatter `visibility: private` with access control when records live in a public repository.\n\n## Phase 1: public read-only web diary\n\nThe initial four **project-planning** diary records dated 2026-11-09 are approved for public reading and marked `visibility: public`. They are available through the [hosted day/week/month diary](https://tempuku.github.io/knowledge-hub-starter/) without login. The public deployment still uses `--public-only`; future records are not automatically published. A frontmatter `visibility: private` flag does **not** protect files stored in this public Git repository. Do not add sensitive or personal notes to this repository while private storage and authenticated editing from [ADR 0001](adr/0001-private-records-authenticated-app.md) remain unimplemented.\n",
  "before_sha256": "42fc2dbf9d268b0b23033261d5e3e44ce3959d8af313c8f4f2210d35edd05e53",
  "after_sha256": "ed483ddfa1fca1c95f98c947ec4f2412686ca97eeaa8acff154fe25d53efe518",
  "source_commit": "2ef2bcf51641c7b3b10de60fee6f9a1db20790a8",
  "provenance": "git-backfill"
}
```
