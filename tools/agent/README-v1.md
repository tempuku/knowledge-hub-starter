# Knowledge Hub v1 trusted CLI and stdio MCP

This is the **source-facing v1 domain writer**, not a deployed remote server,
not an authenticated browser editor, and not a production migration.
All operations use `tools/records/service_v1.py` through the single
`tools/agent/knowledge_service.py` dispatch. There is no second canonical
writer or network listener.

## Trusted launch configuration

Prepare an external JSON file outside the Git checkout (do not commit it):

```json
{
  "repository_mode": "private",
  "operations": ["read", "create", "update", "move", "archive", "reopen"],
  "publisher_scope": false
}
```

Repository mode is an explicit trusted statement, **not** the `visibility`
frontmatter field and not something an MCP caller may choose. An absent or
malformed capability file fails closed. Optional `writable_record_ids`
restricts which canonical IDs may be changed; moving a record that requires
backlink updates also needs `update` permission for each affected ID.
Running the service against a public checkout with its default-private create
is denied regardless of caller-supplied metadata. Use the explicit
`--root` checkout, `--capability-file` path, `--branch` (default main)
and optionally `--remote` arguments in the **trusted launch command**.
The workspace requires local Git, Python/PyYAML, Node and installed OKF staged
validation dependencies. A missing staged checker fails closed.

The `operations` vocabulary stays the six operations shown above. There are no
`search` or `history` operations: `read` grants `knowledge_read`,
`knowledge_search` and `knowledge_history` together, and adding a new name to
`operations` is invalid configuration rather than a higher permission.

## CLI (JSON in, JSON out)

```sh
python tools/agent/knowledge_cli.py \
  --root /path/to/trusted/repository \
  --capability-file /path/outside/repository/knowledge-capability.json \
  --request /path/to/command.json
```

Use `--request -` for one JSON request from stdin. The command JSON contains
`command` and the exact fields from the W-01 contract, plus the read-only
`search`/`history` additions below. For example, to read:

```json
{"command":"read","record_id":"123e4567-e89b-42d3-a456-426614174000"}
```

A successful read yields `record_id`, `path`, `content`, `version`
(event UUID), and `head` (commit SHA). A mutation yields
`status`, `record_id`, `event_id`, `operation_id`, `version`, `head`,
`record_url`, `event_url`, `diff_url`, and `publication: "pending"`.
A committed retry with the same idempotency key returns the original receipt.
Structured errors contain `code`, `message`, `field_errors`, and
`retryable`; no private snapshots are included. The CLI returns exit code 2
for domain errors, with one JSON object on stdout.

Read-only discovery requests are also accepted:

```json
{"command":"search","query":"publication decision","limit":8,"include_archived":false}
{"command":"history","record_id":"123e4567-e89b-42d3-a456-426614174000","limit":20}
```

`search` takes a non-empty query of at most 256 characters with at most eight
distinct tokens, plus `limit` 1–25 (default 8). It matches current records by AND
over title, description, tags and body, and returns `query`, `head`, `total` (all
matches), `count` (returned page) and `results` entries of `record_id`, `path`,
`title` and `status`. Deprecated records appear only with
`include_archived: true`. `history` returns `total`, `next` and `events` newest
first, at most 50 per page (default 20), paging older with `before_sequence`;
each event carries `event_id`, `sequence`, `action`, `recorded_at`, `summary`,
`occurred_on`, `occurred_at`, `actor_label`, `path_before`, `path_after`,
`record_url` (record path) and `event_url` (native log plus `#event-id`). It
returns no `before`/`after` snapshot or hash.

## stdio MCP

```sh
python tools/agent/mcp_server.py \
  --root /path/to/trusted/repository \
  --capability-file /path/outside/repository/knowledge-capability.json
```

The process accepts **newline-delimited UTF-8 JSON-RPC 2.0** over stdin
and emits one JSON-RPC response per line on stdout. It does **not**
use HTTP Content-Length or host any HTTP endpoint. This is the standard
MCP stdio framing; embedded JSON string newlines are escaped.
It supports `initialize`, `ping`, `tools/list`, and `tools/call`,
plus no-response notifications. The eight tools are:

- `knowledge_read` — ID read of current source and version
- `knowledge_search` — token search over current records; `query`, optional
  `limit` (1–25, default 8) and `include_archived` (default false); returns
  `query`, `head`, `total`, `count`, `results`
- `knowledge_history` — per-record event metadata newest first; `record_id`,
  optional `limit` (1–50, default 20) and `before_sequence` cursor; returns
  `record_id`, `path`, `title`, `status`, `head`, `total`, `next`, `events`
- `knowledge_create` — canonical creation
- `knowledge_update` — versioned source replacement
- `knowledge_move` — atomic move and authorized link repair
- `knowledge_archive` — status to deprecated, history retained
- `knowledge_reopen` — explicit status after archive

`knowledge_search` reuses the P-03 tokenization and ranking primitives from
`tools/projection/deterministic.py`: at most eight distinct tokens, AND
matching, and ranking by field weight with deterministic tie-breaks. It scans
the trusted checkout's current v1 records only; there is no remote index and no
history-snapshot search. `knowledge_history` returns event metadata and relative
record/log links, never `before`/`after` snapshots, hashes or bodies.

In `repository_mode: "public"` both discovery tools apply the record
`visibility` boundary, fail-closed. Search indexes and filters only public
records, so matches, totals and results never reveal private records. History
requires a public current record and omits events whose after-snapshot is not
public; an unparseable snapshot counts as not public. This is the record
`visibility` field, **not** the website's `config/publication.json` allowlist:
the local MCP has no allowlist parity, and a result here is not publication
approval.

The `tools/call` arguments omit `command`; it is supplied by the trusted
tool dispatcher. Their remaining fields match the CLI request. Domain
errors produce MCP `isError: true` with the structured domain error
serialized as text content; malformed JSON-RPC produces a protocol error.
The server writes no non-JSON text to stdout and never accepts a capability
profile, repository path, or network identity from tool arguments.

**Provenance, not authentication:** `actor.id`, `actor.kind`, and
`actor.label` are supplied by the local caller. The event history labels
them as such and makes **no claim of remote verified identity**. Actual
trusted client SDK onboarding, disposable Git evidence, and a concrete Codex
setup example are documented in
[issue #40 acceptance](../../docs/acceptance/agent-client-40.md); global
OpenCode V2 registration and the discovery-tool contract are documented in
[issue #104 acceptance](../../docs/acceptance/agent-client-104.md).
The SDK client test does not claim a live model-driven Codex or Claude session,
remote identity verification, or production onboarding.

## Migration / legacy boundary

The previous `knowledge_publish` MCP tool and Content-Length framing are
superseded; the new MCP server never imports `tools/agent/publish.py`.
That file remains a transitional **v0.2-only** journal writer and refuses
canonical v1 metadata. Do not run both source models as canonical publishers.
In the **separate reviewed M-04 migration/cutover**, inventory and migrate
all legacy records, disable the remaining v0.2 entrypoint, switch the builder
to native logs only, and deploy in the same atomic cutover commit. Nothing in
this protocol PR changes live legacy data, performs that migration, claims a
private hosting deployment or asserts real third-party agent integration.

## Validation

```sh
python -m unittest discover -s tools/records -p 'test_*.py' -v
```

`test_transport_v1.py` starts actual CLI and MCP subprocesses against
disposable Git repositories. For each domain command it validates the
domain semantics, real committed log/record/index bytes, retries across
independent process invocations, malformed JSON-RPC, stale references,
public-default-private denial and supplied actor provenance. The separate [real SDK-client smoke test](../../tests/test_issue40_mcp_client.py)
uses the official MCP Python SDK ClientSession and uploads a sanitized CI
transcript; it verifies discovery, read/update, native Git history, stale
version, idempotent retry, and missing write permission.
The full
GitHub CI also executes staged OKF/native checks, Chromium and WebKit and
public-only export.
