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
  - resource: "https://github.com/tempuku/personal-finance/pull/10"
    title: "MVP 00 contract-first foundation delivery"
  - resource: "https://github.com/tempuku/personal-finance/commit/d792d310cd0160756ef13084041183d63eac64ff"
    title: "Merge commit for PR 10"
  - resource: "https://github.com/tempuku/knowledge-hub-starter/issues/72"
    title: "Persistent cross-project stand-up design"
---

# Personal Finance

**Project status: in progress.** This is the public, minimal Knowledge Hub project-progress record. The [original development repository](https://github.com/tempuku/personal-finance) is private, and its full design documents remain there. This record must never contain balances, transactions, bank names, credentials, statements, sessions, account identifiers, or private attachments.

## Objective and current scope

Build a local-first finance application covering manually authorized statement acquisition, a verifiable transaction ledger, spending analysis, and credit-card grace-period information.

## Last checked: 2026-11-24

- [MVP 00: contract-first foundation (#2)](https://github.com/tempuku/personal-finance/issues/2) is closed as completed. The contract package was delivered through [PR #10](https://github.com/tempuku/personal-finance/pull/10) and squash-merged as commit [d792d310](https://github.com/tempuku/personal-finance/commit/d792d310cd0160756ef13084041183d63eac64ff).
- Both required checks passed on the reviewed PR head: OpenWiki and repository validation, and Python contract checks. The reviewed head was 6a44bf004514c92c6451943ad20005aeaded5164 against base 88ef564185b7d9e8fb882b0c77235b7afdb28da9.
- The delivered package contains bank-independent domain types, state machines, typed errors, ports, versioned event/import/artifact schemas, local application request/response contracts, synthetic contract tests, and a typed distribution. No live bank integration, real statement parsing, production ledger, or end-to-end UI is claimed.
- The repository README still states that no bank integration or end-to-end workflow is verified. Contract-test and CI success are not live-bank verification.

## Decisions and completion boundaries

- Keep implementation local-first and protect private financial data; real bank login requires explicit operator control.
- Bank acquisition must not directly mutate the ledger; imported files require quarantine, validation, deduplication and audit trails.
- The MVP excludes MCP, per the project's documented ADR. Resolve ambiguities in source OpenWiki before parallel development.
- Treat mock tests, a merged PR, real-bank operator checks, and production readiness as distinct evidence levels.
- Keep this parent record in_progress until explicitly updated, even when linked work has no recent commits.

## Next actions

1. Record the separately reviewed Python implementation baseline ADR in the private source repository before downstream component work begins.
2. Plan independent ledger, import, browser-acquisition and UI workstreams now that the shared contracts are merged.
3. Verify any bank integration separately with operator-assisted live checks; do not infer live support from contract tests or CI.
4. Reuse this single Knowledge Hub record for future stand-ups; append to its sibling history instead of creating daily records.

## Relationship to earlier staging

A preliminary draft was placed in the private Personal Finance source repository on 2026-11-21. This public, content-minimized Knowledge Hub record is the canonical **stand-up/project-status** record. The private source remains authoritative for implementation requirements, and any prior staging copy is historical, not another active Knowledge Hub project. [Knowledge Hub #72](https://github.com/tempuku/knowledge-hub-starter/issues/72) tracks future automated cross-repository refresh.
