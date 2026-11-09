# Knowledge Hub — OKF v0.2

A private, Git-backed home for ideas, projects, decisions and a browsable diary. Uses Google's **Open Knowledge Format v0.2** (not OKF 2.0).

## What is in this starter

- `openwiki/`: source-of-truth OKF bundle, one concept/diary record per Markdown file.
- `openwiki/journal/YYYY/MM/DD/`: date-partitioned immutable records; optional scoped `log.md` remains small.
- `tools/diary/build.py`: static web exporter. It builds a tiny calendar, daily metadata JSON shards and one lazy-loadable JSON document per record. The browser never downloads or parses a giant `log.md`.
- `site/`: one shared browser application with day/week/month modes, styled in **early iOS 5–6** (glossy blue navigation, grouped lists, beveled segmented controls, subtle linen textures). The theme uses CSS only: a single-column iPhone layout under 720px and a split-view, classic early-iPad library/diary layout for tablets and desktop (sidebar dates synchronize with the diary).
- `.github/workflows/validate-openwiki.yml`, `.githooks/pre-commit`, `tools/okf/`: validation adapted from `tempuku/ivanovo_models`.

## Create the private repository

From the extracted directory, with GitHub CLI authenticated:

```sh
git init -b main
git add .
git commit -m 'Initialize OKF knowledge hub and diary'
gh repo create tempuku/knowledge-hub --private --source=. --remote=origin --push
```

**Safety:** the repository should start **private**. The generated private diary contains personal notes and must not be deployed to public GitHub Pages. A later opt-in public preview must use `--public-only` and an explicit publication review.

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
