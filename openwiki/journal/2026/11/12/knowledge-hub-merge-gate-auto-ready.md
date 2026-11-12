---
type: diary-entry
title: Knowledge Hub protected merge gate and native PR readiness verified
description: Completed the evidence-based reviewless merge-gate foundation and proved CI-driven Draft to Ready in real protected GitHub pull requests.
occurred_on: "2026-11-12"
project: knowledge-hub
tags: [knowledge-hub, ci, validation, github, automation, security]
status: draft
visibility: public
sources:
  - resource: https://github.com/tempuku/knowledge-hub-starter/issues/24#issuecomment-6819748012
    title: Owner-approved change removing mandatory independent PR review
  - resource: https://github.com/tempuku/knowledge-hub-starter/issues/26
    title: Original merge-gate implementation and historical acceptance
  - resource: https://github.com/tempuku/knowledge-hub-starter/issues/42
    title: Completed remediation acceptance with evidence
  - resource: https://github.com/tempuku/knowledge-hub-starter/rules/27036674
    title: Active main-branch protections
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/43
    title: Rejected disposable negative test PR
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/49
    title: Merged positive reviewless-gate test PR
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/53
    title: Merged native Draft-to-Ready test PR
  - resource: https://github.com/tempuku/knowledge-hub-starter/actions/runs/43199420378
    title: GitHub Actions native Draft-to-Ready proof
---

# Protected evidence gate and automatic PR readiness

The Knowledge Hub implementation foundation reached a verified milestone on November 12: [original issue #26](https://github.com/tempuku/knowledge-hub-starter/issues/26) and its [acceptance remediation #42](https://github.com/tempuku/knowledge-hub-starter/issues/42) were completed and reconciled. Issue #26's original PR [#41](https://github.com/tempuku/knowledge-hub-starter/pull/41) had merged before all its historical acceptance conditions were established, so issue #42 supplied real follow-up enforcement tests. Original unchecked human-review requirements were preserved as history, not falsely marked as passing.

## Changes and policy

- [PR #44](https://github.com/tempuku/knowledge-hub-starter/pull/44) installed the evidence gate without mandatory independent GitHub approval, under the [explicit owner-approved amendment to epic #24](https://github.com/tempuku/knowledge-hub-starter/issues/24#issuecomment-6819748012). That did **not** remove the acceptance checklist, reproducible evidence ledger, current-head CI, privacy/regression assessments, or protected branch rules.
- The active [main ruleset #27036674](https://github.com/tempuku/knowledge-hub-starter/rules/27036674) requires pull requests, `validate-openwiki` and `knowledge-merge-gate`, has no bypass actors and no mandatory approving reviewer, and prohibits force-push and deletion.
- [PR #51](https://github.com/tempuku/knowledge-hub-starter/pull/51) corrected the trusted GitHub Actions auto-ready token: `pull-requests: write` alone produced a GraphQL `Resource not accessible by integration` error. The trusted-main `workflow_run` now also uses `contents: write`, while checkout keeps `persist-credentials: false` and never executes PR-head code. Promotion requires successful CI on the exact current PR commit.

## Live validation, not simulation

- **Negative:** [PR #43](https://github.com/tempuku/knowledge-hub-starter/pull/43) was deliberately incomplete. [Gate run #43195488164](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43195488164) posted failure; GitHub reported `mergeable_state=blocked`. The PR was closed without merging.
- **Positive:** [PR #49](https://github.com/tempuku/knowledge-hub-starter/pull/49) passed full [exact-head CI #43195669350](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43195669350) and [gate #43196217578](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43196217578), then was squash-merged without independent approval as [f5d11dd](https://github.com/tempuku/knowledge-hub-starter/commit/f5d11dd6cbe0c6d629afdc2902bb594a61542499).
- **Native automation:** [PR #53](https://github.com/tempuku/knowledge-hub-starter/pull/53) was created as a draft. Its [exact-head CI #43199159208](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43199159208) passed policy, OpenWiki, Chromium, WebKit and public-only export checks. GitHub Actions [run #43199420378](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43199420378) logged the Draft → Ready transition for commit `bc3f19b61a4254fd8ce8088314adc29d5b8c8a26`; the timeline actor was `github-actions[bot]`, not a manual assistant action. [Gate #43200352150](https://github.com/tempuku/knowledge-hub-starter/actions/runs/43200352150) passed; the PR squash-merged as [65a3cc1](https://github.com/tempuku/knowledge-hub-starter/commit/65a3cc1a9204ac94b3a17052afdf09500a6ebe69).

## Operating result and limits

Agents can implement issues, record real exact-head evidence and run the mandatory tests without requesting routine owner approval or a Ready-for-review click. The auto-ready workflow only changes PR state; it **does not approve or merge**. A failed evidence or CI gate blocks that merge while correction work continues. The owner may review the epic whenever desired.

These runs demonstrate protected-branch positive and negative cases and one same-repository native auto-ready transition. They do **not** establish direct-push denial through a disposable write attempt, fork-PR permission behavior, physical iPad validation, or completion of the remaining Knowledge Hub implementation DAG. These are separate scopes, not verified claims.

**Status:** Gate foundation complete; downstream work continues under each issue's own checks. No routine manual action is needed from the owner for PR readiness.
