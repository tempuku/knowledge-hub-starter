---
id: 5d1e098b-24fc-43c6-b2d5-d68237742559
schema_version: 1
type: project
title: Archon routing stack — public status
description: "Public snapshot of a local Archon, Pi and ExtremeRouter deployment: exact role ids, live acceptance results and open work."
status: draft
visibility: public
tags: [archon, pi, phoenix, gateway, routing]
sources:
  - resource: https://hub.docker.com/r/rsalmn/extremerouter
    title: Container image tags
  - resource: https://github.com/tempuku
    title: Fork owner on GitHub
---

# Archon routing stack — public status

**Snapshot: 2026-11-21.** A local orchestration stack runs workflows in Archon,
executes model turns through Pi, and selects providers through a derived
ExtremeRouter gateway build. Phoenix stores traces from the real Archon and Pi
path. A deterministic role evaluation and the Phase 5 migration-readiness
drills are recorded below. The
deployment is loopback-only and lives outside GitHub; this note is a manual
snapshot, not a live status feed.

## Running now

| Item | Value |
| --- | --- |
| Gateway container | running, private restart policy, loopback `127.0.0.1:20128` |
| Anonymous API access | rejected with HTTP 401 |
| Image | derived `0.9.0-a05` (`sha256:88b52296…c749cc`); rollback pin `0.9.0-t03c1` |
| Role combos | five exact ids — `archon-triage`, `archon-policy`, `archon-planner`, `archon-coder`, `archon-reviewer` — plus short compatibility names |
| Strategy | single working lane (OpenCode Go) first, fallback second |
| Router direction | ExtremeRouter is the live gateway; OmniRoute is **not installed**. A12 is a local dry-run portability test, not a swap decision. |
| Router key | one restricted key, 48 model ids, no earlier entry removed |
| Pi | provider pointed at the local gateway; catalog includes the five exact role ids |
| Telemetry | usage metadata only; raw prompt/response logging disabled |
| Phoenix | deployed `21.2.1` (`sha256:becd0809…c749e`), loopback `127.0.0.1:6006`/`:4317`, SQLite, 30-day retention, auth required |
| Budget ledger | adapter-scope cumulative monthly/per-task cap; live gateway still enforces only the per-request cap |

## Task-scoped stickiness (A05)

- Identity: Archon passes `ARCHON_NODE_EXECUTION` to the Pi subprocess; a Pi
  extension emits `x-archon-workflow-id`, `x-archon-task-id` and
  `x-archon-attempt`, and the role is the requested model id.
- The gateway resolves the combo once per `(workflow_id, task_id, role,
  attempt)`, stores assignments and hop/denial events in
  `router-stickiness.sqlite`, reuses the pin on later turns, and exposes
  `x-archon-pinned-model`, `x-archon-sticky-reused` and `x-archon-sticky-hops`.
- A transport failure may hop and records the event; streaming and mid-tool-use
  requests are denied a hop. Non-sticky roles bypass the store.
- Deployed on image `0.9.0-a05`. A gateway restart preserved every assignment
  row and the pin, and service returned authenticated. Backup and rollback
  verified: `~/.local/state/archon-ai-stack/backups/20261119T213839Z-gateway-pre-a05`.
- Policy is Option A; the hybrid target and the staged deployment-wave plan are
  in [ADR 0002](record:2b29dfb1-03e1-47ac-b0a9-c5b9427d3a88) and
  [ADR 0003](record:58a76581-d05f-4883-93bb-c2dd5981729d).

## Phoenix tracing (A08–A11)

- Pinned `arizephoenix/phoenix:21.2.1@sha256:becd0809…c749e` (the image id
  equals the index digest), loopback `127.0.0.1:6006` and `127.0.0.1:4317`
  only, `restart=unless-stopped`.
- Auth required: anonymous `/v1/projects`, GraphQL and OTLP/HTTP return 401;
  OTLP/gRPC returns `UNAUTHENTICATED`; authenticated API and ingest return
  200. JSON OTLP is 415 by design.
- SQLite on a private 0700 state root with a 30-day retention policy; a
  restart and a tested backup/restore preserved all spans.
- One real trace links `archon.workflow → archon.task (role) → archon.pi.run →
  archon.pi.turn → llm.request + archon.tool → archon.validation` across the
  wrapper and Pi processes via a W3C traceparent.
- Synthetic canaries in the prompt, tool path, tool output and validation
  error did not appear in Phoenix; one deliberate control attribute proved the
  search. Raw content logging is off; tool arguments/results and error
  messages are never exported.
- Export is asynchronous and bounded; stopping or killing Phoenix mid-run left
  inference successful and only dropped spans.
- A PASS and a deliberately failing run share the same stable workflow and task
  identifiers; PASS shows validation PASS, FAIL shows `ValidationError` /
  `exec_failed`.

## Acceptance

| ID | Status | Note |
| --- | --- | --- |
| A01 | PASS | direct baseline preserved before and after deployment |
| A02 | PASS | loopback-only, authenticated, rotated password, private state |
| A03 | PASS | live stream, JSON object mode, enforced JSON schema, real Pi tool round-trip |
| A04 | PASS | five-role live matrix through the real Archon → Pi → gateway path; each exact id returned its token and recorded the upstream model |
| A05 | PASS | live identity extension installed with rollback; two-turn reuse reports `reused: true`, a new attempt re-resolves, and a real Archon tool round-trip keys the store by run id; live forced hop deliberately untested |
| A06 | PASS | disposable compiled route: forced 429 records exactly one hop to the approved member; streaming, tool-context and single-member cases deny without an unauthorized fallback |
| A07 | PASS | per-request cost cap fails closed; a cumulative monthly/per-task ledger is implemented and tested behind the local adapter (13/13 tests, disposable drill PASS). Live gateway enforcement is not deployed |
| A08–A11 | PASS | pinned/private Phoenix; anonymous API/OTLP rejected; 30-day retention; full trace hierarchy; canaries clean; PASS vs deliberate FAIL visible |
| A12 | PASS | ExtremeRouter remains live; no OmniRoute installed. A local OmniRoute-compatible dry-run adapter served the five aliases, and the same workflow passed directly and through it with unchanged hashes |
| A13 | PASS | approved 2.19 s gateway outage: safe failure, no usage row, exact token after restore with the task id preserved |
| A14 | PASS | combined gateway + Phoenix restart 6.27 s: providers, combos, ACL, stickiness, spans and evaluation history persist; both smokes pass |

## Recent verified work

- Exact logical role ids created and wired into the key ACL and Pi catalog;
  the short names remain for compatibility.
- One isolated request through `archon-coder` returned the expected token in
  about 2.5 s, with a clean regression on the direct model id.
- Live protocol checks through the running gateway: server-sent events,
  structured JSON, a schema contradiction control, and a real Pi `read` tool
  call in an isolated Archon home.
- Offline A05 reference adapter and tests: resolve-once behaviour, ten-process
  race, recorded transport hop, mid-stream and mid-tool-use denial, TTL expiry,
  and silent model-change detection (10/10 cases, 47/47 assertions).
- Task-scoped stickiness is deployed on the gateway (image `0.9.0-a05`): two
  turns of one attempt reuse the pinned model, a new attempt re-resolves, a
  real Archon run ID keys the store, and the compiled route proves a forced
  429 hop, concurrency and streaming/tool-context denials.
- A versioned routing-policy example, a stdlib validator, a four-check live
  smoke script, and a private Phoenix deployment.
- Phoenix `21.2.1` is deployed and verified: loopback-only, authenticated API
  and OTLP, SQLite retention, restart and tested backup/restore, cross-process
  trace hierarchy, privacy canaries, and non-blocking export.

## Role evaluation and migration readiness (2026-11-20)

- Five-role live matrix through the real Archon → Pi → gateway path: every exact
  alias returned its expected token and recorded
  `opencode-go/deepseek-v4.1-flash`. The live Pi identity extension
  `archon-identity.ts` was installed with a tested rollback; two turns of one
  attempt report `x-archon-sticky-reused: true` and a new attempt re-resolves.
- Deterministic Phase 4 fixtures — triage JSON, planner structure, coding write
  plus external test, reviewer defect set and rate-limit recovery — all passed
  without an LLM judge. Measured cost was $0.00268881 for four validated tasks
  ($0.00067220 per validated success). Stable assignment produced one row;
  per-task rotation produced three.
- A12: a local OmniRoute-compatible dry-run adapter served the five aliases;
  the same workflow passed directly and through the adapter with unchanged
  workflow and Archon config hashes.
- A13: an approved gateway outage lasted 2.19 s; the same workflow failed
  safely with no usage row, then returned the exact token after restore with
  the task id preserved.
- A14: a combined gateway + Phoenix restart lasted 6.27 s; providers, combos,
  key ACL, stickiness rows, Phoenix spans and evaluation history persisted, and
  both smoke scripts passed.
- A07 residual: a cumulative monthly/per-task paid ledger is implemented at
  the adapter enforcement point; 13/13 unit tests and a disposable drill pass,
  with zero post-denial upstream calls. The live gateway still enforces only
  the per-request cap. Write-up: `outputs/A07-LEDGER.md`.
- Still open: a live forced 429 hop (deliberate), live gateway ledger
  enforcement (owner decision), an optional real OmniRoute trial (owner
  authorization required), and a second usable provider family for reviewer
  independence.

## Router direction (A12 clarification)

- ExtremeRouter is the installed, live gateway. OmniRoute appears only in the
  A12 router-independence criterion: the five `archon-*` aliases must survive a
  backend swap with no Archon role, DAG, acceptance or history edits.
- A12 was proven with a local OpenAI-compatible **dry-run adapter**, not by
  installing OmniRoute. The adapter forwards the aliases to the live gateway;
  the workflow and Archon config stay byte-identical.
- A real OmniRoute trial is optional future work. It requires explicit owner
  authorization, must start in a disposable environment, and must not replace
  the live gateway before the swap is proven.
- Current next-step handoff: `outputs/NEXT-AGENT-AFTER-PHASE5.md`.

## Open work

1. Keep Option A (reassign on a recorded pre-stream hop); the live forced hop
   stays intentionally untested. Watch real `429` events.
2. Decide whether to enforce the tested cumulative ledger live: route inference through the adapter or port the ledger into the gateway. The live gateway still enforces only the per-request cap.
3. Install and validate a real OmniRoute backend only with owner authorization;
   A12 currently uses a local dry-run adapter.
4. Obtain a second usable provider family for reviewer independence and
   multi-model comparison.
5. Obtain provider credentials with real quota; file presence alone is not
   evidence of usable rights.

## Operational hazards

- The working upstream intermittently returns a Cloudflare HTML 403 that the
  gateway caches as a per-model lock. While locked, combos fall through to a
  quota-exhausted second lane, so the surfaced error can hide the real cause.
  Retry after a bounded cooldown.
- The Go lane requires a per-request session header; a missing header returns
  400 before dispatch.
- Do not enable no-auth or free providers until the fallback loop bug is fixed.
- The routing policy is a contract, not an enforcement engine.
- Live edits require a fresh private backup and a tested rollback path.

## Evidence

Implementation root: `/Users/tempuku/Documents/Codex/2026-11-19/archon-stack-luna-implementation`.

- `docs/AI-STACK-STATE.md`, `docs/AI-STACK-ACCEPTANCE.md`
- `outputs/P1-A03-LIVE.md`, `outputs/A05-STICKINESS.md`,
  `work/a05/live-a05-results.json`, `work/a05/harness/sticky-route-proof-a05.json`
- `work/live/ARCHON-ROLES.md`, `work/live/archon-roles-live-test.json`
- `config/archon-router-policy.example.yaml`, `docs/ROUTER-POLICY.md`
- `docs/PHOENIX-PLAN.md`, `deploy/ai-stack/compose.phoenix.yaml`
- `outputs/A08-A11-PHOENIX.md`,
  `docs/evidence/phoenix-a08-a11-verification.json`,
  `docs/evidence/phoenix-synthetic-trace.json`
- `scripts/archon-trace.py`, `scripts/smoke-archon-traces.sh`,
  `deploy/ai-stack/pi-extension/archon-trace.ts`
- `outputs/PHASE2-RECONCILIATION.md`, `outputs/PHASE4-EVALUATION.md`,
  `outputs/PHASE5-MIGRATION.md`
- `work/phase2/a04-live-matrix.json`, `work/phase2/a05-live-results.json`,
  `work/phase2/harness/sticky-route-proof-phase2.json`
- `work/eval/results/`, `work/phase5/results/`
- `outputs/A07-LEDGER.md`, `work/phase5/budget/`
- `outputs/NEXT-AGENT-AFTER-PHASE5.md`

**Privacy:** this repository is public; the note contains no credentials,
prompts, payloads or private project data.
