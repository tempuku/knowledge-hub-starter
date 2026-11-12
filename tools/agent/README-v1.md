# Knowledge Hub v1 trusted CLI and stdio MCP

This is the **source-facing v1 domain writer**, not a deployed remote server,
not an authenticated browser editor, and not a production migration.
All six commands use \`tools/records/service_v1.py\` through the single
\`tools/agent/knowledge_service.py\` dispatch. There is no second canonical
writer or network listener.

## Trusted launch configuration

Prepare an external JSON file outside the Git checkout (do not commit it):

\`\`\`json
{
  "repository_mode": "private",
  "operations": ["read", "create", "update", "move", "archive", "reopen"],
  "publisher_scope": false
}
\`\`\`

Repository mode is an explicit trusted statement, **not** the \`visibility\`
frontmatter field and not something an MCP caller may choose. An absent or
malformed capability file fails closed. Optional \`writable_record_ids\`
restricts which canonical IDs may be changed; moving a record that requires
backlink updates also needs \`update\` permission for each affected ID.
Running the service against a public checkout with its default-private create
is denied regardless of caller-supplied metadata. Use the explicit
\`--root\` checkout, \`--capability-file\` path, \`--branch\` (default main)
and optionally \`--remote\` arguments in the **trusted launch command**.
The workspace requires local Git, Python/PyYAML, Node and installed OKF staged
validation dependencies. A missing staged checker fails closed.

## CLI (JSON in, JSON out)

\`\`\`sh
python tools/agent/knowledge_cli.py \
  --root /path/to/trusted/repository \
  --capability-file /path/outside/repository/knowledge-capability.json \
  --request /path/to/command.json
\`\`\`

Use \`--request -\` for one JSON request from stdin. The command JSON contains
\`command\` and the exact fields from the W-01 contract. For example, to read:

\`\`\`json
{"command":"read","record_id":"123e4567-e89b-42d3-a456-426614174000"}
\`\`\`

A successful read yields \`record_id\`, \`path\`, \`content\`, \`version\`
(event UUID), and \`head\` (commit SHA). A mutation yields
\`status\`, \`record_id\`, \`event_id\`, \`operation_id\`, \`version\`, \`head\`,
\`record_url\`, \`event_url\`, \`diff_url\`, and \`publication: "pending"\`.
A committed retry with the same idempotency key returns the original receipt.
Structured errors contain \`code\`, \`message\`, \`field_errors\`, and
\`retryable\`; no private snapshots are included. The CLI returns exit code 2
for domain errors, with one JSON object on stdout.

## stdio MCP

\`\`\`sh
python tools/agent/mcp_server.py \
  --root /path/to/trusted/repository \
  --capability-file /path/outside/repository/knowledge-capability.json
\`\`\`

The process accepts **newline-delimited UTF-8 JSON-RPC 2.0** over stdin
and emits one JSON-RPC response per line on stdout. It does **not**
use HTTP Content-Length or host any HTTP endpoint. This is the standard
MCP stdio framing; embedded JSON string newlines are escaped.
It supports \`initialize\`, \`ping\`, \`tools/list\`, and \`tools/call\`,
plus no-response notifications. The six tools are:

- \`knowledge_read\` — ID read of current source and version
- \`knowledge_create\` — canonical creation
- \`knowledge_update\` — versioned source replacement
- \`knowledge_move\` — atomic move and authorized link repair
- \`knowledge_archive\` — status to deprecated, history retained
- \`knowledge_reopen\` — explicit status after archive

The \`tools/call\` arguments omit \`command\`; it is supplied by the trusted
tool dispatcher. Their remaining fields match the CLI request. Domain
errors produce MCP \`isError: true\` with the structured domain error
serialized as text content; malformed JSON-RPC produces a protocol error.
The server writes no non-JSON text to stdout and never accepts a capability
profile, repository path, or network identity from tool arguments.

**Provenance, not authentication:** \`actor.id\`, \`actor.kind\`, and
\`actor.label\` are supplied by the local caller. The event history labels
them as such and makes **no claim of remote verified identity**. Actual
third-party trusted agent-client onboarding is issue #40, not a passing
protocol test in #30.

## Migration / legacy boundary

The previous \`knowledge_publish\` MCP tool and Content-Length framing are
superseded; the new MCP server never imports \`tools/agent/publish.py\`.
That file remains a transitional **v0.2-only** journal writer and refuses
canonical v1 metadata. Do not run both source models as canonical publishers.
In the **separate reviewed M-04 migration/cutover**, inventory and migrate
all legacy records, disable the remaining v0.2 entrypoint, switch the builder
to native logs only, and deploy in the same atomic cutover commit. Nothing in
this protocol PR changes live legacy data, performs that migration, claims a
private hosting deployment or asserts real third-party agent integration.

## Validation

\`\`\`sh
python -m unittest discover -s tools/records -p 'test_*.py' -v
\`\`\`

\`test_transport_v1.py\` starts actual CLI and MCP subprocesses against
disposable Git repositories. For each of the six tools it validates the
domain semantics, real committed log/record/index bytes, retries across
independent process invocations, malformed JSON-RPC, stale references,
public-default-private denial and supplied actor provenance. The full
GitHub CI also executes staged OKF/native checks, Chromium and WebKit and
public-only export.
