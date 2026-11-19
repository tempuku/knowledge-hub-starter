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

**Snapshot: 2026-11-19.** A local orchestration stack runs workflows in Archon,
executes model turns through Pi, and selects providers through a derived
ExtremeRouter gateway build. Phoenix tracing is planned but not running. The
deployment is loopback-only and lives outside GitHub; this note is a manual
snapshot, not a live status feed.

## Running now

| Item | Value |
| --- | --- |
| Gateway container | running, private restart policy, loopback `127.0.0.1:20128` |
| Anonymous API access | rejected with HTTP 401 |
| Image | derived `0.9.0-t03c1` (`sha256:7b70e917…c5351e`) |
| Role combos | five exact ids — `archon-triage`, `archon-policy`, `archon-planner`, `archon-coder`, `archon-reviewer` — plus short compatibility names |
| Strategy | single working lane (OpenCode Go) first, fallback second |
| Router key | one restricted key, 48 model ids, no earlier entry removed |
| Pi | provider pointed at the local gateway; catalog includes the five exact role ids |
| Telemetry | usage metadata only; raw prompt/response logging disabled |
| Phoenix | not deployed; pinned plan and compose draft only |

## Acceptance

| ID | Status | Note |
| --- | --- | --- |
| A01 | PASS | direct baseline preserved before and after deployment |
| A02 | PASS | loopback-only, authenticated, rotated password, private state |
| A03 | PASS | live stream, JSON object mode, enforced JSON schema, real Pi tool round-trip |
| A04 | PARTIAL | exact ids exist and `archon-coder` ran live; cross-turn attribution unproven |
| A05 | UNVERIFIED | offline reference harness passes 10/10 mock cases; live wiring not done |
| A06 | UNVERIFIED | no controlled 429/timeout drill with a recorded event |
| A07 | UNVERIFIED | no enforced paid-budget cap |
| A08–A11 | UNVERIFIED | Phoenix not deployed; no trace or privacy canary |
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
- A versioned routing-policy example, a stdlib validator, a four-check live
  smoke script, and a pinned Phoenix deployment plan.

## Open work

1. Wire the A05 adapter into the real dispatch path and prove it live.
2. Force a retryable failure and prove one recorded failover hop (A06).
3. Define and enforce a paid-budget cap with retry and concurrency coverage (A07).
4. Deploy Phoenix privately, verify auth and retention, add trace hierarchy and
   privacy canaries, and keep export non-blocking (A08–A11).
5. Add a mock OmniRoute-compatible adapter, run an approved outage drill, and
   prove restart persistence (A12–A14).
6. Obtain provider credentials with real quota; file presence alone is not
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
- `outputs/P1-A03-LIVE.md`, `outputs/A05-STICKINESS.md`
- `work/live/ARCHON-ROLES.md`, `work/live/archon-roles-live-test.json`
- `config/archon-router-policy.example.yaml`, `docs/ROUTER-POLICY.md`
- `docs/PHOENIX-PLAN.md`, `deploy/ai-stack/compose.phoenix.yaml`

**Privacy:** this repository is public; the note contains no credentials,
prompts, payloads or private project data.
