---
id: 58a76581-d05f-4883-93bb-c2dd5981729d
schema_version: 1
type: decision
title: "ADR 0003 — Deployment waves and zero-downtime"
description: "Blue/green, rolling and canary options for the local gateway, and why SQLite blocks multi-writer waves."
status: draft
visibility: public
project_id: 5d1e098b-24fc-43c6-b2d5-d68237742559
tags: [deployment, blue-green, kubernetes, canary, decision]
---

# ADR 0003 — Deployment strategy: blue/green, waves and zero-downtime

- **Date:** 2026-11-19
- **Decision status:** Proposed. Current deployment remains stop/start; brief
  outage accepted.
- **Scope:** gateway image/state rollout, restart handling and future
  orchestrator choice.
- **Related:** ADR 0002 (stickiness hop policy), `docs/AI-STACK-RUNBOOK.md`,
  `deploy/ai-stack/compose.yaml`.

## Context

Today the gateway is a single Docker container on one host (Colima), bound to
`127.0.0.1:20128`, `restart=no`, with private state on a bind mount
(`~/.local/state/archon-ai-stack/gateway`): provider connections, combos, keys,
usage history and the stickiness SQLite store.

A deploy is a stop/start. The owner has accepted brief outages, but asked
whether Kubernetes-style wave/rolling deploys are possible next time.

Hard constraint: **SQLite is single-writer**. Two containers sharing the same
database file will corrupt it. True rolling/canary with multiple writers
requires moving persistence to a shared server database first.

## Options

| Option | Downtime | Writers | Complexity | Notes |
|---|---|---|---|---|
| A. Stop/start (today) | seconds | 1 | lowest | accepted; rollback by image pin |
| B. Blue/green behind a local proxy | sub-second switch | 1 active | medium | green starts, passes probes, proxy flips; only one writer at a time |
| C. Compose scale + proxy | near zero | 1 writer, N readers | medium-high | needs shared DB or read-only replicas |
| D. k3s/kind Deployment + Service | zero | N | high | needs Postgres; probes, PDB, maxSurge/maxUnavailable |
| E. Canary weights at the proxy | zero | N | high | 5% → 25% → 100%, automatic rollback on failed gates |

## Recommendation (staged)

**Phase 0 — now.** Keep stop/start, but make it disciplined:

- add a `/healthz`-style check (or reuse authenticated `/api/settings` 401 as a
  liveness signal) and a post-start smoke;
- pre-build and verify the image before stopping the old one;
- keep the verified rollback script and state snapshot;
- measure the outage instead of guessing it.

**Phase 1 — blue/green with a local proxy.** Put Caddy/nginx in front on
`127.0.0.1:20128`, route to a backend port (`20128`/`20129`).

1. Start green with a copy of state or the same mount after blue is stopped
   (single writer).
2. Wait for readiness (container running, 401 anonymous, authenticated admin
   call, one bounded model call).
3. Flip the proxy upstream; keep blue stopped for a fast rollback.
4. Roll back by flipping the upstream back if any gate fails.

This removes image-start time from the outage window without a database change.

**Phase 2 — shared Postgres.** Move provider/usage/stickiness state to Postgres.
Then run two or more gateway replicas and do real rolling waves:

- wave 1: canary (one replica), synthetic checks (401, auth, exact model token,
  sticky reuse);
- wave 2: 50%; wave 3: 100%;
- hold-down between waves; automatic rollback on failed gate;
- connection draining before removing a replica.

**Phase 3 — optional k3s/kind.** Only after Phase 2. A single-node k3s with a
Deployment, Service, PVC and probes gives `maxSurge`/`maxUnavailable` waves,
`PodDisruptionBudget`, startup/readiness/liveness probes, and ingress-weighted
canaries. For one host and one service this is mostly operational overhead; it
is justified if more services (Phoenix, adapters) join the stack.

## Wave gate definition

Every wave must pass, in order:

1. container/pod ready and bound to loopback only;
2. anonymous `/api/settings` = 401;
3. authenticated admin read succeeds;
4. one bounded model call returns the expected token;
5. one sticky reuse check (`x-archon-sticky-reused: true`);
6. error rate and latency within the agreed window;
7. rollback path still executable.

## State rules

- Never run two writers against SQLite.
- Image rollback must not require a schema downgrade; migrations are additive
  and old builds ignore new columns.
- Back up state before any wave; keep the previous image pinned.
- Secrets stay in private 0600 files; no secret enters logs or evidence.

## Consequences

- Blue/green is achievable now with a small proxy and no data migration.
- Real rolling/canary is blocked on replacing SQLite, not on Kubernetes.
- k3s is a later option, not a prerequisite.

## Revisit triggers

- a second service needs the same rollout path (Phoenix);
- outage duration or user impact becomes unacceptable;
- concurrent gateway replicas become necessary for throughput;
- a real canary signal (latency/error) is needed for model or prompt changes.
