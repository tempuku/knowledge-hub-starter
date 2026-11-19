# Issue #40 — real stdio MCP client smoke (disposable Git)

Scope: [#40](https://github.com/tempuku/knowledge-hub-starter/issues/40)
under [#24](https://github.com/tempuku/knowledge-hub-starter/issues/24).
The v1 source writer and six tools are supplied by completed [#30](https://github.com/tempuku/knowledge-hub-starter/issues/30).
This verifies a **real official MCP Python SDK client**, not the previous
handcrafted JSON-RPC subprocess test. No hosted gateway, language-model
inference, external/private Git checkout or production cutover is involved.

## Trust boundary and client onboarding

**Never point a newly configured client at a private production repository
until it has been exercised with a disposable checkout.** Python, Git, Node,
the pinned staged OKF checker, and the local client application are needed.

Example of a disposable checkout and explicit external capability profile:

```sh
# Run from the Knowledge Hub repository root.
KH_SOURCE="$PWD"
KH_SANDBOX="$(mktemp -d)"
git init -q -b main "$KH_SANDBOX/sandbox"
git -C "$KH_SANDBOX/sandbox" config user.name 'Synthetic client'
git -C "$KH_SANDBOX/sandbox" config user.email 'synthetic@example.invalid'
mkdir -p "$KH_SANDBOX/sandbox/openwiki"
printf '%s\n' '---' 'okf_version: "0.2"' '---' '' '# Synthetic' '' > "$KH_SANDBOX/sandbox/openwiki/index.md"
git -C "$KH_SANDBOX/sandbox" add -A
git -C "$KH_SANDBOX/sandbox" commit -qm 'initial'
printf '%s\n' '{"repository_mode":"private","operations":["read","create","update"],"publisher_scope":false}' > "$KH_SANDBOX/client-capability.json"
```

**Codex CLI** is an example of a real agent application that can launch the
same stdio server. The following is a *setup example*, not a claim that a Codex
model session ran in CI:

```sh
codex mcp add knowledge-hub-local -- \
  python3 "$KH_SOURCE/tools/agent/mcp_server.py" \
  --root "$KH_SANDBOX/sandbox" \
  --capability-file "$KH_SANDBOX/client-capability.json"
codex mcp list
```

Open Codex and inspect `/mcp` for `knowledge_read`, `knowledge_create`
and `knowledge_update` (also `knowledge_move`, `knowledge_archive`,
`knowledge_reopen` if granted). Use the agent in this *disposable checkout*
only. The CLI handles tool schema discovery, but authorization comes from
the launch capability file — not model-supplied arguments. A client cannot
claim a trusted identity by passing `actor`: it is unauthenticated provenance.
MCP history is not a seventh tool; read the sibling `.log.md` through the
trusted local Git checkout when reviewing event history.

## Reproducible, automated **real client** evidence

From a repository checkout with its staged OKF dependencies already installed:

```sh
sh tools/okf/setup.sh
python -m pip install -r tools/diary/requirements.txt
python -m pip install 'mcp==1.30.0'
KH_ISSUE40_REPORT=/tmp/issue40-client-smoke.json \
  python -m unittest discover -s tests -p 'test_issue40_mcp_client.py' -v
```

`tests/test_issue40_mcp_client.py` launches the real server via
`mcp.client.stdio.stdio_client`, negotiates the protocol with
`mcp.ClientSession.initialize`, queries `list_tools` and executes
`call_tool` for all changes. It uses a fresh Git fixture and an external
capability file, never an actual personal record.

| Acceptance | Exact observation checked |
| --- | --- |
| Real client discovery | The official SDK initializes the process and discovers exactly six tools |
| Read → write → read/history | MCP create/read/update/read; parse the two persisted `CREATED`/`UPDATED` entries from `git show` of the native sibling log |
| Idempotent retry | Replay the exact MCP update request; receipt is `already_committed` with the original event, version and HEAD; no new commit |
| Stale version | MCP update using the original version returns `CONFLICT`, preserving HEAD |
| Insufficient write permission | A separately launched, read-only SDK session rejects MCP update with `PUBLICATION_DENIED`, but permits read |
| Integrity and privacy | Native index/history validation succeeds; capability file stays outside Git; report excludes content, paths and credentials |
| CI | Required `validate-openwiki` runs this SDK client and publishes a sanitized `issue40-real-mcp-client-smoke` artifact |

The public CI evidence is the `issue40-real-mcp-client-smoke` artifact of the
successful `validate-openwiki` workflow run **on the exact merged
implementation commit**. The artifact contains an ordered result transcript
and disposable Git HEAD, without record body or private fields. A passing unit
test before CI is not proof of a passing current-head required gate.

## Deliberate exclusions

- No real model-driven Codex/Claude session has been executed by this test;
  the real client is the official Python MCP SDK. A future optional interactive
  agent check can be added without holding this lightweight onboarding gate.
- No remote hosted authentication, internet endpoint, private data, source
  migration, publication cutover, move/archive/reopen demonstration or
  exhaustive scenario matrix is claimed.
- The current six-tool MCP contract has `knowledge_read` but no
  `knowledge_history` tool. The smoke verifies **committed native history**
  through the trusted Git checkout, rather than inventing a history MCP API.
- Caller-supplied actor labels are **not** identity attestation. Source commits
  have `publication: pending` until separately published and verified.
