---
id: "f3f297e5-394b-46b0-b16d-b8ac09bf6ee4"
schema_version: 1
type: project
title: "Personal Finance"
description: "Public project progress overview for a private local-first finance application; no financial account data."
status: in_progress
visibility: public
tags: [personal-finance, software-development, mvp]
sources:
  - resource: "https://github.com/tempuku/personal-finance"
    title: "Source code repository (private; access required)"
  - resource: "https://github.com/tempuku/personal-finance/issues/2"
    title: "MVP 00: contract-first foundation"
  - resource: "https://github.com/tempuku/knowledge-hub-starter/issues/72"
    title: "Persistent cross-project stand-up design"
---

# Personal Finance

**Project status: in progress.** This is the public, minimal Knowledge Hub project-progress record. The [original development repository](https://github.com/tempuku/personal-finance) is private, and its full design documents remain there. This record must never contain balances, transactions, bank names, credentials, statements, sessions, account identifiers, or private attachments.

## Objective and current scope

Build a local-first finance application covering manually authorized statement acquisition, a verifiable transaction ledger, spending analysis, and credit-card grace-period information.

## Last checked: 2026-11-24

- [MVP 00: contract-first foundation (#2)](https://github.com/tempuku/personal-finance/issues/2) is open. Define domain value types, state transitions, bank-independent ports, errors, versioned interfaces, offline tests, and clear compatibility rules before separate agents implement bank adapters, import, core, and UI.
- The repository README describes the project as design-stage work. There is no verified live bank integration or end-to-end workflow.
- The 2026-11-21 GitHub check found one open implementation issue and no open PRs. Recheck the source for live changes; this snapshot is not an automatically refreshed CI claim.
- On 2026-11-24 the generic Archon issue flow completed [issue #8](https://github.com/tempuku/personal-finance/issues/8) in [PR #9](https://github.com/tempuku/personal-finance/pull/9), merged at `88ef564185b7d9e8fb882b0c77235b7afdb28da9`. The repository gained a deterministic OpenWiki validator, 13 tests and a passing `OpenWiki and repository validation` check. This is repository-preparation evidence, not bank or application verification.

## Decisions and completion boundaries

- Keep implementation local-first and protect private financial data; real bank login requires explicit operator control.
- Bank acquisition must not directly mutate the ledger; imported files require quarantine, validation, deduplication and audit trails.
- The MVP excludes MCP, per the project's documented ADR. Resolve ambiguities in source OpenWiki before parallel development.
- Treat mock tests, a merged PR, real-bank operator checks, and production readiness as distinct evidence levels.
- Keep this parent record in_progress until explicitly updated, even when linked work has no recent commits.

## Next actions

1. Implement and validate the contract-first foundation in [issue #2](https://github.com/tempuku/personal-finance/issues/2).
2. Record exact merged PR, CI links and validation observations here as append-only updates; do not claim tests passed without evidence.
3. Plan independent workstreams once contracts are stable.
4. Reuse this single Knowledge Hub record for future stand-ups; append to its sibling history instead of creating daily records.

## Relationship to earlier staging

A preliminary draft was placed in the private Personal Finance source repository on 2026-11-21. This public, content-minimized Knowledge Hub record becomes the canonical **stand-up/project-status** record upon merge. The private source remains authoritative for implementation requirements, and any prior staging copy is historical, not another active Knowledge Hub project. [Knowledge Hub #72](https://github.com/tempuku/knowledge-hub-starter/issues/72) tracks future automated cross-repository refresh.
