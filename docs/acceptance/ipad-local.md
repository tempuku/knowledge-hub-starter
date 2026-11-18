# Local browser and physical iPad acceptance

**Policy:** Optional, on-demand local acceptance, **not a required GitHub Actions merge check**. Source validation, deterministic projections, and public-only privacy/audit checks remain required CI. This policy does not waive UX acceptance or authorize calling an untested device supported.

## Local browser checks (developer workstation)

Run in a Python virtual environment after a one-time install:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r tools/diary/requirements.txt -r tools/diary/requirements-ui.txt
python -m playwright install chromium webkit
sh tools/diary/run_local_ui_checks.sh
```

The script builds `dist/`, performs static iOS 12 syntax/PWA metadata checks, then runs the responsive browser suite in both **Chromium and modern WebKit**. It uses a localhost HTTP server; do not publish private fixtures. Reuse the virtual environment and downloaded browsers for later runs. If a browser is unavailable on the local OS, record the skip and reason; do not report a pass.

## Physical original iPad Air (Safari 12) — manual, local/device only

This cannot be substituted by desktop WebKit or a simulated tablet viewport. With an authorized, actually deployed HTTPS URL, verify and record:

- [ ] Safari opens the real application in portrait (768×1024) and landscape (1024×768), with readable layout and no horizontal overflow.
- [ ] Diary Day/Week/Month navigation, record opening, source links, Back/Forward and reload work.
- [ ] Add to Home Screen creates a usable standalone app; reopen it and navigate again.
- [ ] Previously visited permitted public content is usable during an offline check (within iOS best-effort caching limits); private content is **not** cached publicly.
- [ ] Public/private authorization and anonymous-denial checks are performed against the actual target environment.
- [ ] Log the deployment URL, exact commit/generation, device/iOS version, date, observed results and failures in issue [#2](https://github.com/tempuku/knowledge-hub-starter/issues/2).

**Evidence rule:** Leaving these tests out of required CI speeds up merging but does not convert pending UX/iPad acceptance into passed validation. Device signoff remains explicitly open until actual hardware observations are recorded. Privacy/publication CI must remain enforced.
