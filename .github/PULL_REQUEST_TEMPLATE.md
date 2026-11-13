# Knowledge Hub implementation PR — evidence gate

> Before merging, replace ALL placeholders below. Copy **every** checkbox from
> the linked issue verbatim; change each to [x] only after the result is
> demonstrated. Never assert a mock is real evidence. **One numbered C-row per
> issue checkbox**, in exactly the same order. The evidence gate status is
> advisory; it does not block merging. Core `validate-openwiki` CI remains
> required. The owner may request review at their discretion.
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

## Verification and optional owner review

The evidence gate's `knowledge-merge-gate` status is advisory and is not a
required GitHub status context. Reviewers should inspect the current diff,
issue checklist, SHA-bound evidence, privacy/regression implications, and the
exact-head `validate-openwiki` result. Independent GitHub approvals are not
required under the [owner-approved policy amendment](https://github.com/tempuku/knowledge-hub-starter/issues/24#issuecomment-6819748012).
The owner may request review at their discretion. Never report synthetic unit
tests as live enforcement proof or claim unfinished #31/#32 acceptance.
