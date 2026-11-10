# Knowledge Hub MCP — one acceptance criterion: WORKING MCP

**Acceptance is binary.** The implementation is accepted only when a real agent/client connects to the MCP and successfully writes **and updates** actual records in the verified **private** Knowledge Hub GitHub repository. Mocked tests, green CI, documentation and a draft PR do **not** satisfy this criterion.

## Live end-to-end demonstration (required)

- [ ] **WORKING MCP** — from a real compatible MCP client, using the deployed/available MCP connection:
  1. Discover tools via MCP initialization and `tools/list`; call `knowledge_capture` with a sourced, private test diary entry.
  2. Observe an actual GitHub commit on the private data repository, including the record and its directory indexes; verify no change to the public repository.
  3. Use `knowledge_read` to retrieve that record and its real Git blob SHA.
  4. Call `knowledge_update` with that SHA and revised body; verify the new content and second actual private commit.
  5. Retry the same operation: verify no duplicate commit. Attempt an update with an outdated SHA: verify rejection without data loss.
  6. Attempt unauthorized/public publishing or a write when configured against a public repository: verify rejection.
  7. Confirm the connected agent can repeat this flow in normal use, not only as a shell script in a test runner.

**Proof required:** an accessible, authenticated MCP endpoint or host connection; the actual tool responses; real private GitHub commit SHAs and affected paths; evidence of safe retry/conflict and rejection; no public content leak. Do not post note bodies, secrets or tokens in public PR logs.

**Current result: NOT ACCEPTED.** No real private `tempuku/knowledge-hub-data` repository was found through the connected GitHub account, and no live MCP client-to-private-repo demonstration has been performed. Code exists only on draft PR #11.

## DDD use cases (implementation behavior, not separate acceptance gates)

| Use case | Successful behavior |
| --- | --- |
| Capture | Atomic new private draft with OKF v0.2 frontmatter, source URL and date indexes |
| Update | Agent changes existing private Markdown body, preserving protected frontmatter and requiring current SHA |
| Read | Agent receives current private file contents and Git SHA |
| Search | Agent finds allowed private journal records |
| Retry | Same operation key and payload are idempotent |
| Refuse | Cross-repo writes, public publication, stale SHA and malformed records fail closed |
| Optional review | Explicit proposal creates a draft PR instead of committing directly |

See [DDD use cases](USE_CASES.md) for bounded contexts and invariants. Synthetic unit tests and CI can help diagnose failures, but **never substitute for the live demonstration above**. iPad web editing and Cloudflare deployment have their own future acceptance scope; they are not additional gates for *this* MCP acceptance.
