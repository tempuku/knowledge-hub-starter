---
id: "44b0e133-ea13-4e61-a7f8-98a2af3a106b"
schema_version: 1
type: "concept"
title: "Hermes Mini App — multi-profile access model"
description: "Design discussion for serving archon-operator and other Hermes profiles\
  \ from one Telegram Mini App, with authentication, isolation and implementation\
  \ trade-offs."
status: "in_progress"
visibility: "public"
tags:
  - "hermes"
  - "telegram"
  - "miniapp"
  - "profiles"
  - "authentication"
  - "archon"
occurred_on: "2026-11-26"
sources:
  - resource: "record:023e7ae2-4677-4738-b8f2-be812cca6cf3"
    title: "Agentic development management — Manager, Lead, Archon"
  - resource: "record:5d1e098b-24fc-43c6-b2d5-d68237742559"
    title: "Archon routing stack — public status"
  - resource: "https://github.com/tempuku/archon-automation-pilot/issues/5"
    title: "Issue #5 — Hermes owner Telegram access"
---

# Hermes Mini App — multi-profile access model

**Status:** in progress. This is a design discussion, not a deployed multi-profile feature. The live Mini App currently operates against the `archon-operator` profile.

## What is true today

- The Telegram Mini App plugin is installed in `archon-operator`, and the dashboard process on `127.0.0.1:9120` is launched with that profile.
- The host also has the default Hermes profile, so Hermes enables multi-profile hosting. Under that mode, credential reads without an active profile scope fail closed.
- Hermes accepts a dashboard-auth provider only from the **launch profile**. A provider registered from a secondary profile is ignored because dashboard auth belongs to the launch process.
- The earlier "auth provider unreachable" failure was an unscoped secret read in the bearer-token middleware, not a missing bot token. A local fallback now binds the launch profile's own secret scope for that middleware path.
- After login, the Mini App receives the dashboard session token. That token is **dashboard-wide**, not scoped to one profile.

## Core constraint

One dashboard process has one login boundary. `?profile=<name>` can scope a plugin request, its secret scope and its session store to another served profile, but it does not create a second login or a second bot identity.

A secondary profile that wants to serve plugin routes must have the plugin installed and enabled there. Hermes then runs that profile's copy in its own plugin host rather than importing it into the launch process.

## Option A — one Mini App with a profile switcher

One bot, one owner, one menu button, with a selector for `archon-operator` and any other enabled profile.

Implementation shape:

1. Install and enable `telegram-app` in each participating profile.
2. Keep `auth/verify` on the launch profile and obtain one dashboard session token.
3. Send `?profile=<name>` on data calls such as sessions, status, logs, cron and knowledge.
4. Add a profile selector to the Mini App UI and persist the selection.
5. Restrict the accepted profile list in the proxy or plugin rather than allowing arbitrary names.

What this buys:

- one login and one menu button;
- profile-scoped data and secrets;
- no need to run a second tunnel or a second dashboard.

What it does **not** buy:

- separate owners or separate bot identities;
- isolation between profiles. The session token is dashboard-wide, so the launch-profile owner can see every participating profile.
- per-profile login revocation. Revoking the dashboard session affects the whole dashboard.

## Option B — separate Mini Apps per profile

Each profile gets its own dashboard process, port, tunnel, bot and login.

What this buys:

- strong isolation between bot tokens, owners and session tokens;
- independent revocation and restart;
- no shared dashboard auth boundary.

Costs:

- more processes, tunnels, launchd services and secrets;
- Telegram permits only one menu button per direct-message chat, so two Mini Apps in the same chat need separate bots or direct/inline links;
- more operational surface to monitor.

## Recommendation

For profiles owned by the same operator, prefer **Option A**: one Mini App, one owner, one login, profile-scoped data calls. Treat the profile switcher as a convenience over one shared dashboard auth boundary, not as a security boundary.

If profiles have different owners or require independent bot identities, prefer **Option B**: separate dashboards and separate Mini Apps.

## Open questions

- Which profiles should be selectable: a fixed list, or every served profile with the plugin enabled?
- Is the owner model intentionally one person across all profiles, or must each profile have its own owner and bot?
- Should the profile list be enforced in the local proxy, the plugin, or both?
- Does the secondary-profile plugin host behave correctly for sessions, knowledge and cron routes when reached with `?profile=`?
- Should the proper fix be upstreamed into Hermes so token-auth middleware runs under the launch profile's secret scope for every provider, rather than kept as a plugin-local fallback?

## Related records

- [Agentic development management — Manager, Lead, Archon](record:023e7ae2-4677-4738-b8f2-be812cca6cf3) — owner access and the manager/lead boundary.
- [Archon routing stack — public status](record:5d1e098b-24fc-43c6-b2d5-d68237742559) — the verified local stack this Mini App surfaces.
- [Issue #5](https://github.com/tempuku/archon-automation-pilot/issues/5) — current Hermes access tracking issue.
