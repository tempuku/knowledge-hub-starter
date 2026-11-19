# Direct UI review and physical iPad acceptance

**Policy (owner simplification, 2026-11-19):** UI review is performed by an agent or person in a real browser. The former hardcoded legacy/v1 Chromium and WebKit test suites, synthetic browser fixture, and JSON report validator are removed. Browser review is **not** a required CI merge gate. Keep required source, integrity, build and public/private privacy checks in `validate-openwiki`. `knowledge-merge-gate` stays advisory and unchanged.

## Quick public-only UI preview

From a local checkout with Python dependencies installed:

```sh
python3 tools/diary/build.py --output-dir dist-public --public-only
python3 tools/diary/publish_v1.py --output-dir dist-public
python3 tools/diary/test_publication.py dist-public
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist-public
```

Use an agent with an actual browser to open `http://127.0.0.1:8000/`. Do **not** publish the private build or its files. If the agent runs in a different machine/container, it must have an authorized, safe way to reach the preview; localhost on one machine is not localhost on another. The optional Playwright-equipped Docker image offers a browser-capable shell (`tools/docker/run.sh browser-shell`) but does not itself make visual judgments or run scripted UI acceptance tests.

For a UI change, inspect only the impacted journeys plus these compact checks:

- [ ] Pages load with actual public-only generated data: Diary, Records, Projects, Search, Today, Calendar
- [ ] Record content, history/diff, navigation, links and Back/Forward/reload work
- [ ] Mobile/tablet/desktop screens are usable, screenshots inspected for broken layout or missing content
- [ ] Keyboard controls, focus, readable text, and visible error/retry states work where applicable
- [ ] Privacy-critical public/private export and negative leakage checks are green in required CI; do not rely on a screenshot for security
- [ ] Report visited URL, exact commit/deployment generation, browser, screenshots or concrete observations, and failures; leave unreviewed cases pending

Agent exploration and screenshots are *observations*, not a substitute for deterministic storage, projection and privacy tests. In particular, an inspected browser is not evidence that **every** existing S/P/U contract item passed. Keep open acceptance items visible in [#69](https://github.com/tempuku/knowledge-hub-starter/issues/69).

A cheap local compatibility check remains available: `python3 tools/diary/test_ios12.py`. It checks source syntax and PWA metadata, not actual Safari 12 operation.

## Physical original iPad Air (Safari 12) — manual local/device only

A desktop browser or simulated tablet viewport cannot establish actual original-iPad compatibility. With an authorized, deployed HTTPS URL, verify and record:

- [ ] Safari opens the application in portrait and landscape without clipping or horizontal overflow
- [ ] Diary Day/Week/Month navigation, opening records, Back/Forward and reload work
- [ ] Add to Home Screen starts a usable standalone app
- [ ] Previously visited permitted public content works offline where supported; private content is not publicly cached
- [ ] Actual target public/private authorization and anonymous-denial behavior is checked
- [ ] Record deployment URL, commit/generation, device/iOS version, date, observations and failures in [issue #2](https://github.com/tempuku/knowledge-hub-starter/issues/2)

**Evidence rule:** no browser/device execution means *pending*, not passing. Privacy/publication CI remains enforced.
