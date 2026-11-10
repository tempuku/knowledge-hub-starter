# Strict Knowledge Hub MCP (stdio, v0.1)

This is the write-policy application for the DDD contracts in [USE_CASES](../../docs/knowledge-mcp/USE_CASES.md) and [ACCEPTANCE](../../docs/knowledge-mcp/ACCEPTANCE.md). It is a **local stdio MCP prototype**, **not** an internet-accessible, authenticated or deployed service.

The only target repository is \`tempuku/knowledge-hub-data\` (private). The public \`tempuku/knowledge-hub-starter\` repository contains **only this implementation, documentation and synthetic tests**, not your notes. The private data repository must be provisioned and verified separately. The existing Cloudflare PR #9 remains a read-only access gateway; this code does not deploy or alter it.

## Run in a trusted MCP host

Requires Node.js 22.18+ and a GitHub App installation token (preferred) or a fine-grained token scoped **only** to \`tempuku/knowledge-hub-data\`. The token needs Contents read/write and Pull requests read/write if review-mode proposals are used. Protect the credential as a server/local secret; never check it in, paste it into chats, or ship it to the iPad web app.

Configure the hosting process environment (not a .env committed to Git):

\`\`\`sh
export KNOWLEDGE_GITHUB_TOKEN="(injected secret from your credential manager)"
export KNOWLEDGE_ENABLE_WRITE=direct-write
node tools/knowledge_mcp/server.mjs
\`\`\`

\`KNOWLEDGE_ENABLE_WRITE\` policy:

- \`review-only\`: capture/update → draft PR only; no direct writes to main.
- \`direct-capture\`: new drafts → commit directly; existing revisions → draft PR.
- \`direct-write\`: **both** new drafts and body revisions → private main after SHA validation; explicit \`knowledge_propose_edit\` → draft PR.
- unset: write calls fail. Read operations also require the repository-scoped token.

In a supported MCP client's configuration, register \`command: "node"\`, \`args: ["/ABSOLUTE/PATH/tools/knowledge_mcp/server.mjs"]\`, and inject those environment variables using the client's secrets mechanism. This is **not a ChatGPT plugin/hosted connector yet**; client registration and permissions must be completed separately.

**Do not expose this stdio server as unauthenticated HTTP.** Any future Worker/MCP HTTP deployment needs a reviewed Access/OAuth trust boundary, per-request authenticated identity and authorization, CSRF/origin handling where applicable, quotas, rate limits and audit identity attribution. This prototype relies on the local MCP host process and token isolation.

## Preparation

1. Verify \`tempuku/knowledge-hub-data\` exists and is **private**. Initialization requires a valid OKF \`openwiki/index.md\` with a Journal link (\`[...](journal/)\`) and ordinary date indexes. The current GitHub connection does not expose this repository, so this is an unresolved prerequisite.
2. Set branch permissions intentionally. If direct commits to \`main\` are forbidden, choose \`review-only\`; the MCP does not bypass GitHub branch rules.
3. Install/run in a trusted MCP host with the scoped secret. Never run it from a public browser or Cloudflare Pages.
4. Run \`node --test tools/knowledge_mcp/*.test.mjs\` (synthetic API fixtures, no credentials). No private notes are used in tests.
5. Compare behavior to \`docs/knowledge-mcp/ACCEPTANCE.md\`. Run a disposable real private record test only after provisioning.

## Tool contract

- \`knowledge_search({query})\` searches private diary **paths** (not record bodies); maximum 25.
- \`knowledge_read({path})\` returns content and blob SHA for one private dated entry.
- \`knowledge_validate({...captureFields})\` validates a capture without network writes.
- \`knowledge_capture({title,description,occurred_on,body,source_urls,idempotency_key,project?,tags?})\` commits a **private draft** directly or proposes a draft PR, depending on mode.
- \`knowledge_update({path,expected_sha,replacement_body,reason,idempotency_key})\` safely replaces body after SHA check, never metadata; commits directly in \`direct-write\` mode.
- \`knowledge_propose_edit({...updateFields})\` always creates a draft PR, regardless of direct-write policy.

Idempotency keys are agent-generated stable operation IDs (min 16 characters) and should be reused on retries **with the exact same payload**. Changes to the body or target require a new key. Each direct mutation stores a small hash receipt under the private repository's \`.knowledge-mcp/operations/\` folder in the same atomic Git commit. The receipt is not a public artifact.

The tool refuses to write arbitrary files, expose raw Git credentials, modify protected diary frontmatter, publish public records, remove records, or operate against other repositories.

**Scope of updates in v0.1:** Markdown body only; metadata is protected and requires a future independently validated metadata-patch use case. Never use this MCP for public-record editing.

## Local smoke check (protocol only, no token)

\`\`\`sh
printf '%s\n' \
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' \
'{"jsonrpc":"2.0","method":"notifications/initialized"}' \
'{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
| node tools/knowledge_mcp/server.mjs
\`\`\`

Expect one initialization response listing server capabilities and a \`tools/list\` response with safe tool names. This does not prove private GitHub access or real write functionality.

## Known limitations

- No private-data repository provisioning or data migration in this change.
- New records require HTTPS source links; source authenticity and factual support are **not** automatically verified.
- Duplicate control is a conservative same-day slug heuristic, not a semantic embedding search.
- GitHub generates an immutable commit, but Git branch protection or concurrent pushes may reject main advancement; the caller must retry with fresh state.
- No remotely connected ChatGPT tool yet; stdio setup is required.
- No automated rebuilding of private \`site-data/data/\` JSON; that belongs to the private authenticated reader and deployment pipeline.
