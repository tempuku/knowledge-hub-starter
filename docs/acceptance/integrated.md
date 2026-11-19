# Issue #37 — Integrated acceptance ledger (DAG 11)

Status: **in progress / blocked**. The report currently contains **60 pending entries**, not 60 successful tests. Opening or merging a documentation-only change does not certify acceptance. Normative contract: [approved #25 source at 5befec6](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/acceptance.md); performance budgets: [P-05 at same revision](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/projections.md#p-05-caching-failure-and-complexity). Tracker: [#37](https://github.com/tempuku/knowledge-hub-starter/issues/37).

## Gates and parallelizable work

- **#36** — deterministic rehearsal with frozen source, stable aliases, provenance, CAS stop, public/private and no-Git candidate builds; *not* production cutover.
- **#40** — an identified real agent (not a handcrafted JSON-RPC client) driving local stdio MCP against disposable Git, including safe conflict/idempotency/authorization handling.
- **#69** — projection, privacy and generated-v1 UI sections A–D, including local browser observation. Merged implementation alone does not prove browser acceptance.
- **#37** — integrate results only **after** predecessors are validated. S1–S20, P1–P16, U1–U24 must each have exact-head fixture/version, command, expected and observed result and evidence.

The first three can progress independently in their own issues; #37 may develop tests/fixture tooling in advance. The report's dependency statuses remain pending until the evidence is independently verified.

## Reproducible ledger usage

From a Git checkout at the exact tested commit:

~~~sh
# Validate all 60 IDs, report field shapes and every claimed pass.
python3 scripts/check_integrated_acceptance.py

# Make a fresh pending matrix if the contract ever needs to be re-keyed.
python3 scripts/check_integrated_acceptance.py --init > /tmp/issue-37-pending.json

# Actual completion gate: must exit nonzero until prerequisites, full matrix,
# 3-run benchmarks, agent transcript and latest-head CI are evidenced.
python3 scripts/check_integrated_acceptance.py --require-complete

# Fast regression tests for this ledger's fail-closed behavior.
python3 -m unittest discover -s tests -p 'test_integrated_acceptance.py' -v
~~~

Maintain [integrated-evidence.json](integrated-evidence.json) as the version-controlled **pending baseline**. For final exact-head verification, copy it to an **external report file** after the target PR head is frozen; populate actual scenario observations there and pass its absolute path via `--report`. Putting `tested_head` inside the very same commit whose SHA it references creates an impossible self-referential commit hash. Link the external completed report from the PR/CI evidence or issue; only include public-safe digests/counts. A passed scenario requires a matching per-row `tested_head`, real command/fixture, expected-versus-observed results, and supporting evidence links. Never put raw private records, log snapshots, cache content or secrets in the public evidence ledger. Private source candidates stay in secured local temporary storage. Reports should record digests/counts and canonical links.

All regressions and acceptance gaps remain failed/pending until observed; merging code or passing fast CI does not automatically verify UI. Under the 2026-11-19 owner simplification, UI acceptance uses direct agent/reviewer browser inspection of the actual generated **public-only v1** site, following the [short review checklist](ipad-local.md). Record visited routes, URL, exact commit/generation, browser and screenshots/observations. Deterministic publication/privacy checks remain required in CI; screenshot inspection never substitutes for a private-byte leak audit. Physical iPad operation remains separately pending until tested on actual hardware.

## Concrete execution commands

Existing lower-level test suites and UI generator (these commands are *inputs* to integrated acceptance, not proof that the 60 rows passed):

~~~sh
python3 -m unittest discover -s tools/records -p 'test_*.py' -v
python3 -m unittest discover -s tools/projection -p 'test_*.py' -v
python3 tools/diary/build.py --output-dir dist-public --public-only
python3 tools/diary/publish_v1.py --output-dir dist-public
python3 tools/diary/test_publication.py dist-public
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist-public
# Open the local public-only preview with a browser-capable agent for UI review.
~~~

#36 must supply a frozen source/manifest rehearsal report; #40 must supply an authentic agent-client transcript and disposable Git head history. Link those external reports into the integrated ledger, not copies of private source content.

## P16 exact performance contract

Committed deterministic generator and real measurement are still required. Fixture: 10,000 records, 100,000 events (including 1,000 on the busiest UTC day), 365 dates, nested depth 8, approximately 2 KiB average snapshots and 1,000 reminders. Record exact source bytes and generator revision. On a documented four-core/eight-GiB runner, measure **three clean builds** and report each elapsed time and peak RSS: median must be ≤120 seconds and ≤1 GiB. Measure Diary first usable list after manifest response (≤2 seconds), first-open record after data response (≤1 second), and transfer bytes on 10 Mbit/s, 100 ms RTT, 4× CPU throttling; record browsers and system environment. The evidence validator rejects missing runs, wrong fixture, and over-budget medians.

**Reproducible full-size measurements** (local/isolated runner; not a GitHub browser CI gate):

~~~sh
python3 scripts/generate_p16_fixture.py \
  --destination /tmp/kh-p16/source --report /tmp/kh-p16/fixture.json
python3 scripts/benchmark_p16.py \
  --source /tmp/kh-p16/source --fixture-report /tmp/kh-p16/fixture.json \
  --output-dir /tmp/kh-p16/builds --report /tmp/kh-p16/build-report.json
# This is synthetic source only; the public projection explicitly allowlists
# safe records and events and excludes private-transition records.
python3 tools/projection/build.py --root /tmp/kh-p16/source \
  --revision HEAD --mode public --destination /tmp/kh-p16/public-ui/data
# Copy/generated browser assets are handled by the local timing script.
python3 scripts/measure_p16_browser.py --dist /tmp/kh-p16/public-ui \
  --build-report /tmp/kh-p16/build-report.json \
  --report /tmp/kh-p16/performance-report.json
python3 -m unittest discover -s tests -p 'test_p16_fixture.py' -v
~~~

The P16 build script measures three **fresh processes**, deletes their temporary
projection outputs and logs real wall time and process peak RSS. The browser
script uses a local HTTP server, Chromium CDP CPU/network throttling and three
fresh contexts for each route. It reports the browser/public eligible counts
separately from the exact 10k/100k **source** workload; noneligible
public/private transition events are never shown in the public UI. CI only
executes a small deterministic fixture regression, never a reduced-size P16
acceptance substitute. An unmeasured/failed metric stays pending. Private data
and native source bundles must not be uploaded as public artifacts.

No benchmark claim exists yet. Do not reduce the fixture, silently change budgets, drop privacy checks, or count synthetic timings from the evidence-validator unit tests as measurements. Failed budgets require optimization or an explicit #24 design amendment.

## Release boundary

#37 does not perform #38 production source cutover or #39 deployment. Even if its ledger later passes, the downstream atomic cutover and live web verification are separate. Report any physical iPad gap explicitly, per the 2026-11-18 owner amendment; never claim it from browser emulation.
