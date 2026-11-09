# Knowledge Hub — OKF v0.2

A Git-backed home for ideas, projects, decisions and a browsable diary. The current first phase is a **public, read-only web diary**. Uses Google's **Open Knowledge Format v0.2** (not OKF 2.0).

## What is in this starter

- `openwiki/`: source-of-truth OKF bundle, one concept/diary record per Markdown file.
- `openwiki/journal/YYYY/MM/DD/`: date-partitioned immutable records; optional scoped `log.md` remains small.
- `tools/diary/build.py`: static web exporter. It builds a tiny calendar, daily metadata JSON shards and one lazy-loadable JSON document per record. The browser never downloads or parses a giant `log.md`.
- `site/`: one shared browser application with day/week/month modes, styled in **early iOS 5–6** (glossy blue navigation, grouped lists, beveled segmented controls, subtle linen textures). The theme uses CSS only: a single-column iPhone layout under 720px and a split-view, classic early-iPad library/diary layout for tablets and desktop (sidebar dates synchronize with the diary).
- `.github/workflows/validate-openwiki.yml`, `.githooks/pre-commit`, `tools/okf/`: validation adapted from `tempuku/ivanovo_models`.

## Live site and public reading — phase 1

**Open the real web app:** https://tempuku.github.io/knowledge-hub-starter/

The repository is public. Four existing project-planning journal records for 2026-11-09 are explicitly marked `visibility: public`, so they appear on the hosted Day/Week/Month diary without login. Each record remains an atomic OKF v0.2 Markdown source with links back to original evidence.

The GitHub Pages build **still uses `--public-only`**. Future records default to `visibility: private` in frontmatter and will not appear on the website until individually marked public. **Warning:** any files committed to this public repository, even those labeled `private`, remain readable via GitHub and its history. Do not commit new private thoughts here.

This is an interim, unrestricted read-only release, **not** the secure final architecture. The accepted [ADR 0001](openwiki/adr/0001-private-records-authenticated-app.md) specifies a separate private data repository and authenticated reading/editing as a subsequent stage.

## Visual direction

Preserve the classic **early iOS 5–6** app aesthetic in any future views (Projects, Search, Timeline): glossy navigation bars, inset grouped lists, readable Helvetica-style typography, restrained skeuomorphic textures, and thumb-friendly controls. The viewer must remain responsive and accessible. Do not create a separate HTML app per project; all sections share one style system and data loader.

## Local diary

Python 3.10+ and PyYAML are required:

```sh
python3 -m pip install -r tools/diary/requirements.txt
python3 tools/diary/build.py
python3 -m http.server 8000 --directory dist
```

Open `http://localhost:8000/`. The browser uses a local HTTP server because fetching JSON from `file://` is unreliable or blocked.

## Validation (same checker as ivanovo_models)

`ivanovo_models` has `.github/workflows/validate-openwiki.yml` → `.githooks/pre-commit` → `tools/okf/verify.mjs`, with a pinned upstream `frontmatter.ts`. This starter copies that verification approach and adds a diary-build smoke test.

```sh
sh tools/okf/setup.sh   # requires Node 22.18+, npm, curl, network on first setup
git config --local core.hooksPath .githooks
git add .
sh .githooks/pre-commit
```

The pinned upstream OKF validator is downloaded by setup rather than vendored. Its Git hash is verified by the setup script.

## iPad Air (1st generation) Home Screen app

The original iPad Air is limited to **iOS 12** (latest legacy security update: iOS 12.5.8). This is a real **installable web app** rather than a modern Swift/App Store package: one iPad-friendly split-view UI, old-Safari-compatible JavaScript, Apple Home Screen metadata, generated PNG icon, and a service worker for best-effort offline access.

**Install:** Open the **HTTPS hosted site** in Safari on the iPad, tap Share, then **Add to Home Screen**. The tablet will launch Knowledge Hub without the ordinary Safari browser chrome. The service worker caches the application and previously visited diary entries for offline access when Safari allows it; storage can be evicted by iOS and must not be used as the only copy.

**Privacy:** The git repository and OKF files are the source of truth; the iPad app is a **read-only diary browser**. It does not provide editing or syncing from the device. Private diary data must not be exposed through publicly reachable GitHub Pages. Public exports must continue to use `--public-only`, which intentionally shows no entries if all notes are private.

**Hosting:** The public GitHub Pages deployment is available at https://tempuku.github.io/knowledge-hub-starter/ . This is an actual HTTPS web app, but opening it successfully on the original physical iPad Air still requires a device-level check.

## HTTPS hosting (public-approved diary entries only)

The repository includes `.github/workflows/deploy-pages.yml`, which packages the **actual Knowledge Hub app** and only OKF journal records explicitly marked `visibility: public`. A strict allowlist verifies the published static HTML/JS/CSS, generated icons and date-partitioned JSON. This is not a mock or screenshot; it is the same read-only PWA that runs locally, but with private records excluded.

**Hosting status:** GitHub Pages is enabled and the deployment runs automatically for changes to journal records and site code on `main`. The public website serves the approved records without authentication. The app source remains public, but private data storage is still future work.

**Private diary requirement:** Publishing private notes behind login needs authenticated hosting (e.g. access-controlled hosting or a private app service), not a normal public GitHub Pages site. This workflow does not solve authenticated access or provide write/edit synchronization from the iPad. If no records have `visibility: public`, the public website will show an empty diary rather than exporting records marked private.

For any deployment failure check the GitHub Actions run and Pages settings. No credentials are stored in the repository: Pages deployment uses GitHub's scoped `GITHUB_TOKEN` and OIDC permissions. The shared URL becomes the acceptance proof only after a successful real deployment and device-level test.

## Responsive browser tests

The repository keeps **real headless Chromium checks** alongside the UI source in `tools/diary/test_ui.py`. They test the iPhone single-column layout, early-iPad split views at tablet and desktop widths, horizontal overflow, sidebar/date selection, Day/Week/Month switching, and opening lazy-loaded records. GitHub Actions runs these tests for every PR and `main` push.

To run locally (requires the one-time Chromium browser download):

```sh
python3 -m pip install -r tools/diary/requirements.txt -r tools/diary/requirements-ui.txt
python3 -m playwright install chromium
python3 tools/diary/build.py
python3 tools/diary/test_ui.py
```

The tests serve the generated `dist/` folder on localhost and never publish private entries. CI additionally runs `node --check site/app.js` and tests the separate `--public-only` export.

## Add a dated record

Create `openwiki/journal/2026/11/09/my-note.md` using the same frontmatter shape as the examples. Register it in that day's `index.md`, commit, and rebuild. `occurred_on` is a user-defined local calendar date (YYYY-MM-DD); it is distinct from `generated.at`, commits, or the date a note was last edited.

Use a new file for a new decision or event, not another paragraph in a global journal log. Git history records edits and who changed them; it is not the only source of diary events.

## Preview scale

`dist/data/calendar.json` contains only dates and counts. `dist/data/days/YYYY-MM-DD.json` contains only count/pagination metadata; `dist/data/days/YYYY-MM-DD/N.json` contains up to 50 title/summary items; `dist/data/entries/<record-id>.json` is fetched **only on opening the record**. Day/week/month views fetch data for the selected dates. For exceptionally busy dates, pagination can be added without changing OKF source structure.

## Source references

- [Official OKF v0.2 spec](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)
- [Source project](https://github.com/tempuku/ivanovo_models)
