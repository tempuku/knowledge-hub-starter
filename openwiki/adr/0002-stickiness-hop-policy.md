---
id: 2b29dfb1-03e1-47ac-b0a9-c5b9427d3a88
schema_version: 1
type: decision
title: "ADR 0002 — Stickiness hop policy"
description: "Why the gateway reassigns a pinned model on a recorded pre-stream hop, and the planned hybrid."
status: draft
visibility: public
project_id: 5d1e098b-24fc-43c6-b2d5-d68237742559
tags: [archon, routing, stickiness, failover, decision]
---

# ADR 0002 — Stickiness hop policy

- **Date:** 2026-11-19
- **Decision status:** Accepted: Option A now. Hybrid is the proposed target.
- **Scope:** gateway task-scoped stickiness (A05) and controlled failover (A06).
- **Related:** `docs/A05-STICKINESS-DESIGN.md` (worktree), `config/archon-router-policy.example.yaml`, `docs/ROUTER-POLICY.md`.

## Context

A05 pins one concrete model per `(workflow_id, task_id, role, attempt)`. The
open question is what happens when the pinned member fails with a retryable
transport or quota error (`429`, `5xx`, timeout) before any response bytes are
delivered.

Two behaviours are possible:

- move the pin to the next approved member and continue the attempt;
- keep the pin and require a new attempt to rotate.

Only `archon-coder` is sticky in the policy. Reviewer independence and Gemini
quota are separate, unresolved constraints.

## Options

| | A — reassign on recorded hop | B — strict new attempt | Hybrid |
|---|---|---|---|
| Availability | best | worst | good |
| One model per attempt | no (splits after hop) | yes | yes after first turn |
| Attribution | join hop event | clean | clean except bootstrap |
| Work lost on a blip | none | whole attempt | none at bootstrap |
| Complexity | shipped | needs attempt retry | small addition to A |

## Decision

1. **Run Option A now.** A pre-stream retryable failure with no tool context
   writes one `hop` event, atomically moves the pin, retries once on the next
   approved member, and keeps later turns of that attempt on the new model.
   Streaming and mid-tool-use hops stay denied. Non-retryable 4xx never hops.
2. **Do not force a live 429 drill.** Real usage will exercise the path. Inspect
   `router_switch_events` and gateway usage history afterwards, then decide
   whether the observed behaviour is acceptable.
3. **Hybrid is the intended target**, recorded here rather than implemented now.

## Hybrid implementation plan (when approved)

**Store (additive migration, fail closed):**

- add `turns_completed INTEGER NOT NULL DEFAULT 0`
- add `emitted_output INTEGER NOT NULL DEFAULT 0`
- migration sets both to `1` for pre-existing pin rows, so old rows can never
  hop; new rows start at `0`
- increment `turns_completed` after a successful non-stream response or a
  completed stream; set `emitted_output=1` once any assistant content or tool
  call has been emitted

**Gate in `chat.js` (replaces the current pre-stream check):**

allow reassignment only when all hold:

1. pinned sticky role, approved fallback member exists;
2. retryable transport/quota failure;
3. no response bytes delivered and no tool context;
4. `turns_completed = 0` and `emitted_output = 0`;
5. fewer than `max_hops` (one) used;
6. not an authorization or budget denial.

Otherwise record `outcome=denied`, `reason=attempt_has_output` (or
`mid_stream` / `mid_tool_use`), leave the pin unchanged, and return the upstream
error.

**Rotation after denial:** the caller starts a new attempt. Archon's attempt id
is the rotation boundary; the adapter must not synthesise a new attempt silently.
If Archon does not retry automatically, the operator/agent retries explicitly.

**Tests to add:** first-call hop allowed; post-turn hop denied; post-tool hop
denied; new attempt re-resolves after denial; concurrency unchanged.

**Rollback:** image rollback is enough; the added columns are inert to the
previous build. Do not delete the store on rollback.

## Consequences

- Option A can mix two models inside one long attempt. That is recorded, but it
  is still a mid-task family change; evaluations must join the event.
- The hybrid removes that risk without failing a task on a first-call blip.
- Until the hybrid ships, A05 evidence must state “one model from the hop
  onward”, not “one model per attempt”.

## Revisit triggers

- first real `429` recorded in `router_switch_events`;
- any attempt with more than one hop;
- a mixed-model attempt with a failed validation;
- the A06 controlled-failover test;
- a second sticky role being enabled.

## Observing the real-usage path

```sh
# on the host, read-only
sqlite3 -readonly ~/.local/state/archon-ai-stack/gateway/data/router-stickiness.sqlite \
  "select recorded_at, workflow_id, task_id, role, attempt, trigger_class, from_model, to_model, outcome from router_switch_events order by recorded_at desc limit 20;"
```

Do not treat the intermittent Cloudflare `403` as a hop trigger: policy classes
it as non-retryable. That lock is an A06/runtime concern.
