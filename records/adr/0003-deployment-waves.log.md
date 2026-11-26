# Record history

## Entry c809bd06-4f9b-461a-9479-bbf15320bc13
```json
{
  "schema_version": 1,
  "id": "c809bd06-4f9b-461a-9479-bbf15320bc13",
  "record_id": "58a76581-d05f-4883-93bb-c2dd5981729d",
  "operation_id": "742625fc-a8ca-4a21-8a05-a0593daf7bc4",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-19T22:03:50Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Record decision: ADR 0003 — Deployment waves and zero-downtime",
  "path_before": null,
  "path_after": "openwiki/adr/0003-deployment-waves.md",
  "before": null,
  "after": "---\nid: 58a76581-d05f-4883-93bb-c2dd5981729d\nschema_version: 1\ntype: decision\ntitle: \"ADR 0003 — Deployment waves and zero-downtime\"\ndescription: \"Blue/green, rolling and canary options for the local gateway, and why SQLite blocks multi-writer waves.\"\nstatus: draft\nvisibility: public\nproject_id: 5d1e098b-24fc-43c6-b2d5-d68237742559\ntags: [deployment, blue-green, kubernetes, canary, decision]\n---\n\n# ADR 0003 — Deployment strategy: blue/green, waves and zero-downtime\n\n- **Date:** 2026-11-19\n- **Decision status:** Proposed. Current deployment remains stop/start; brief\n  outage accepted.\n- **Scope:** gateway image/state rollout, restart handling and future\n  orchestrator choice.\n- **Related:** ADR 0002 (stickiness hop policy), `docs/AI-STACK-RUNBOOK.md`,\n  `deploy/ai-stack/compose.yaml`.\n\n## Context\n\nToday the gateway is a single Docker container on one host (Colima), bound to\n`127.0.0.1:20128`, `restart=no`, with private state on a bind mount\n(`~/.local/state/archon-ai-stack/gateway`): provider connections, combos, keys,\nusage history and the stickiness SQLite store.\n\nA deploy is a stop/start. The owner has accepted brief outages, but asked\nwhether Kubernetes-style wave/rolling deploys are possible next time.\n\nHard constraint: **SQLite is single-writer**. Two containers sharing the same\ndatabase file will corrupt it. True rolling/canary with multiple writers\nrequires moving persistence to a shared server database first.\n\n## Options\n\n| Option | Downtime | Writers | Complexity | Notes |\n|---|---|---|---|---|\n| A. Stop/start (today) | seconds | 1 | lowest | accepted; rollback by image pin |\n| B. Blue/green behind a local proxy | sub-second switch | 1 active | medium | green starts, passes probes, proxy flips; only one writer at a time |\n| C. Compose scale + proxy | near zero | 1 writer, N readers | medium-high | needs shared DB or read-only replicas |\n| D. k3s/kind Deployment + Service | zero | N | high | needs Postgres; probes, PDB, maxSurge/maxUnavailable |\n| E. Canary weights at the proxy | zero | N | high | 5% → 25% → 100%, automatic rollback on failed gates |\n\n## Recommendation (staged)\n\n**Phase 0 — now.** Keep stop/start, but make it disciplined:\n\n- add a `/healthz`-style check (or reuse authenticated `/api/settings` 401 as a\n  liveness signal) and a post-start smoke;\n- pre-build and verify the image before stopping the old one;\n- keep the verified rollback script and state snapshot;\n- measure the outage instead of guessing it.\n\n**Phase 1 — blue/green with a local proxy.** Put Caddy/nginx in front on\n`127.0.0.1:20128`, route to a backend port (`20128`/`20129`).\n\n1. Start green with a copy of state or the same mount after blue is stopped\n   (single writer).\n2. Wait for readiness (container running, 401 anonymous, authenticated admin\n   call, one bounded model call).\n3. Flip the proxy upstream; keep blue stopped for a fast rollback.\n4. Roll back by flipping the upstream back if any gate fails.\n\nThis removes image-start time from the outage window without a database change.\n\n**Phase 2 — shared Postgres.** Move provider/usage/stickiness state to Postgres.\nThen run two or more gateway replicas and do real rolling waves:\n\n- wave 1: canary (one replica), synthetic checks (401, auth, exact model token,\n  sticky reuse);\n- wave 2: 50%; wave 3: 100%;\n- hold-down between waves; automatic rollback on failed gate;\n- connection draining before removing a replica.\n\n**Phase 3 — optional k3s/kind.** Only after Phase 2. A single-node k3s with a\nDeployment, Service, PVC and probes gives `maxSurge`/`maxUnavailable` waves,\n`PodDisruptionBudget`, startup/readiness/liveness probes, and ingress-weighted\ncanaries. For one host and one service this is mostly operational overhead; it\nis justified if more services (Phoenix, adapters) join the stack.\n\n## Wave gate definition\n\nEvery wave must pass, in order:\n\n1. container/pod ready and bound to loopback only;\n2. anonymous `/api/settings` = 401;\n3. authenticated admin read succeeds;\n4. one bounded model call returns the expected token;\n5. one sticky reuse check (`x-archon-sticky-reused: true`);\n6. error rate and latency within the agreed window;\n7. rollback path still executable.\n\n## State rules\n\n- Never run two writers against SQLite.\n- Image rollback must not require a schema downgrade; migrations are additive\n  and old builds ignore new columns.\n- Back up state before any wave; keep the previous image pinned.\n- Secrets stay in private 0600 files; no secret enters logs or evidence.\n\n## Consequences\n\n- Blue/green is achievable now with a small proxy and no data migration.\n- Real rolling/canary is blocked on replacing SQLite, not on Kubernetes.\n- k3s is a later option, not a prerequisite.\n\n## Revisit triggers\n\n- a second service needs the same rollout path (Phoenix);\n- outage duration or user impact becomes unacceptable;\n- concurrent gateway replicas become necessary for throughput;\n- a real canary signal (latency/error) is needed for model or prompt changes.\n",
  "before_sha256": null,
  "after_sha256": "2c31b29e7ad93b3c1f501797354fac621397677da73b6b40b2a202376b152ced",
  "previous_event_id": null,
  "idempotency_key": "97036f53-e01e-4cb4-9d9a-6818388177bb",
  "request_sha256": "1e004aa0c8a927e649f3a9f8ef087d0dc771bd89a09feabdd8adc5a7036f2780",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
