# Record history

## Entry ca9918bc-c4a7-4d4d-befe-45d485a74ff8
```json
{
  "schema_version": 1,
  "id": "ca9918bc-c4a7-4d4d-befe-45d485a74ff8",
  "record_id": "5d1e098b-24fc-43c6-b2d5-d68237742559",
  "operation_id": "77b8e49b-02c9-4e53-907f-6d52b1ceddc4",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-19T20:56:15Z",
  "occurred_on": null,
  "occurred_at": null,
  "actor": {
    "id": "opencode-agent",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Create a public Archon routing status record",
  "path_before": null,
  "path_after": "openwiki/projects/archon-ai-stack-public.md",
  "before": null,
  "after": "---\nid: 5d1e098b-24fc-43c6-b2d5-d68237742559\nschema_version: 1\ntype: project\ntitle: Archon routing stack — public status\ndescription: \"Public snapshot of a local Archon, Pi and ExtremeRouter deployment: exact role ids, live acceptance results and open work.\"\nstatus: draft\nvisibility: public\ntags: [archon, pi, phoenix, gateway, routing]\nsources:\n  - resource: https://hub.docker.com/r/rsalmn/extremerouter\n    title: Container image tags\n  - resource: https://github.com/tempuku\n    title: Fork owner on GitHub\n---\n\n# Archon routing stack — public status\n\n**Snapshot: 2026-11-19.** A local orchestration stack runs workflows in Archon,\nexecutes model turns through Pi, and selects providers through a derived\nExtremeRouter gateway build. Phoenix tracing is planned but not running. The\ndeployment is loopback-only and lives outside GitHub; this note is a manual\nsnapshot, not a live status feed.\n\n## Running now\n\n| Item | Value |\n| --- | --- |\n| Gateway container | running, private restart policy, loopback `127.0.0.1:20128` |\n| Anonymous API access | rejected with HTTP 401 |\n| Image | derived `0.9.0-t03c1` (`sha256:7b70e917…c5351e`) |\n| Role combos | five exact ids — `archon-triage`, `archon-policy`, `archon-planner`, `archon-coder`, `archon-reviewer` — plus short compatibility names |\n| Strategy | single working lane (OpenCode Go) first, fallback second |\n| Router key | one restricted key, 48 model ids, no earlier entry removed |\n| Pi | provider pointed at the local gateway; catalog includes the five exact role ids |\n| Telemetry | usage metadata only; raw prompt/response logging disabled |\n| Phoenix | not deployed; pinned plan and compose draft only |\n\n## Acceptance\n\n| ID | Status | Note |\n| --- | --- | --- |\n| A01 | PASS | direct baseline preserved before and after deployment |\n| A02 | PASS | loopback-only, authenticated, rotated password, private state |\n| A03 | PASS | live stream, JSON object mode, enforced JSON schema, real Pi tool round-trip |\n| A04 | PARTIAL | exact ids exist and `archon-coder` ran live; cross-turn attribution unproven |\n| A05 | UNVERIFIED | offline reference harness passes 10/10 mock cases; live wiring not done |\n| A06 | UNVERIFIED | no controlled 429/timeout drill with a recorded event |\n| A07 | UNVERIFIED | no enforced paid-budget cap |\n| A08–A11 | UNVERIFIED | Phoenix not deployed; no trace or privacy canary |\n| A12 | UNVERIFIED | no OmniRoute-compatible adapter |\n| A13 | PARTIAL | backups and rollback scripts exist; live outage drill not run |\n| A14 | UNVERIFIED | restart persistence not tested |\n\n## Recent verified work\n\n- Exact logical role ids created and wired into the key ACL and Pi catalog;\n  the short names remain for compatibility.\n- One isolated request through `archon-coder` returned the expected token in\n  about 2.5 s, with a clean regression on the direct model id.\n- Live protocol checks through the running gateway: server-sent events,\n  structured JSON, a schema contradiction control, and a real Pi `read` tool\n  call in an isolated Archon home.\n- Offline A05 reference adapter and tests: resolve-once behaviour, ten-process\n  race, recorded transport hop, mid-stream and mid-tool-use denial, TTL expiry,\n  and silent model-change detection (10/10 cases, 47/47 assertions).\n- A versioned routing-policy example, a stdlib validator, a four-check live\n  smoke script, and a pinned Phoenix deployment plan.\n\n## Open work\n\n1. Wire the A05 adapter into the real dispatch path and prove it live.\n2. Force a retryable failure and prove one recorded failover hop (A06).\n3. Define and enforce a paid-budget cap with retry and concurrency coverage (A07).\n4. Deploy Phoenix privately, verify auth and retention, add trace hierarchy and\n   privacy canaries, and keep export non-blocking (A08–A11).\n5. Add a mock OmniRoute-compatible adapter, run an approved outage drill, and\n   prove restart persistence (A12–A14).\n6. Obtain provider credentials with real quota; file presence alone is not\n   evidence of usable rights.\n\n## Operational hazards\n\n- The working upstream intermittently returns a Cloudflare HTML 403 that the\n  gateway caches as a per-model lock. While locked, combos fall through to a\n  quota-exhausted second lane, so the surfaced error can hide the real cause.\n  Retry after a bounded cooldown.\n- The Go lane requires a per-request session header; a missing header returns\n  400 before dispatch.\n- Do not enable no-auth or free providers until the fallback loop bug is fixed.\n- The routing policy is a contract, not an enforcement engine.\n- Live edits require a fresh private backup and a tested rollback path.\n\n## Evidence\n\nImplementation root: `/Users/tempuku/Documents/Codex/2026-11-19/archon-stack-luna-implementation`.\n\n- `docs/AI-STACK-STATE.md`, `docs/AI-STACK-ACCEPTANCE.md`\n- `outputs/P1-A03-LIVE.md`, `outputs/A05-STICKINESS.md`\n- `work/live/ARCHON-ROLES.md`, `work/live/archon-roles-live-test.json`\n- `config/archon-router-policy.example.yaml`, `docs/ROUTER-POLICY.md`\n- `docs/PHOENIX-PLAN.md`, `deploy/ai-stack/compose.phoenix.yaml`\n\n**Privacy:** this repository is public; the note contains no credentials,\nprompts, payloads or private project data.\n",
  "before_sha256": null,
  "after_sha256": "e9c51b6c578ade7e0cad17730c7430472b48079b4ba3759cb95c6b17c518cb04",
  "previous_event_id": null,
  "idempotency_key": "37f3b3b4-4a88-4747-abbe-c41d2625f303",
  "request_sha256": "368dbb908a657c5fd81ae71b0dc43c914c1dff4aa41ebb12afa1751009bf4d1a",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
