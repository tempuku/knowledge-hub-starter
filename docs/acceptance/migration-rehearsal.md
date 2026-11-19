# Issue #36 — disposable migration rehearsal evidence

**Scope:** preview only; **no source cutover, public deploy, live-writer changes or private archive publication**.

- Normative source: [M-02, M-03, M-04](../../openwiki/design/migration.md), [P-01](../../openwiki/design/projections.md) and [P10–P13/P2](../../openwiki/design/acceptance.md).
- Frozen reviewed base: \`de749bed9053dd4bc9f96fee3cb7f816e5bdebcb\`
- Review manifest: \`migration/records-v1.json\`; verification: \`scripts/validate_inventory.py\` (#35).
- Fixed rehearsal time: \`2026-11-18T12:00:00Z\` (not a claimed occurrence time).
- Implementation: \`scripts/rehearse_migration.py\`
- Exact real-Git acceptance: \`tests/test_rehearse_migration.py\`; required workflow \`validate-openwiki\`.

## Repeatable commands (run only in disposable source checkouts)

\`\`\`sh
BASE=de749bed9053dd4bc9f96fee3cb7f816e5bdebcb
ROOT="$(pwd)"
TMP="$(mktemp -d)"
git clone --no-hardlinks "$ROOT" "$TMP/frozen"
git -C "$TMP/frozen" checkout --detach "$BASE"
python scripts/validate_inventory.py --manifest migration/records-v1.json
python scripts/rehearse_migration.py \
  --source "$TMP/frozen" --manifest "$ROOT/migration/records-v1.json" \
  --expected-head "$BASE" --fixed-time 2026-11-18T12:00:00Z \
  --output "$TMP/candidate-private" --report "$TMP/report-private.json"
python -m unittest discover -s tests -p test_rehearse_migration.py -v
# The private candidate contains raw original source/archive snapshots.
# Never commit, deploy, publish or upload it or its sourcebundle to public CI.
\`\`\`

The acceptance suite independently creates two identical candidates, checks the
Git tree and per-file hashes, fails changed-head and corrupt-manifest attempts,
builds public/private preview generations, and compares the private generation to
a no-Git rebuild using a verified, externally SHA-256-pinned source bundle.
The report contains only hashes, identities and counts; raw source and
historical snapshot contents remain in ephemeral runner storage.

## Acceptance assertions (expected)

| Check | Exact expected result |
|---|---|
| M-01 coverage | 45 reviewed source dispositions, unchanged frozen input |
| M-02 preservation | All 45 exact original bytes archived privately with their SHA-256 |
| M-02 history | 52 legacy events + 2 Git-backed repairs + 1 imported baseline + 23 normalization events = **78** distinct events |
| M-02 records | 23 canonical v1 records with sibling histories |
| P10/M-03 aliases | 61 reviewed old-UI mappings plus 23 reviewed source-path mappings, no duplicate history row |
| P11 | Identical source tree, candidate commit, files, deterministic preview output and manifest |
| P12 | Expected-head mismatch rejects without producing a candidate; corrupt manifest likewise |
| P13 | Original times retained under provenance; approved uncertain/decreasing chains use fixed migration time; **no invented occurrence date** |
| P2 | Private current/history/diff generation rebuilds from verified source bundle after Git metadata removal |
| Publication | The reviewed preview proposal permits only the independent public Diary diff demo and its two approved legacy events; private artifacts never appear in public bytes, aliases, reminders or counts |

## Gate, evidence, and privacy

The **current PR head** and required GitHub Actions run must be linked here after passing. A generated public fixture is not production publication permission. Actual private archives, candidate repositories, raw snapshots and complete source bundles must never be uploaded or logged as public evidence. Do not merge before the exact-head rehearsal checks, source/hash/alias audit, publication byte audit, reviewed code diff and #69 A/B prerequisite are independently satisfied.

**Status: implementation under validation, not yet accepted.**
