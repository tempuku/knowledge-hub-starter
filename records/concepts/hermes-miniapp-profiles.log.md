# Record history

## Entry 3bfff13c-f08c-4a45-b391-97412a7be0ee
```json
{
  "schema_version": 1,
  "id": "3bfff13c-f08c-4a45-b391-97412a7be0ee",
  "record_id": "44b0e133-ea13-4e61-a7f8-98a2af3a106b",
  "operation_id": "88f861ca-fe18-4499-bb50-3d49c411729c",
  "sequence": 1,
  "action": "CREATED",
  "recorded_at": "2026-11-26T18:23:00Z",
  "occurred_on": "2026-11-26",
  "occurred_at": null,
  "actor": {
    "id": "opencode:deepseek-v4.1-flash",
    "kind": "agent",
    "label": "OpenCode agent"
  },
  "summary": "Record multi-profile Mini App access options and keep the design in progress",
  "path_before": null,
  "path_after": "openwiki/concepts/hermes-miniapp-profiles.md",
  "before": null,
  "after": "---\nid: \"44b0e133-ea13-4e61-a7f8-98a2af3a106b\"\nschema_version: 1\ntype: \"concept\"\ntitle: \"Hermes Mini App — multi-profile access model\"\ndescription: \"Design discussion for serving archon-operator and other Hermes profiles\\\n  \\ from one Telegram Mini App, with authentication, isolation and implementation\\\n  \\ trade-offs.\"\nstatus: \"in_progress\"\nvisibility: \"public\"\ntags:\n  - \"hermes\"\n  - \"telegram\"\n  - \"miniapp\"\n  - \"profiles\"\n  - \"authentication\"\n  - \"archon\"\noccurred_on: \"2026-11-26\"\nsources:\n  - resource: \"record:023e7ae2-4677-4738-b8f2-be812cca6cf3\"\n    title: \"Agentic development management — Manager, Lead, Archon\"\n  - resource: \"record:5d1e098b-24fc-43c6-b2d5-d68237742559\"\n    title: \"Archon routing stack — public status\"\n  - resource: \"https://github.com/tempuku/archon-automation-pilot/issues/5\"\n    title: \"Issue #5 — Hermes owner Telegram access\"\n---\n\n# Hermes Mini App — multi-profile access model\n\n**Status:** in progress. This is a design discussion, not a deployed multi-profile feature. The live Mini App currently operates against the `archon-operator` profile.\n\n## What is true today\n\n- The Telegram Mini App plugin is installed in `archon-operator`, and the dashboard process on `127.0.0.1:9120` is launched with that profile.\n- The host also has the default Hermes profile, so Hermes enables multi-profile hosting. Under that mode, credential reads without an active profile scope fail closed.\n- Hermes accepts a dashboard-auth provider only from the **launch profile**. A provider registered from a secondary profile is ignored because dashboard auth belongs to the launch process.\n- The earlier \"auth provider unreachable\" failure was an unscoped secret read in the bearer-token middleware, not a missing bot token. A local fallback now binds the launch profile's own secret scope for that middleware path.\n- After login, the Mini App receives the dashboard session token. That token is **dashboard-wide**, not scoped to one profile.\n\n## Core constraint\n\nOne dashboard process has one login boundary. `?profile=<name>` can scope a plugin request, its secret scope and its session store to another served profile, but it does not create a second login or a second bot identity.\n\nA secondary profile that wants to serve plugin routes must have the plugin installed and enabled there. Hermes then runs that profile's copy in its own plugin host rather than importing it into the launch process.\n\n## Option A — one Mini App with a profile switcher\n\nOne bot, one owner, one menu button, with a selector for `archon-operator` and any other enabled profile.\n\nImplementation shape:\n\n1. Install and enable `telegram-app` in each participating profile.\n2. Keep `auth/verify` on the launch profile and obtain one dashboard session token.\n3. Send `?profile=<name>` on data calls such as sessions, status, logs, cron and knowledge.\n4. Add a profile selector to the Mini App UI and persist the selection.\n5. Restrict the accepted profile list in the proxy or plugin rather than allowing arbitrary names.\n\nWhat this buys:\n\n- one login and one menu button;\n- profile-scoped data and secrets;\n- no need to run a second tunnel or a second dashboard.\n\nWhat it does **not** buy:\n\n- separate owners or separate bot identities;\n- isolation between profiles. The session token is dashboard-wide, so the launch-profile owner can see every participating profile.\n- per-profile login revocation. Revoking the dashboard session affects the whole dashboard.\n\n## Option B — separate Mini Apps per profile\n\nEach profile gets its own dashboard process, port, tunnel, bot and login.\n\nWhat this buys:\n\n- strong isolation between bot tokens, owners and session tokens;\n- independent revocation and restart;\n- no shared dashboard auth boundary.\n\nCosts:\n\n- more processes, tunnels, launchd services and secrets;\n- Telegram permits only one menu button per direct-message chat, so two Mini Apps in the same chat need separate bots or direct/inline links;\n- more operational surface to monitor.\n\n## Recommendation\n\nFor profiles owned by the same operator, prefer **Option A**: one Mini App, one owner, one login, profile-scoped data calls. Treat the profile switcher as a convenience over one shared dashboard auth boundary, not as a security boundary.\n\nIf profiles have different owners or require independent bot identities, prefer **Option B**: separate dashboards and separate Mini Apps.\n\n## Open questions\n\n- Which profiles should be selectable: a fixed list, or every served profile with the plugin enabled?\n- Is the owner model intentionally one person across all profiles, or must each profile have its own owner and bot?\n- Should the profile list be enforced in the local proxy, the plugin, or both?\n- Does the secondary-profile plugin host behave correctly for sessions, knowledge and cron routes when reached with `?profile=`?\n- Should the proper fix be upstreamed into Hermes so token-auth middleware runs under the launch profile's secret scope for every provider, rather than kept as a plugin-local fallback?\n\n## Related records\n\n- [Agentic development management — Manager, Lead, Archon](record:023e7ae2-4677-4738-b8f2-be812cca6cf3) — owner access and the manager/lead boundary.\n- [Archon routing stack — public status](record:5d1e098b-24fc-43c6-b2d5-d68237742559) — the verified local stack this Mini App surfaces.\n- [Issue #5](https://github.com/tempuku/archon-automation-pilot/issues/5) — current Hermes access tracking issue.\n",
  "before_sha256": null,
  "after_sha256": "87d8247ce25a7446092437a0f0e439af3c1ef366fee80878c69e2c8507044423",
  "previous_event_id": null,
  "idempotency_key": "c7f3b1a2-9d4e-4f6a-8b2c-1e5d7a9c3f10",
  "request_sha256": "85d049d1960a951e0364d49c697ef3b9bb489b37ad09277d4d11af39c1c86a8f",
  "provenance": {
    "kind": "native",
    "source_ref": null,
    "original_time": null
  }
}
```
