# Knowledge Hub evidence merge gate (issue #26)

**Normative contract:** [acceptance A-04](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/acceptance.md#a-04-implementation-evidence-and-completion), [migration M-05](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/migration.md#m-05-ordered-implementation-slices), [precedence D-05](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/overview.md#d-05-reading-order-and-precedence). These links are pinned to the approved commit, not a changing main-branch document. This slice changes CI policy and templates only; no knowledge storage or migration occurs.

## What runs

- Existing **Validate OKF and diary / validate-openwiki** continues to run its full OpenWiki validator, frontmatter tests, private/public builds, privacy audit, Chromium, WebKit and old-Safari source checks. An additional Node standard-library policy test covers incomplete, complete, stale-head, absent-review and skipped-CI cases. Parser fixtures are synthetic and do **not** establish real acceptance.
- New **Enforce evidence merge gate** runs on PR create/edit/head update, review submit/dismiss and core-workflow completion. It checks out the trusted **main** branch only; it does not run PR code, expose secrets to submitted code or consume proposed scripts as commands. PR text, issue descriptions, review descriptions and artifact links are treated only as data.
- The evaluator posts the GitHub commit status **knowledge-merge-gate** on the *actual head SHA*. No status is posted for a stale PR after an unrelated completed CI run. Any missing evidence, required issue checkbox, issue link, pinned design link, head SHA, per-check command/fixture/result/artifact, explicit privacy/regression/limits decision, an authenticated exact-head reviewer attestation, required core CI step, or main-branch protection causes **failure**, not skipped or optimistic success. API errors fail closed.
- Review can be an independent non-author GitHub APPROVED review on the current SHA with exact-head evidence attestation, or the explicitly owner-authorized **agent self-verification** recorded in [epic #24](https://github.com/tempuku/knowledge-hub-starter/issues/24): a genuine OWNER GitHub COMMENTED review on the exact SHA, explicitly labeled `Agent self-verification for head SHA: <sha>` and linking the epic. Do not describe agent self-verification as independent human review. PR body must still record the actual reviewer decision. A new commit invalidates old review evidence.

The parser requires each checkbox in the linked issue (including mandatory merge criteria) reproduced **verbatim and checked** once in the PR description. The evidence ledger has one C-numbered row per checkbox in issue order. The ledger fields are: exact head SHA, reproducible command/tool call, fixture revision, expected result, observed result, artifact/report URL, limits/failures. This is a machine-checkable completeness contract; it **does not authenticate the truth** of manually entered evidence. The attesting reviewer (an independent person or the explicitly delegated agent) must inspect each artifact and code diff. Issue #24 is an epic, not a substitute for the child issue's checklist. An amendment to the pinned contract must be approved in #24 before the implementation can claim compliance.

## Critical repository configuration — administrator action, not replaced by CI

A successful GitHub Action, a green PR template or a commit status **does not stop direct pushes**. On GitHub, configure an active ruleset or branch protection targeting **main**, with all of these safeguards:

1. Require pull requests for all main-branch changes and at least the SHA-bound evidence-gate review attestation. Under the owner-authorized agent self-review procedure, a separate GitHub APPROVED review is not a requirement; use an active ruleset with a required PR and zero platform approvals while **knowledge-merge-gate** enforces the exact-head self-review. If using an independent human review instead, require an approval in the ruleset. Keep direct pushes and force-pushes blocked. Do not create an administrator/bot bypass for routine merges.
2. Configure an **active ruleset**, including pull_request, non_fast_forward, and required_status_checks. Require both successful status contexts, from the intended GitHub Actions source: **validate-openwiki** (existing core CI job) and **knowledge-merge-gate** (privileged status on PR head). Neither may be skipped, neutral, disabled or permanently pending. Keep all existing required checks as well; never replace them with this gate.
3. Keep workflow permissions narrow: gate has contents/read, actions/read, pull-requests/read and statuses/write. Do not add checkout of a contributor's head ref to pull_request_target or workflow_run. Protect changes to gate files with review.
4. Verify **main** reports protected and inspect the actual active rule's required checks and bypass actors in GitHub Settings → Rules → Rulesets (a classic-only protection rule is insufficient for this gate's current effective-rules verification). Recording a configuration screenshot without checking the active rules is insufficient. Also try direct push with a disposable test branch/identity and confirm it is refused.

The connected GitHub integration can write repository files, issues and PRs, but **does not expose a branch-protection/ruleset write endpoint**. This is an administrator-only action through GitHub Settings or an appropriately authorized GitHub CLI session. Do not claim the configuration has been applied through a PR. On November 11, 2026, the branch metadata returned protected=false and the rulesets collection was empty. Recheck after an administrator configures enforcement; this snapshot is not proof of the future state.

Because the privileged workflow reads trusted **main** code, it becomes active only after that workflow is present on main. Before the first release, arrange a reviewed, auditable bootstrap of the trust policy; **do not** declare issue #26 merged/closed merely because its draft PR or mocked policy fixtures passed. Record any bootstrap exception explicitly in #24 and verify the final rules immediately after activation. Do not silently weaken or remove a required status to achieve the initial merge.

## Exact ruleset configuration

The reviewed, declarative ruleset request is
[\`tools/ci/main-ruleset.json\`](../../tools/ci/main-ruleset.json).
It targets only \`main\`, has **no bypass actors**, requires pull requests,
refuses force-push/deletion, and requires the two status contexts.
The owner-authorized agent review is enforced through the
\`knowledge-merge-gate\` status, rather than GitHub's native review count.

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
\`knowledge-merge-gate\`. No separate human approval is required under the
owner-authorized agent self-review procedure; do not weaken the verified
review-attestation status check.

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

Real negative case: open a disposable PR with a linked issue but **one unchecked checkbox**, or remove a C-row or replace a head SHA. Record the head SHA, PR URL, CI run, failing knowledge-merge-gate status and the GitHub UI merge refusal under the active main ruleset. Repeat for missing report URL, skipped core check and stale review. Merely observing the script output is not a protection demonstration.

Real positive case: create a disposable PR with complete real evidence for the current head, green **validate-openwiki** with every named job step successful, the actual authenticated reviewer attestation (independent APPROVED or owner-authorized agent COMMENTED) on the exact head, and a PR body whose reviewer decision is Approved. Record the successful gate status, real core CI and ruleset enforcement; confirm the authorized squash merge is permitted. Push a new head commit and verify that the old approval/evidence is invalid and the gate fails until evidence and review are renewed.

Required records for **each real case**: test PR/head SHA, fixture commit or revision, reproducible command, expected/observed output, direct GitHub Actions run/check or report URL, privacy/security outcome, limitations, human review and ruleset verification. Store the human report with OpenWiki; fixtures stay with tools. Never convert the example unit-test fixtures into asserted live evidence.

## Operational boundary

The commit status is refreshed at supported GitHub events, not on an unseen timer. If a workflow trigger or GitHub permission fails, a missing/pending required status must block merging. A reviewer must verify that the core workflow was run on the latest exact PR head; an older green result is not enough. Any issue dependency must have been validated and merged first. Issue #26 has none, but dependent issues must still wait for its **enforced** merge gate.
