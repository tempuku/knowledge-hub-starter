# Knowledge Hub MCP — domain model and use cases (DDD v0.1)

**Status:** implementation candidate; not yet deployed. Source application repository is **public**. The storage target in this version is **exactly** the separately provisioned **private** `tempuku/knowledge-hub-data`, never `knowledge-hub-starter`. The private repository was not found among connected GitHub repositories at development time. This document describes intended behavior, not a claim of live operation.

## Ubiquitous language and bounded contexts

- **Record:** authoritative OKF v0.2 Markdown concept, stored under `openwiki/journal/YYYY/MM/DD/<slug>.md`.
- **Capture:** create a brand-new private draft record with references and date.
- **Revision:** replace an existing record's body, keeping its identity and immutable metadata.
- **Occurrence date:** `occurred_on`, the date the event happened; never inferred from Git timestamps.
- **Receipt:** an operation fingerprint under `.knowledge-mcp/operations/`, written in the same atomic Git commit, for safe retries.
- **Review proposal:** an unmerged draft PR; it is never an authoritative change until merged.
- **Publication:** a separate, explicitly authorized action to disclose material to a public destination; **out of scope** for this MCP.
- **Knowledge Archive** (core domain): notes, dates, source citations, indexes and revisions; Git is the source of truth.
- **Write Policy** (supporting domain): input validation, duplication guard, immutable-field enforcement, concurrency control, allowed operations and audit.
- **Repository Adapter** (infrastructure): GitHub fixed-repository API, immutable trees/commits, atomic branch updates and PR creation.
- **Authentication** (external boundary): launching MCP host controls who can use its credentials; this local stdio proof of concept must not be placed on the public internet. An HTTP/Cloudflare deployment requires separate OAuth/Access verification and authorization for every request.

## Aggregate invariants

1. **Private-only:** repository full name and `private: true` are verified before every read or write. Never fallback to public app data.
2. **Schema and identity:** every capture has title, description, valid calendar date, Markdown body, at least one HTTPS source URL, an idempotency key and an internally generated path. Agent cannot set filesystem path or visibility for capture.
3. **Draft by default:** every new record has `status: draft` and `visibility: private`. An agent cannot publish through the MCP.
4. **Atomic graph consistency:** note + year/month/day `index.md` links + operation receipt are committed in one Git tree update. Any failure rejects the operation.
5. **Protected metadata:** updates preserve type, title, description, project, tags, sources, `occurred_on`, status and visibility. v0.1 updates only the Markdown body; extensible typed metadata patches are future work.
6. **Concurrency:** a caller must present the current Git blob SHA; stale updates fail. Main branch update is non-force. Concurrent changes fail instead of being overwritten.
7. **Idempotency:** matching replay of direct writes returns `already_committed`; different payload under the same operation identifier is rejected.
8. **No destructive tools:** agents cannot delete or rename, force-push, merge a PR or manipulate arbitrary Git repository files.
9. **Publication isolation:** content in private Git is not copied to GitHub Pages or any public repository by MCP, even if an agent requests it.
10. **Explicit evidence:** a new note requires at least one source URL, but the tool cannot automatically verify whether that source actually supports its claims. Source verification remains a separate acceptance gate.

## Commands / application services

| Command (MCP tool) | Mode | Domain result | Preconditions |
| --- | --- | --- | --- |
| `knowledge_search` | Any | Up to 25 matching private diary paths | Valid query, private repo, permitted token |
| `knowledge_read` | Any | Record content + blob SHA | Valid diary path, private repo |
| `knowledge_validate` | Any | Validity and generated path | All fields pass policy; **no network write** |
| `knowledge_capture` | `direct-write` or `direct-capture` | Private commit | Not duplicate; indexes valid; Git protected branch permits write |
| `knowledge_capture` | `review-only` | Draft PR | Same record validation; no direct main write |
| `knowledge_update` | `direct-write` | Private commit updating body | Private record; expected current blob SHA; no conflict |
| `knowledge_update` | `review-only` or `direct-capture` | Draft PR | Same update validation; no direct main write |
| `knowledge_propose_edit` | All write-enabled modes | Draft PR | Never updates main, even when direct writes are enabled |

**Disabled configuration:** without `KNOWLEDGE_ENABLE_WRITE`, all mutations fail. Valid values are `review-only`, `direct-capture`, `direct-write`. Token must be present and scoped to the private data repository. `direct-write` is an explicit operational choice, not a default. All modes keep public publishing impossible.

## Use-case catalog

### UC-01: Agent captures a verified diary event

**Actor:** authorized local agent. **Trigger:** "write to diary".
**Input:** title, summary, event date, body, source links and stable operation key.
**Happy path:** validate → verify private repo → check receipt → check duplicate title/date → load indexes → assemble note/indexes/receipt → create tree and commit → non-force update private `main` → return path and SHA.
**Failure paths:** missing sources, invalid date, attempted public visibility, duplicate, stale Git ref, missing private repo, lack of write permission.
**Postcondition:** one private atomic commit, no public Git change.

### UC-02: Agent revises an existing diary record

**Actor:** authorized local agent. **Trigger:** "correct this note".
**Input:** exact diary path, current blob SHA from `knowledge_read`, replacement Markdown body, change reason, stable operation key.
**Happy path:** validate → verify private repo → check prior receipt → compare SHA → preserve frontmatter → tree commit with record + receipt → non-force private `main` update.
**Failure paths:** stale SHA, attempt to edit public-marked record, invalid path, unsafe Markdown, same key different payload, concurrent update.
**Postcondition:** updated private note; `occurred_on`, sources and privacy unchanged.

### UC-03: Agent submits review-only proposal

**Actor:** authorized agent. **Trigger:** uncertain or sensitive content change.
**Path:** choose `review-only` or call `knowledge_propose_edit` → create deterministic branch + draft PR → CI → human review → merge by a separate authorized workflow.
**Postcondition:** no direct authoritative change.

### UC-04: Agent searches or reads prior knowledge

**Actor:** authorized agent. **Path:** bounded path search → explicit record read → use returned current blob SHA for changes.
**Postcondition:** no mutation, no public fallback.

### UC-05: Retry an interrupted write

**Actor:** agent retrying after uncertain network result. **Path:** reuse exact idempotency key and payload → inspect atomic receipt → return `already_committed`; reject different payload for same key.
**Postcondition:** no duplicate commit.

### UC-06: Unauthorized disclosure or cross-repository write

**Actor:** adversarial or misconfigured agent. **Trigger:** `visibility: public`, malicious path, wrong repository, missing token, or private data repo not actually private.
**Postcondition:** request rejected; no public push, private fallback or leaked content.

## Dependency on existing read architecture

This is deliberately **not** a modification to the existing Cloudflare *read-only* gateway draft PR #9. The MCP is a local stdio client/server interface, with fixed GitHub repository and separate scoped credentials. For remote deployment reuse identity/authz principles of ADR 0001; do not expose stdio as an unauthenticated public HTTP service. The private browser UI and derived JSON indexes still need a reviewed private build pipeline.

## Open decisions / out of scope

- Create or provision the data repository with verified private visibility and narrow GitHub App permissions.
- Select protected-branch policy: if direct private commits are blocked, switch to `review-only` instead of bypassing rules.
- Authenticate remote clients before exposing MCP over Streamable HTTP; audit actor identity and rate-limit requests.
- Future patch commands for typed metadata changes (tags, sources, descriptions) must re-run full OKF validation.
- Evidence-quality verification and semantic duplicate detection are beyond simple presence/path guards.
