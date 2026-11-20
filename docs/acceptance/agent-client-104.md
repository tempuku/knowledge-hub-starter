# Issue #104 — OpenCode V2 global MCP onboarding and discovery

Scope: [#104](https://github.com/tempuku/knowledge-hub-starter/issues/104) under
[#24](https://github.com/tempuku/knowledge-hub-starter/issues/24): one concrete client,
**OpenCode V2 on macOS**, plus the discovery tools added beside the original six. It
builds on [agent-client-40.md](agent-client-40.md) and the writer from
[#30](https://github.com/tempuku/knowledge-hub-starter/issues/30). No hosted gateway,
remote authentication, production repository or write session is involved.

## Verification status

**Owner-verified at `8464beb` (OpenCode v2.2.7, macOS):** a global `knowledge-hub-local`
server launched from a virtual environment outside the checkout connects from three
working directories, including one outside the checkout, with no per-project
configuration. `opencode mcp list` reports `✓ knowledge-hub-local connected`; the six
tools present at `8464beb` are discovered; a real agent session performed
`knowledge_read` for record `820d2f86-8f25-486d-afc0-214c5291f4bf`
(`openwiki/design/agent-workflow.md`, draft, version
`318d22ec-d804-47ae-8d68-405c21ded759`, head `8464beb`); no write ran.

**Pending, explicitly unverified:** live discovery of `knowledge_search` and
`knowledge_history` on a checkout containing this change (the session above predates
them), the model journey below, and every remote/HTTPS/OAuth/private
([#12](https://github.com/tempuku/knowledge-hub-starter/issues/12)) or
production-cutover ([#38](https://github.com/tempuku/knowledge-hub-starter/issues/38))
concern.

## Trust boundary and capability profile

**Never point a newly configured client at a private production repository until it has
been exercised with a disposable checkout.** Python, Git, Node and the pinned staged
checker are required. The read-only capability profile limits what the **local server**
will do; it is not a sandbox and does not restrict the process's filesystem access. The
`visibility` frontmatter field does **not** secure files in a public Git repository —
the public-mode filter below only constrains tool output. Absolute interpreter, script,
root and capability paths are mandatory for a global server, because its launch working
directory is arbitrary.

The trusted profile lives **outside** the checkout, e.g.
`~/.config/knowledge-hub/read-only.json`:

```json
{"repository_mode":"public","operations":["read"],"publisher_scope":false}
```

An absent, malformed or unknown profile fails closed. The operation vocabulary is
unchanged: `read`, `create`, `update`, `move`, `archive`, `reopen`. There are no `search`
or `history` operations; `read` grants `read`, `search` and `history` together. Listing a
new name in `operations` is a configuration error, not a higher permission.

## Register globally and verify

```sh
KH="$HOME/Downloads/knowledge-hub-starter"
VENV="$HOME/.local/share/knowledge-hub/venv"
opencode mcp add knowledge-hub-local --global -- \
  "$VENV/bin/python" "$KH/tools/agent/mcp_server.py" \
  --root "$KH" --capability-file "$HOME/.config/knowledge-hub/read-only.json"
opencode mcp list
```

This writes `mcp.servers.knowledge-hub-local` with `"type": "local"` to
`~/.config/opencode/opencode.json`. The interpreter must meet the documented Python
3.10+ requirement ([`pyproject.toml`](../../pyproject.toml),
[`README.md`](../../README.md)); the observed venv was Python 3.13.18 with PyYAML 6.0.3,
while system `python3` was 3.9.6 and therefore unusable.

After `opencode mcp add`, an immediate `opencode mcp list` showed no servers; a later
invocation showed the server connected without any restart. Treat that as observed
configuration/service reload lag, not a persistent failure. Discovery is independent of
permissions: all eight tools are listed even under a read-only profile, and writes then
fail with `PUBLICATION_DENIED`.

**Code Mode** is the OpenCode V2 default: tools are called inside `execute` as
`tools["knowledge-hub-local"].knowledge_search({...})`. Setting `"codemode": false` on
the server entry exposes them directly instead, at the cost of model context.

## Tool surface

| Tool | Required operation | Inputs | Returns |
| --- | --- | --- | --- |
| `knowledge_read` | `read` | `record_id` | `record_id`, `path`, `content`, `version`, `head` |
| `knowledge_search` | `read` | `query`, `limit?`, `include_archived?` | `query`, `head`, `total`, `count`, `results` |
| `knowledge_history` | `read` | `record_id`, `limit?`, `before_sequence?` | `record_id`, `path`, `title`, `status`, `head`, `total`, `next`, `events` |
| `knowledge_create` | `create` | `path`, `content`, common write fields | mutation receipt |
| `knowledge_update` | `update` | `record_id`, `expected_version`, `content` | mutation receipt |
| `knowledge_move` | `move` | `record_id`, `expected_version`, `destination` | mutation receipt |
| `knowledge_archive` | `archive` | `record_id`, `expected_version` | mutation receipt |
| `knowledge_reopen` | `reopen` | `record_id`, `expected_version`, `status` | mutation receipt |

Common write fields are `expected_head`, `idempotency_key`, `actor` (`id`, `kind`,
`label`) and `summary`, plus optional `occurred_on`/`occurred_at`; `actor` is supplied
provenance, never authenticated identity.

## Read contracts

`knowledge_search` accepts a non-empty query of at most 256 characters, at most
eight distinct tokens, and `limit` 1–25 (default 8). It tokenizes and ranks with
the P-03 primitives in
[`tools/projection/deterministic.py`](../../tools/projection/deterministic.py): AND
matching over title, description, tags and body. It scans the trusted checkout's
**current** v1 records — not history snapshots, and no remote index. Deprecated
records are excluded unless `include_archived: true`. `total` counts all matches;
`count` is the returned page size.

```json
{"query":"publication decision","limit":8,"include_archived":false}
{"query":"publication decision","head":"<sha>","total":2,"count":2,
 "results":[{"record_id":"<uuid>","path":"…","title":"…","status":"draft"}]}
```

`knowledge_history` returns newest first, at most 50 events per page (default 20);
`next` is the last returned sequence and is the cursor for the next older page,
passed as `before_sequence`. `total` counts all events eligible in this view,
before the cursor. It returns event **metadata** plus `record_url` (the record
path) and `event_url` (the native sibling log with an `#<event-id>` fragment) —
never `before`/`after` snapshots, hashes or bodies. Invalid requests and
out-of-boundary records yield structured domain errors.

```json
{"record_id":"<uuid>","limit":20,"before_sequence":null}
{"record_id":"<uuid>","path":"…","title":"…","status":"draft","head":"<sha>",
 "total":3,"next":null,
 "events":[{"event_id":"<uuid>","sequence":3,"action":"UPDATED","recorded_at":"…",
            "summary":"…","occurred_on":null,"occurred_at":null,"actor_label":"…",
            "path_before":"…","path_after":"…","record_url":"…","event_url":"…"}]}
```

## Publication-scoped read boundary

In `repository_mode: "public"` all three reads are filtered to `visibility: public` at
the current record. `knowledge_read` of a non-public record returns `NOT_FOUND`, revealing
no existence; `knowledge_search` indexes and filters only public records, so matches,
totals and the returned set never reveal private records; `knowledge_history` requires a
public current record and omits any event whose after-snapshot is not public, treating an
unparseable snapshot as not public (fail-closed). This is the record `visibility` boundary
only — **not** the website's separate `config/publication.json` allowlist. There is no
allowlist parity: a record can be returned here while remaining unapproved for public
site publication, and an MCP result is not publication approval.

## Not claimed

No public-site allowlist parity or byte audit; no remote, HTTPS, OAuth, multi-user or
private authenticated endpoint ([#12](https://github.com/tempuku/knowledge-hub-starter/issues/12));
no write, idempotency or conflict proof from this onboarding (write is covered by
[agent-client-40.md](agent-client-40.md) against disposable Git); no production cutover,
source migration or deployed reader
([#38](https://github.com/tempuku/knowledge-hub-starter/issues/38)).

## Manual acceptance run (unverified)

Use the disposable checkout from [agent-client-40.md](agent-client-40.md) or a trusted
read-only checkout, start a fresh OpenCode session, and send exactly:

> Find the publication decision, tell me what changed most recently, and link me to the
> evidence.

Expected behaviour: `knowledge_search` locates the publication decision from the prompt
text alone, with no record UUID supplied; `knowledge_read` on the matched `record_id`
returns the canonical current source, version and head; `knowledge_history` for the same
record returns native sibling-log events and the answer names the most recent change from
event metadata; the answer surfaces the record path and native event link returned by
the tool (`record_url`, `event_url`), not a guessed path or commit SHA; and no write
tool is called. Record the checkout head, tool
arguments, returned `record_id`/`event_id` and whether each link resolved. Until then,
this journey is **unverified**; the owner-verified read above is not a model journey.

## Related evidence and source

Implemented in [`tools/agent/mcp_server.py`](../../tools/agent/mcp_server.py),
[`tools/agent/knowledge_service.py`](../../tools/agent/knowledge_service.py) and
[`tools/records/service_v1.py`](../../tools/records/service_v1.py); client notes in
[`tools/agent/README-v1.md`](../../tools/agent/README-v1.md).
