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

**Snapshot: 2026-11-20.** A local orchestration stack runs workflows in Archon,
executes model turns through Pi, and selects providers through a derived
ExtremeRouter gateway build. Phoenix stores traces from the real Archon and Pi
path. The
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
| Router key | one restricted key, 48 model ids, no earlier entry removed |
| Pi | provider pointed at the local gateway; catalog includes the five exact role ids |
| Telemetry | usage metadata only; raw prompt/response logging disabled |
| Phoenix | deployed `21.2.1` (`sha256:becd0809…c749e`), loopback `127.0.0.1:6006`/`:4317`, SQLite, 30-day retention, auth required |

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
| A04 | PARTIAL | exact ids exist and `archon-coder` ran live; cross-turn attribution unproven |
| A05 | PARTIAL | live pin per workflow/task/role/attempt; turn reuse, new attempt, real run ID, regression and store-across-restart pass; live forced hop deferred to real 429 observations |
| A06 | UNVERIFIED | no controlled 429/timeout drill with a recorded event |
| A07 | UNVERIFIED | no enforced paid-budget cap |
| A08–A11 | PASS | pinned/private Phoenix; anonymous API/OTLP rejected; 30-day retention; full trace hierarchy; canaries clean; PASS vs deliberate FAIL visible |
| A12 | UNVERIFIED | no OmniRoute-compatible adapter |
| A13 | PARTIAL | backups and rollback scripts exist; live outage drill not run |
| A14 | UNVERIFIED | restart persistence not tested |

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

## Open work

1. A05: keep Option A (reassign on a recorded pre-stream hop) and watch real
   `429` events before revisiting the hybrid. Do not force a live failure.
2. Force a retryable failure and prove one recorded failover hop (A06).
3. Define and enforce a paid-budget cap with retry and concurrency coverage (A07).
4. Add a mock OmniRoute-compatible adapter, run an approved outage drill, and
   prove restart persistence (A12–A14).
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

**Privacy:** this repository is public; the note contains no credentials,
prompts, payloads or private project data.
