# Knowledge Hub evidence gate (advisory)

**Current owner policy (2026-11-13):** The owner has amended [issue #24](https://github.com/tempuku/knowledge-hub-starter/issues/24): independent GitHub approval is not required, and `knowledge-merge-gate` is advisory. This policy supersedes older #26/#42 instructions that described the evidence status as a merge blocker or required an administrator to enable it. The gate remains useful for diagnostics; its absence or failure does not block merging.

**Core CI remains required.** The main ruleset configuration at [`tools/ci/main-ruleset.json`](../tools/ci/main-ruleset.json) requires `validate-openwiki`. That workflow continues to run the OpenWiki checks, storage and projection tests, source validation, diary builds, privacy checks, and browser checks. The evidence status does not replace or weaken these checks.

## What the advisory gate does

The evaluator runs on supported pull request events and after the core workflow completes. It loads trusted code from the default branch and treats pull request text, issue descriptions, and artifact URLs as data. It does not check out or execute proposed pull request code.

It posts `knowledge-merge-gate` against the inspected head SHA. A success or failure reports whether the issue link, pinned design baseline, acceptance IDs, issue checkboxes, evidence rows, privacy/regression/limitations notes, current-head CI, and configured branch protections satisfy the parser's checks. API errors produce diagnostics. Stale workflow completions are ignored and do not refresh status for a newer head. The status is advisory: it is not listed as a required ruleset context and must not be treated as a merge blocker.

The parser can check completeness and exact-head linkage; it cannot establish that manually entered results are true. Manual or agent review should inspect the current diff, evidence, privacy and regression implications, unresolved acceptance scenarios, and core CI outcome. No approval requirement or reviewer-decision field is added by this gate. Do not describe synthetic parser tests as live enforcement evidence or claim unfinished #31/#32 acceptance.

## Validation and review

Run the parser tests with:

```sh
node --test tools/ci/merge-gate.test.cjs
```

Those tests exercise synthetic policy fixtures only. For a real implementation PR, reviewers should inspect its linked issue checklist and evidence, verify the exact current head and successful `validate-openwiki` run, and record any remaining limitations in the relevant issue or report. The owner may review issue #24 or any implementation PR at their discretion. A bounded implementation slice may merge after core CI passes even while parent acceptance or migration criteria remain open; keep those criteria open and do not claim them complete.

The ruleset configuration keeps the repository's configured pull request, force-push, and deletion protections and requires `validate-openwiki`; it does not require `knowledge-merge-gate`. This document describes repository intent, not live GitHub settings. Changes to active settings must be verified separately before claiming they are in effect.
