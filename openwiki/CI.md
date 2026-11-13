---
type: guide
title: Knowledge Hub CI validation and troubleshooting
status: draft
tags: [ci, validation, knowledge-hub]
---

# CI validation and troubleshooting

The `Validate OKF and diary` workflow must run on pull requests, pushes to `main`, and manual dispatch. Keep the `validate-openwiki` job enabled. Its checks cover staged OKF pages and links, diary exports, JavaScript syntax, iOS 12 source compatibility, Chromium and WebKit interactions, and the public export allowlist. Browser checks use a local server and do not publish records.

## Target validation additions (not yet implemented)

The [acceptance contract](design/acceptance.md) requires v1 record/event schemas, complete chain and trusted-base prefix validation, real writer/MCP transaction tests, deterministic generation/publication checks, migration reconciliation and UI/performance evidence. Existing OKF/browser checks do not establish those guarantees. Keep current checks enabled while implementing the target.

## Current owner policy — November 13, 2026

The owner amendment to [issue #24](https://github.com/tempuku/knowledge-hub-starter/issues/24) makes `knowledge-merge-gate` advisory; it is not a required status or administrator-configuration blocker. The declarative [`main-ruleset.json`](../tools/ci/main-ruleset.json) requires `validate-openwiki`. Current live GitHub settings after this policy change have not been reverified. Reviewers should still inspect the diff, exact-head core CI, evidence, privacy impact and remaining acceptance work. Bounded implementation PRs may merge with parent criteria still open; those criteria stay open and must not be described as complete.

## Historical evidence-gate configuration — verified November 12, 2026

The configuration and enforcement results below document the former policy as observed on November 12. They are historical evidence and do not describe current merge requirements.

This milestone is recorded in the [November 12 diary entry](journal/2026/11/12/knowledge-hub-merge-gate-auto-ready.md), [original implementation issue #26](https://github.com/tempuku/knowledge-hub-starter/issues/26) and [completed remediation issue #42](https://github.com/tempuku/knowledge-hub-starter/issues/42).

### Prior diagnostic contract

The active [main ruleset #27036674](https://github.com/tempuku/knowledge-hub-starter/rules/27036674) requires pull requests and successful `validate-openwiki` **and** `knowledge-merge-gate` statuses, with no bypass actors. Force pushes and deletion are denied by the ruleset. Mandatory independent GitHub approval was explicitly removed by the [owner-approved epic #24 amendment](https://github.com/tempuku/knowledge-hub-starter/issues/24#issuecomment-6819748012); the platform has zero required approving reviews.

The trusted-main [evidence merge gate](../tools/ci/merge-gate.cjs) checks the **current PR head SHA**, exact linked implementation issue, pinned design baseline, all verbatim checked issue acceptance items, one reproducible SHA-bound `C1…Cn` evidence row per item, concrete artifact URLs, privacy/regression/limitations assessments, current complete `Validate OKF and diary` job with no skipped required steps, and effective main branch rules. A reviewer-decision field and non-author GitHub APPROVED review are **not** required. A structurally complete evidence table alone cannot prove that its claims are true; the agent must inspect actual runs and artifacts. Never weaken the fail-closed gate or replace observed CI with a synthetic unit-test fixture.

### Real merge-enforcement tests

- **Negative:** [PR #43](https://github.com/tempuku/knowledge-hub-starter/pull/43), head `0267ba1eef8a1844165997bd336e7fef56944608`, posted `knowledge-merge-gate=failure` in [run #43195488164](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43195488164). GitHub reported `mergeable_state=blocked`; the disposable PR was closed unmerged.
- **Positive:** [PR #49](https://github.com/tempuku/knowledge-hub-starter/pull/49), head `4216cf7d7a6840c1c3747c132eb6bdfc677252d8`, passed [exact-head CI #43195669350](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43195669350), including policy, Chromium, WebKit and public-only export, and [gate #43196217578](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43196217578). GitHub reported `mergeable_state=clean`; the PR squash-merged as [f5d11dd](https://github.com/tempuku/knowledge-hub-starter/commit/f5d11dd6cbe0c6d629afdc2902bb594a61542499) without human GitHub approval.

### Native GitHub Actions Draft → Ready, after CI

The trusted-main [auto-ready workflow](../.github/workflows/auto-ready.yml) listens to completion of `Validate OKF and diary`, not merely a PR being opened. Its [helper](../tools/ci/auto-ready.cjs) only transitions an **open same-repository draft PR targeting main** if that completed `pull_request` run succeeded at the **exact current head SHA**. It checks out trusted main, keeps `persist-credentials: false` and never executes submitted PR code, approves a review or merges the PR.

[Initial run #43195928527](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43195928527) failed the `markPullRequestReadyForReview` GraphQL mutation with `Resource not accessible by integration` despite `pull-requests: write` and `contents: read`. [PR #51](https://github.com/tempuku/knowledge-hub-starter/pull/51) added `contents: write` to the trusted workflow token, while retaining `pull-requests: write`; this **expands permissions** and therefore must remain confined to the trusted-main, metadata-only workflow.

**Live result:** [PR #53](https://github.com/tempuku/knowledge-hub-starter/pull/53) began as a draft. Its [exact-head CI #43199159208](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43199159208) passed all required steps; [GitHub Actions run #43199420378](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43199420378) logged promotion at commit `bc3f19b61a4254fd8ce8088314adc29d5b8c8a26`, and the GitHub PR timeline reported `ready_for_review` by `github-actions[bot]`. Its [gate #43200352150](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43200352150) passed and it squash-merged as [65a3cc1](https://github.com/tempuku/knowledge-hub-starter/commit/65a3cc1a9204ac94b3a17052afdf09500a6ebe69).

A successful auto-ready operation is **not** permission to merge. The workflow does not auto-merge; reviewers should inspect current-head CI and evidence. The evidence status is advisory under the current owner policy.

**Known limits:** The observed native promotion was for a same-repository PR, not an untrusted fork. No disposable direct-push denial attempt, physical iPad verification, live Cloudflare deployment or completion of the remaining Knowledge Hub implementation DAG is claimed. The checked ruleset establishes configured protection; the tested PRs establish positive/negative merge enforcement.

## Repair of the paused pipeline

The workflow had a temporary unconditional `if: false` on its only job. GitHub reported those runs as skipped, so they provided no validation. The [last failed validation run before the pause](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42869097404) expected the old `records` counter text while the app displayed `changes`. Later changes updated the counter tests to the current `entries` label, but two additional regressions remained on the current main branch:

- The history interaction test still rejected all GitHub links and expected a clickable title. The current app provides a canonical **File:** source link and explicit **Open** / **Show diff** buttons. The test now checks that link and exercises the explicit controls.
- `index.html` loaded version 9 of the JavaScript and stylesheet, while the service worker precached version 8. Updating the cache name and shell URLs to version 9 restores precaching of the files actually loaded. Keep these versions synchronized when changing the app shell.

The repair removes the unconditional validation skip. Build, publication, and browser assertions remain required; a skipped run is not a passing result. Chromium and WebKit both remain in the workflow. Source and browser checks do not establish physical iPad acceptance.

The staged checker also exposed a newer schema mismatch: [the guide](GUIDE.md) and current demo record use `status: completed`, but the pinned upstream OKF validator accepts only `draft`, `stable`, and `deprecated`. A local adapter explicitly accepts `completed` as a Knowledge Hub extension while retaining all other upstream checks and rejecting unknown statuses. The downloaded upstream validator remains unchanged and hash-verified. Regression tests cover accepted statuses, invalid YAML and other invalid metadata, and run in CI before the staged checker. This is a local compatibility extension, not a claim that upstream OKF defines `completed`.

## CI completion handoff

The separate `Return to PR when CI completes` workflow handles completed validation runs. It needs `pull-requests: write` to create or update its PR conversation comment; `issues: write` with `pull-requests: read` returned `403 Resource not accessible by integration` in [this handoff run](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42975069303).

Keep its existing same-repository, current-head and open-PR checks. This privileged workflow must never check out or run PR code. Its comment records a CI result but does not authorize merging; an agent or maintainer verifies current-head core CI and evidence. The evidence status is advisory and independent GitHub approval is not required under the owner amendment linked above.

## Verification

Run the commands in the [repository README](../README.md), including the staged OKF checker before every commit. Build `dist/` before browser tests, and separately build and audit `dist-public/` with `--public-only`. Inspect the real GitHub Actions result for the exact commit after pushing; local macOS checks alone do not establish that the Ubuntu runner passes.

The repair merged in [PR #22](https://github.com/tempuku/knowledge-hub-starter/pull/22). The [PR validation run](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42979580422) passed every step for `cb4fca7f1fd210846941c37ccc25caa0bd4022cf`. The [main push validation run](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42979797478) also passed every step for merged commit `e68270c2d1dc4c3195eaab4590a74677108f999d`, including Chromium, WebKit and the public-only export audit.

The [handoff triggered by PR #22](https://github.com/tempuku/knowledge-hub-starter/actions/runs/42979756960) still ran the old default-branch workflow before the repair merged and failed with the existing permissions error. A fresh PR after the merge is required to exercise the repaired handoff against an open current head; a successful validation run alone does not verify that comment write.
