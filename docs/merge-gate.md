# Knowledge Hub evidence merge gate (issues #26 and #42; policy amendment #24)

**Owner-approved review-policy amendment (2026-11-12):** [epic #24 decision](https://github.com/tempuku/knowledge-hub-starter/issues/24#issuecomment-6819748012) removes all mandatory independent GitHub review and reviewer-decision attestation for implementation PRs. The owner may review the epic at discretion. Neither this amendment nor autonomous merges waive issue evidence, exact-head CI, privacy or actual active GitHub branch protection. The structural parser cannot authenticate the truth of supplied evidence; agent verification must be accurate and auditable. The ruleset has 0 native approving reviewers and both required status contexts. Changes to trusted gate code still require verified CI/evidence before merge.

**Normative contract:** [acceptance A-04](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/acceptance.md#a-04-implementation-evidence-and-completion), [migration M-05](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/migration.md#m-05-ordered-implementation-slices), [precedence D-05](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/overview.md#d-05-reading-order-and-precedence). These links are pinned to the approved commit, not a changing main-branch document. This slice changes CI policy and templates only; no knowledge storage or migration occurs.

## What runs

- Existing **Validate OKF and diary / validate-openwiki** continues to run its full OpenWiki validator, frontmatter tests, private/public builds, privacy audit, Chromium, WebKit and old-Safari source checks. An additional Node standard-library policy test covers incomplete, complete, stale-head and skipped-CI cases. Parser fixtures are synthetic and do **not** establish real acceptance.
- New **Enforce evidence merge gate** runs on PR create/edit/head update, core-workflow completion. It checks out the trusted **main** branch only; it does not run PR code, expose secrets to submitted code or consume proposed scripts as commands. PR text, issue descriptions and artifact links are treated only as data.
- The evaluator posts the GitHub commit status **knowledge-merge-gate** on the *actual head SHA*. No status is posted for a stale PR after an unrelated completed CI run. Any missing evidence, required issue checkbox, issue link, pinned design link, head SHA, per-check command/fixture/result/artifact, explicit privacy/regression/limits decision, required core CI step, or main-branch protection causes **failure**, not skipped or optimistic success. API errors fail closed.
- An independent GitHub review is **not required**. The assistant may run repeatable checks, inspect evidence, and transition/merge passing PRs. The gate fails on mismatched current SHA or missing evidence, not on absent approvals. A new commit invalidates SHA-bound evidence and requires fresh CI.

The parser requires each checkbox in the linked issue (including mandatory merge criteria) reproduced **verbatim and checked** once in the PR description. The evidence ledger has one C-numbered row per checkbox in issue order. The ledger fields are: exact head SHA, reproducible command/tool call, fixture revision, expected result, observed result, artifact/report URL, limits/failures. This is a machine-checkable completeness contract; it **does not authenticate the truth** of manually entered evidence. The assistant must self-validate the code diff and evidence, recording observed outcomes without pretending this is independent review. Issue #24 is an epic, not a substitute for the child issue's checklist. An amendment to the pinned contract must be approved in #24 before the implementation can claim compliance.

## Critical repository configuration — administrator action, not replaced by CI

A successful GitHub Action, a green PR template or a commit status **does not stop direct pushes**. On GitHub, configure an active ruleset or branch protection targeting **main**, with all of these safeguards:

1. Require pull requests for all main-branch changes with **zero native required approving reviewers** (owner-approved reviewless policy). The **knowledge-merge-gate** independently verifies every SHA-bound evidence row and current-head CI. Keep direct pushes and force-pushes blocked. Do not create an administrator/bot bypass for routine merges.
2. Configure an **active ruleset**, including pull_request, non_fast_forward, and required_status_checks. Require both successful status contexts, from the intended GitHub Actions source: **validate-openwiki** (existing core CI job) and **knowledge-merge-gate** (privileged status on PR head). Neither may be skipped, neutral, disabled or permanently pending. Keep all existing required checks as well; never replace them with this gate.
3. Keep workflow permissions narrow: gate has contents/read, actions/read, pull-requests/read and statuses/write. Do not add checkout of a contributor's head ref to pull_request_target or workflow_run. Check changes to gate files through the full evidence-gate and core CI pipeline.
4. Verify **main** reports protected and inspect the actual active rule's required checks and bypass actors in GitHub Settings → Rules → Rulesets (a classic-only protection rule is insufficient for this gate's current effective-rules verification). Recording a configuration screenshot without checking the active rules is insufficient. Also try direct push with a disposable test branch/identity and confirm it is refused.

The connected GitHub integration can write repository files, issues and PRs, but **does not expose a branch-protection/ruleset write endpoint**. This is an administrator-only action through GitHub Settings or an appropriately authorized GitHub CLI session. Do not claim the configuration has been applied through a PR. As of 2026-11-12 GitHub confirms ruleset #27036674 is ACTIVE on main with no bypass, zero native review requirement and **both** `validate-openwiki` and `knowledge-merge-gate` required. The proposed removal of independent review from the trusted **merge-gate code** is not active until this PR is merged.

Because the privileged workflow reads trusted **main** code, it becomes active only after that workflow is present on main. Before the first release, arrange an auditable, owner-approved one-time policy transition; **do not** declare issue #26 merged/closed merely because its draft PR or mocked policy fixtures passed. Record any bootstrap exception explicitly in #24 and verify the final rules immediately after activation. Do not silently weaken or remove a required status to achieve the initial merge.

## Exact ruleset configuration

The maintained, declarative ruleset configuration is
[\`tools/ci/main-ruleset.json\`](../../tools/ci/main-ruleset.json).
It targets only \`main\`, has **no bypass actors**, requires pull requests,
refuses force-push/deletion, and requires the two status contexts.
SHA-bound evidence, protected-branch checks and exact-head CI are enforced through the
\`knowledge-merge-gate\` status. Neither this gate nor the native ruleset requires a human review.

A repository administrator authenticated with a token having
**Administration: write** may apply it through the official GitHub CLI:

~~~sh
gh auth status
gh api --method POST repos/tempuku/knowledge-hub-starter/rulesets \
  --input tools/ci/main-ruleset.json
gh api repos/tempuku/knowledge-hub-starter/rules/branches/main
gh api repos/tempuku/knowledge-hub-starter/rulesets
~~~

Equivalent UI: repository **Settings → Rules → Rulesets → New branch ruleset**.
Choose active enforcement, branch \`main\`, require a PR, no bypass roles,
block force pushes/deletion, and require \`validate-openwiki\` plus
\`knowledge-merge-gate\`, with zero required approving GitHub reviews. Do not weaken evidence/CI requirements.

**Bootstrap ordering:** The privileged status workflow cannot operate until
its trusted code exists on \`main\`. Activating the ruleset *before* installing
that code will intentionally block every PR, including the bootstrap PR.
Any one-time bootstrap must be expressly approved as an amendment in #24,
must be limited to the reviewed implementation, and must be followed by
ruleset activation and live positive/negative tests **before issue #26 closes
or any dependent DAG PR merges**. Do not claim an unenforced checkout is
an active gate.

## Reproducible tests and required real evidence

Local policy parser:

    node --test tools/ci/merge-gate.test.cjs

Real negative case: open a disposable PR with a linked issue but **one unchecked checkbox**, or remove a C-row or replace a head SHA. Record the head SHA, PR URL, CI run, failing knowledge-merge-gate status and the GitHub UI merge refusal under the active main ruleset. Repeat for missing report URL, skipped core check and stale SHA evidence. Merely observing the script output is not a protection demonstration.

Real positive case: create a disposable PR with complete real evidence for the current head, green **validate-openwiki** with every named job step successful, a complete evidence ledger and explicit privacy/regression assessments. Record the successful gate status, real core CI and ruleset enforcement; confirm the authorized squash merge is permitted. Push a new head commit and verify that the old approval/evidence is invalid and the gate fails until evidence and CI are renewed.

Required records for **each real case**: test PR/head SHA, fixture commit or revision, reproducible command, expected/observed output, direct GitHub Actions run/check or report URL, privacy/security outcome, limitations, agent verification notes and ruleset verification. Store the human report with OpenWiki; fixtures stay with tools. Never convert the example unit-test fixtures into asserted live evidence.

## Operational boundary

The commit status is refreshed at supported GitHub events, not on an unseen timer. If a workflow trigger or GitHub permission fails, a missing/pending required status must block merging. The automation must verify that the core workflow was run on the latest exact PR head; an older green result is not enough. Any issue dependency must have been validated and merged first. Issue #26 has none, but dependent issues must still wait for its **enforced** merge gate.
