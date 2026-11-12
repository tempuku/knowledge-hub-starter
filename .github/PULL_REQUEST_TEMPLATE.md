# Knowledge Hub implementation PR — evidence gate

> Before merging, replace ALL placeholders below. Copy **every** checkbox from
> the linked issue verbatim (including its mandatory gate); change each to [x]
> only after the result is demonstrated. Never assert a mock is real evidence.
> **One numbered C-row per issue checkbox**, in exactly the same order.
> Each row must include real, current-head evidence. Unchecked items,
> unverified scenarios or stale SHA intentionally block merging. No independent
> approval is required by the owner-approved issue #24 policy amendment.
>
> Gate specification: [issue #26](https://github.com/tempuku/knowledge-hub-starter/issues/26)
> and [A-04 acceptance](https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/acceptance.md#a-04-implementation-evidence-and-completion).

## Traceability

Closes #<child-issue-number>

Design baseline: 5befec6cc67486327fa36b22f54f22db59cceecb

Design sections: https://github.com/tempuku/knowledge-hub-starter/blob/5befec6cc67486327fa36b22f54f22db59cceecb/openwiki/design/acceptance.md#a-04-implementation-evidence-and-completion

Head SHA: <exact-40-character-PR-head-SHA>

Acceptance IDs: <A-04 or explicit S/P/U IDs assigned by child issue>

Privacy/security/integrity: <explicit review of public/private boundaries, trust, integrity and any exposures>

Regression impact: <list affected existing checks and exact outcomes>

Known limitations: <specific known gaps; if none, say why>

## Validation checklist

Copy the entire issue's checkboxes here **verbatim and in issue order**,
including its merge-blocker section. Mark checked only after verified.

- [ ] <first exact issue checkbox text>
- [ ] <second exact issue checkbox text; add all remaining issue boxes>

## Evidence ledger

Row C1 supports the first issue checkbox, C2 the second, etc.
All rows must carry the **same exact current head SHA**, a command/tool call,
fixture revision, expected and observed outcomes, a concrete artifact/report URL,
and limitations/failures. Use plain text without literal table separator pipes.
Reports should live in OpenWiki, test fixtures in tooling, and remote CI runs
should link the exact SHA. Do not use this template as evidence of completion.

| Check | Head SHA | Reproducible command/tool call | Fixture revision | Expected | Observed | Artifact/report URL | Limits/failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | <head-sha> | <command> | <fixture-revision> | <expected> | <observed> | <artifact-url> | <limitations> |
| C2 | <head-sha> | <command> | <fixture-revision> | <expected> | <observed> | <artifact-url> | <limitations> |

## Autonomous verification and optional owner review

Independent GitHub APPROVED reviews are **not mandatory** under the
[owner-approved policy amendment](https://github.com/tempuku/knowledge-hub-starter/issues/24#issuecomment-6819748012).
The assistant must verify every checkbox and current-head evidence row, inspect
privacy/regression implications, and check exact-head CI and both required
GitHub status contexts before squash merge. Optional human review of epic #24
is welcome but is not an implementation-PR blocker. Never report synthetic
unit tests as live merge-enforcement proof.
