---
type: project
title: Knowledge Hub
status: draft
project_id: knowledge-hub
tags: [knowledge-management, diary, okf]
visibility: private
sources:
  - resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
    title: OKF v0.2 specification
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/3
    title: Public GitHub Pages publishing
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/4
    title: Private-records authentication ADR
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/5
    title: Public diary records
---

# Knowledge Hub

A Git-backed home for projects, ideas and decisions. Initial entry: [kickoff record](../journal/2026/11/09/knowledge-hub-kickoff.md). Keep atomic OKF v0.2 dated records and a small day/week/month static diary, not a generated copy of a giant `log.md`.

## Implementation snapshot — 2026-11-09

- [PR #1](https://github.com/tempuku/knowledge-hub-starter/pull/1) merged the responsive early-iOS/iPad split-view, Safari 12 compatibility and Home Screen app groundwork.
- [PR #3](https://github.com/tempuku/knowledge-hub-starter/pull/3) merged GitHub Pages packaging for a real public-only read-only diary.
- [PR #4](https://github.com/tempuku/knowledge-hub-starter/pull/4) merged [ADR 0001](../adr/0001-private-records-authenticated-app.md): separate private records, authenticated access and Git-backed editing are **future architecture**, not implemented functionality.
- [PR #5](https://github.com/tempuku/knowledge-hub-starter/pull/5) merged publication of the **four existing, explicitly public** diary records. The [public diary publication run](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42664233918) and [OKF/diary validation run](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42664233843) both reported success on `main`.

**Expected public app:** https://tempuku.github.io/knowledge-hub-starter/ . The successful deployment is documented by GitHub Actions; verify current HTTP access and actual UI behavior in a browser. The app is public, read-only and unauthenticated. It **cannot** yet read/write private records through an authenticated API or sync browser edits into Git. Physical original iPad Air testing remains a separate check.

## How to check

1. Open the [public diary](https://tempuku.github.io/knowledge-hub-starter/) in a browser, select **2026-11-09**, switch Day/Week/Month, open the four published project-planning entries, and verify navigation/links. Also inspect the site at tablet width. A green CI badge alone is not evidence that a particular device can access the page.
2. Inspect [GitHub Actions runs](https://github.com/tempuku/knowledge-hub-starter/actions), especially the latest **Publish Knowledge Hub public diary** and **Validate OKF and diary** results on `main`. Review the completed deployment URL before claiming it is live.
3. From a local checkout of the current `main`:
   ```sh
   python3 -m pip install -r tools/diary/requirements.txt
   python3 tools/diary/build.py
   python3 tools/diary/test_build.py
   python3 tools/diary/build.py --output-dir dist-public --public-only
   python3 tools/diary/test_build.py --output-dir dist-public --public-only
   python3 tools/diary/test_publication.py dist-public
   ```
4. For browser/UI regression checks, install `tools/diary/requirements-ui.txt`, run `python3 -m playwright install chromium webkit`, then `python3 tools/diary/test_ui.py` and `DIARY_BROWSER=webkit python3 tools/diary/test_ui.py`. The [README](../../README.md) contains the full documented setup.
5. To check the future **private** functionality, verify separately that a private data repo exists, unauthenticated requests are denied, authenticated reading/editing creates a private Git commit and an actual original iPad Air can sign in. **None of those acceptance conditions is met by the current public diary.**

**Privacy:** `knowledge-hub-starter` is a public GitHub repository. Frontmatter `visibility: private` does not make its source files confidential; no new personal notes or credentials should be committed here. The hosted public diary exports only explicitly `visibility: public` records. The private-data migration described in ADR 0001 is pending.
