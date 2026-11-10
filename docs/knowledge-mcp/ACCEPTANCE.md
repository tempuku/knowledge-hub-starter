# Knowledge Hub MCP — acceptance checklist (BDD / executable contracts)

This is the **validation contract** for the strict knowledge writer. Each scenario has a measurable expected result. Unit tests use an in-memory GitHub API and **do not establish that live storage, Cloudflare authentication or remote clients work**. The final acceptance gate requires a newly provisioned private repository, scoped credentials, CI, and real negative tests.

## A. Policy and domain validation

- [ ] **AC-01** Capture is deterministic: identical validated input yields same ID, path and Markdown.
- [ ] **AC-02** Invalid/unknown fields, invalid date/path, unsafe Markdown and missing source URLs fail before GitHub write operations.
- [ ] **AC-03** Captured record is always \`status: draft\`, \`visibility: private\`; caller cannot supply a different visibility or repo.
- [ ] **AC-04** A new diary record and missing date-partitioned indexes are written together, exactly once.
- [ ] **AC-05** Same-day same-title duplicate is rejected, rather than silently creating redundant files.
- [ ] **AC-06** Revision preserves frontmatter, \`occurred_on\`, type, visibility and links. Public-marked records cannot be edited.
- [ ] **AC-07** Invalid record path, missing file and stale \`expected_sha\` fail without writing.
- [ ] **AC-08** Same operation key and identical payload retry without a second commit; mismatched payload under same key fails.
- [ ] **AC-09** An intervening Git main change is not overwritten; non-force update rejects any concurrent ref movement.

## B. MCP interface

- [ ] **AC-10** Standard stdio MCP initialization / \`tools/list\` / \`tools/call\` work with a supported client; JSON-RPC errors cannot leak tokens or private bodies.
- [ ] **AC-11** Tool schemas permit only search, read, validate, capture, update and propose-edit; no generic file writer/deleter or publish operation is exposed.
- [ ] **AC-12** \`review-only\` mode opens a draft PR for captures/updates and never directly advances main.
- [ ] **AC-13** \`direct-capture\` mode commits a new private draft but routes edits to draft PR review.
- [ ] **AC-14** \`direct-write\` mode permits agents to commit both a new private draft and a SHA-checked private diary body update; explicit \`knowledge_propose_edit\` still opens a draft PR.
- [ ] **AC-15** Without an enabled write mode, changes fail closed; read-only inspection remains possible with a valid read token.

## C. Storage security / privacy

- [ ] **AC-16** Every read/write verifies the exact target repository is private; missing/misconfigured/public repo fails before reading records.
- [ ] **AC-17** Credential is repository-scoped, server-side and absent from public Git, UI, trace payloads and CI logs.
- [ ] **AC-18** Any attempted public publication, cross-repository write, arbitrary path or metadata visibility override is denied.
- [ ] **AC-19** No private records, derived private JSON or operation receipts appear in the public Pages artifact/history as a result of MCP.
- [ ] **AC-20** No deletion/force-push/merge/publish operation exists in the writer tool surface.
- [ ] **AC-21** The complete private archive passes the pinned OKF v0.2 checker after representative direct captures/updates.
- [ ] **AC-22** If exposed remotely, every request passes verified authentication/authorization and negative unauthenticated tests; stdio mode must never be exposed as unauthenticated HTTP.

## D. Real-world acceptance (not unit tests)

- [ ] **AC-23** Verify \`tempuku/knowledge-hub-data\` exists, is private, has valid \`openwiki/index.md\` and initialized journal indexes, and the intended bot has least-privilege access.
- [ ] **AC-24** Launch MCP in a supported client, capture a disposable private diary record, and inspect its Git commit, YAML metadata and date indexes.
- [ ] **AC-25** Read the record, update its body with its current SHA, and confirm exactly one private commit; retry unchanged operation key and confirm no second commit.
- [ ] **AC-26** Attempt stale update, public repo configuration, malformed input and private→public visibility change; each must fail.
- [ ] **AC-27** Verify private UI/Cloudflare read pipeline refreshes derived JSON after edits; test actual authenticated reading plus anonymous denial on live HTTPS.
- [ ] **AC-28** Real iPad Air 1 / Safari 12 reads edited private records after login; device observation is required, not inferred from Chromium CI.

## Given / When / Then scenarios

**S01 — Direct capture**

Given the private target and \`direct-write\` mode, when an agent captures a valid note with a new idempotency key, then the response includes \`committed_private\` and a commit SHA, while the note, missing indexes and receipt are in one private commit.

**S02 — Direct revision**

Given a private existing record with blob SHA A, when an agent supplies A and a new Markdown body, then the service changes only the body in private Git and returns \`updated_private\`.

**S03 — Concurrent revision**

Given a record that has changed since SHA A, when an agent submits a revision based on A, then the service refuses \`STALE_OR_MISSING_RECORD\` and does not overwrite the newer record.

**S04 — Safe retry**

Given a write previously committed with operation K, when an agent repeats the same operation K with the same input, then it receives \`already_committed\`, and no extra Git commit occurs. Changing the payload while keeping K must fail.

**S05 — Public isolation**

Given only public \`knowledge-hub-starter\` is accessible, when an agent requests capture/update, then the call fails; it must never commit a note to the public app source.

**S06 — Human-review override**

Given \`direct-write\` mode, when the agent explicitly calls \`knowledge_propose_edit\`, then a draft PR is created rather than modifying private main.

## Status evidence

| Gate | Evidence required | Status at proposal time |
| --- | --- | --- |
| Domain tests | Node test output in CI | Not yet verified |
| MCP protocol | Actual stdio client invocation | Not yet verified |
| Git integration | Real private repository + resulting commit | Blocked: private target not present |
| Access security | Live anonymous denial + signed-in read | Not yet deployed |
| Old iPad | Physical device result | Not yet verified |

**Rule:** Mark a checkbox only after observing its evidence. Passing mocked tests does not turn a live deployment criterion green.
