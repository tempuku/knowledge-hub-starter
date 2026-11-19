# Issue #38: M-04 atomic cutover — pre-release runbook

**Status: BLOCKED — NOT CUT OVER (2026-11-19).** Normative terms: [M-04](../../openwiki/design/migration.md#m-04-transaction-and-cutover), [issue #38](https://github.com/tempuku/knowledge-hub-starter/issues/38). The current public site must continue serving its previous live generation.

## Stop/go gate

1. **Already satisfied (do not reopen):** #35's reviewed frozen inventory was merged in PR #68; #36's disposable deterministic rehearsal was merged in PR #90 after required exact-head CI. This is NOT the production source cutover.
2. **Required external storage:** identify an authorized **private** canonical repository for original bytes and archive material, verify that the trusted writer/publisher can access it, and confirm its source and deployment identities. The connected GitHub installation currently exposes only the public `tempuku/knowledge-hub-starter`; `tempuku/knowledge-hub-data` is not accessible as of 2026-11-19. Never copy archived private snapshots or private event chains to this public repo, a public PR, logs, Actions artifacts, or Pages.
3. **Freeze the actual current production source:** #35/#36 verified frozen baseline `de749bed9053dd4bc9f96fee3cb7f816e5bdebcb`, not the subsequently changed live `main`. Reconcile intervening records and native updates, re-freeze and verify exact remote HEAD before preparing a candidate. Refuse a stale/rebased/unreviewed candidate; a green old rehearsal does not authorize its direct push to current `main`.
4. **Candidate privacy and integrity:** review the exact complete candidate and every privacy boundary: original bytes, private archive, native chains, allowlisted public records/events, aliases, routes, indexes and generated output. Use the merged native-only loader and a SHA-pinned no-Git preview. The eligible public generation must exclude private content and all unapproved imported events. Keep prior public generation available until the new generation is verified.
5. **Global writer quiescence:** enumerate and pause every active production clone, bot, trusted CLI/MCP writer, legacy publisher and workflow; set `KH_WRITES_MAINTENANCE=1` on each trusted process. This is a local process interlock, NOT a distributed lease. Independently establish exclusive release authority and expected-head remote CAS.
6. **One cutover source commit:** combine the migrated canonical records/logs/indexes, protected private archive only in the authorized private source, single v1 CLI/MCP writer routing, explicit removal/denial of legacy writes, and native-log-only Diary/public projection wiring. No legacy fallback. Run required `validate-openwiki` and verify no private bytes entered the publication candidate.
7. **Actual source and generation evidence:** atomically publish via authorized expected-head CAS, confirm the resulting source SHA and native writer behavior, verify candidate generation identity and previous-live preservation under failure, and record the successful required CI link. Then close #38. #39 owns post-cutover live HTTPS smoke; #40 agent-client demo, #2 physical iPad and #12 private web gateway are not prerequisites under the 2026-11-19 lightweight owner policy.

## Candidate verification on an isolated checkout

Set FROZEN_HEAD, CANDIDATE and OUT using independently reviewed, exact SHA values and a disposable external **private** working directory. Do not infer them. Run the reconciliation and private generation only in the appropriate private trusted source checkout: a disposable runner directory alone does **not** make a public repository safe for archived private bytes. In the Git clone containing the candidate Git object, run:

    python tools/cutover/report_v1.py --root "$PWD" --revision "$CANDIDATE" --report-json "$OUT/reconciliation.json"
    git worktree add --detach "$OUT/candidate" "$CANDIDATE"
    python "$OUT/candidate/tools/records/validate_v1.py" --root "$OUT/candidate" --base "$FROZEN_HEAD" --strict-indexes
    python "$OUT/candidate/tools/projection/build.py" --root "$OUT/candidate" --revision "$CANDIDATE" --destination "$OUT/private-git" --mode private --native-only
    python "$OUT/candidate/tools/projection/build.py" --root "$OUT/candidate" --revision "$CANDIDATE" --destination "$OUT/public-git" --mode public --native-only
    python "$OUT/candidate/tools/projection/sourcebundle.py" --root "$OUT/candidate" --revision "$CANDIDATE" --output "$OUT/source-bundle.json" --receipt-output "$OUT/source-receipt.json"
    RECEIPT_SHA="$(sha256sum "$OUT/source-receipt.json" | cut -d' ' -f1)"
    python "$OUT/candidate/tools/projection/build.py" --destination "$OUT/private-nogit" --bundle "$OUT/source-bundle.json" --receipt "$OUT/source-receipt.json" --receipt-sha256 "$RECEIPT_SHA" --mode private --native-only
    diff -qr "$OUT/private-git/g" "$OUT/private-nogit/g"

Also build and compare the public no-Git generation, assert every reviewed old ID/alias/event mapping, and inspect public artifact bytes and all planned live network requests. Compare generation content hashes, not wall-clock published_at fields. Preserve exact validation command outputs and a privacy-safe SHA-bound report.

The reconciliation utility fails on missing/altered frozen bytes, missing exact historical snapshots, missing original archive bytes, lost event/provenance/operation allocations and lost legacy UI targets. It supplements, and does not replace, the full #36 rehearsal.

## Atomic source publication and fault model

Source CAS must happen against the exact frozen remote head with the reviewed candidate source commit, through an authorized path respecting branch protection. The local primitive in tools/cutover/atomic_v1.py is only an independently tested disposable-Git proof; it does not publish remotely or establish that all writers are paused.

- Maintenance, validation or commit preparation failure: no source-ref update and no live manifest switch.
- Concurrent remote source change: reject the CAS, refresh the entire inventory and repeat rehearsal. Never silently merge history.
- Successful source CAS but lost response: recover by inspecting actual ref and durable event receipts, not by making another commit.
- Generation publication failure: retain previous compatible live generation; mark publication pending, do not revert migrated source.
- After the first post-cutover write: do not automatically roll back source. Fix forward to preserve all new history. Before first write, a revert requires separately authorized action.
- #39 deploys and checks the actual HTTPS generation after this source cutover; physical iPad acceptance remains separate.

## Unchecked release gates

- [x] #35 reviewed inventory and #36 isolated rehearsal merged, with source counts, hashes and history/no-Git evidence linked in their issues.
- [ ] Authorized private production source/archive destination is accessible; no new private material enters the public repository or public CI artifacts.
- [ ] Intervening live source records reconciled against the actual frozen production HEAD; no added/changed record is silently discarded.
- [ ] Global writer quiescence and maintenance rejection proven at all production entry points.
- [ ] Exact-byte source/identity/event/alias reconciliation and private archive audit from the actual candidate.
- [ ] Legacy writes denied; CLI/MCP share only v1 writer; Diary and public generation use native logs only.
- [ ] Fault injection and public/private candidate generations pass strict native, no-Git and privacy checks.
- [ ] Current candidate required `validate-openwiki` passes; privacy-safe release report links source SHA, generation and CI.
- [ ] Authorized protected remote expected-head CAS observed; previous live generation preserved and post-write rollback prohibited.

Do not mark a gate complete merely because a preparatory script exists or a PR is green. Cite observed exact-head evidence for each.
