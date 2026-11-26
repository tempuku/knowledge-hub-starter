---
id: 044e0d32-88d4-487f-a3e2-85232fa4722a
schema_version: 1
type: project
title: Archon AI stack (ExtremeRouter, Pi, Phoenix)
description: Local Archon/Pi/ExtremeRouter routing stack with exact role aliases; Phoenix planned, not deployed.
status: draft
visibility: private
tags: [archon, extreme-router, pi, phoenix, llm-routing, ai-infrastructure]
sources:
  - resource: https://github.com/tempuku/ExtremeRouter
    title: Derived gateway fork
  - resource: https://github.com/rsalmn/ExtremeRouter
    title: Upstream ExtremeRouter (v0.9.0 pin)
---

# Archon AI stack — routing and tracing

Local, private AI-orchestration stack: Archon orchestrates workflows, Pi executes
model turns, ExtremeRouter selects the provider/model, and Phoenix is intended to
store traces. The implementation checkout is local and not a GitHub repository;
this record is a **manual snapshot**, not an automatically synchronized status
feed. Recorded 2026-11-19 after the routing/role/acceptance session.

## Current live state (2026-11-19)

| Item | Value |
| --- | --- |
| Gateway | `archon-ai-stack-gateway-1`, running, `restart=no` |
| Image | derived `0.9.0-t03c1`, digest `sha256:7b70e917…c5351e`, from upstream pin `rsalmn/extremerouter@sha256:43310d9e…b076e8` |
| Binding | `127.0.0.1:20128` only; anonymous API access returns 401 |
| Provider lanes | OpenCode Go works; Gemini key has quota 0; ChatGPT/Codex is quota-limited |
| Role combos | `archon-triage`, `archon-policy`, `archon-planner`, `archon-coder`, `archon-reviewer` (plus compatibility short names), all Go-first with fallback |
| Router key | one restricted key; 48 allowed model ids, no prior entry removed |
| Pi | provider points at the local gateway; catalog contains the five exact role ids |
| Raw logging | off; usage metadata only |
| Phoenix | **not deployed**; pinned plan and compose draft only |

## Acceptance snapshot

| ID | Status | Note |
| --- | --- | --- |
| A01 | PASS | direct baseline preserved before and after deployment |
| A02 | PASS | loopback-only, authenticated, rotated password, private state |
| A03 | PASS | live SSE stream, JSON object mode, enforced JSON schema, real Pi tool round-trip |
| A04 | PARTIAL | exact aliases exist and `archon-coder` ran live; cross-turn assignment and model attribution unproven |
| A05 | UNVERIFIED | no `(workflow_id, task_id, role, attempt)` stickiness test |
| A06 | UNVERIFIED | fallback fires, but no controlled 429/timeout drill with a recorded event |
| A07 | UNVERIFIED | budget settings are advisory; no enforced paid cap |
| A08–A11 | UNVERIFIED | Phoenix not deployed; no trace, auth or privacy-canary evidence |
| A12 | UNVERIFIED | no OmniRoute-compatible adapter |
| A13 | PARTIAL | backups and rollback scripts exist; live outage drill not run |
| A14 | UNVERIFIED | restart persistence not tested |

## Work completed this session

- Created the five exact logical role combos and merged the router ACL without
  removing any existing model id; kept the short names for compatibility.
- Backed up and extended the live Pi catalog with the five role ids, then proved
  one isolated Archon/Pi request (`opencode-go/archon-coder` → `ARCHON_CODER_OK`,
  about 2.5 s) plus a regression on the direct alias.
- Closed live A03 through the running gateway: SSE stream, structured JSON,
  enforced schema (contradiction control), and a real Pi `read` tool round-trip
  in an isolated Archon home.
- Added a versioned, vendor-neutral routing-policy example with a stdlib
  validator, an operator document, and a four-check live smoke script.
- Added a pinned Phoenix deployment plan and compose draft without starting it.

Implementation commits: `7a4638d` and merge `79dafcf` (roles), `1716bcf`
(live A03, policy, validator, smoke), `30fa5ca` and `6b695dc` (policy/Phoenix
records). Evidence is kept in the local checkout; it is not published here.

## Next work, in order

1. **A05 stickiness** — resolve a role once per `(workflow_id, task_id, role,
   attempt)` and refuse to change model mid-stream or mid-tool-use.
2. **A06 failover** — force a retryable 429/timeout, allow exactly one hop,
   record role/from/to/class/attempt/latency.
3. **A07 budget** — define enforcement point, per-task and monthly caps,
   `on_exceed: deny`, and prove coverage of retries and concurrent calls. No paid
   setting may change without explicit owner authorization.
4. **Phoenix A08–A11** — private state dir, authenticated loopback deployment,
   retention, trace hierarchy, privacy canaries, and non-blocking export.
5. **A12–A14** — mock OmniRoute adapter, approved outage/bypass drill, restart
   persistence.
6. **Credentials** — Gemini needs a project with non-zero quota; ChatGPT needs a
   quota reset; free-tier provisioning needs real accounts. No key is inferred
   usable from file presence.

## Constraints and known pitfalls

- The OpenCode Go upstream intermittently returns a Cloudflare HTML 403 that the
  gateway caches as a per-model lock. While locked, combos fall through to
  Gemini, whose quota is 0, so the final error is a 429 that hides the 403.
  Retry after a bounded cooldown; it is not a routing defect.
- `x-opencode-session` is mandatory on the Go lane; a missing header returns 400
  before dispatch.
- Never enable no-auth/free providers until the fallback loop bug is fixed.
- Policy is a contract, not an enforcer: the gateway currently enforces member
  order and fallback only.
- Consumer-subscription proxying is an explicit owner override, not a
  brief-compliant default.
- Live edits require a fresh private backup plus a tested rollback path.

## Evidence and how to check

Local implementation root: `/Users/tempuku/Documents/Codex/2026-11-19/archon-stack-luna-implementation`.

- `docs/AI-STACK-STATE.md`, `docs/AI-STACK-ACCEPTANCE.md` — current snapshot and matrix.
- `outputs/P1-A03-LIVE.md` — live protocol proof and limitations.
- `work/live/ARCHON-ROLES.md` — role aliases, ACL, Pi backup, live result.
- `config/archon-router-policy.example.yaml`, `docs/ROUTER-POLICY.md`.
- `docs/PHOENIX-PLAN.md`, `deploy/ai-stack/compose.phoenix.yaml`.

Read-only verification from that root:

```sh
docker inspect archon-ai-stack-gateway-1 --format '{{.State.Status}} {{.Image}}'
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:20128/api/settings   # 401
bash scripts/smoke-gateway.sh
python3 scripts/validate-router-policy.py
```

**Privacy:** this Knowledge Hub source repository is public, so
`visibility: private` does not make this file confidential. It intentionally
contains no credentials, prompts, upstream payloads or private project data.

Superseded by the public status record [archon-ai-stack-public.md](../../records/projects/archon-ai-stack-public.md); retained for history.
