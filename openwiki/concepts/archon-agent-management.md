---
id: 023e7ae2-4677-4738-b8f2-be812cca6cf3
schema_version: 1
type: concept
title: "Agentic development management — Manager, Lead, Archon"
description: "Proposed on-demand Manager and repository Lead roles, single task-chain ownership, iterative validation and knowledge boundaries."
status: draft
visibility: public
project_id: 5d1e098b-24fc-43c6-b2d5-d68237742559
tags: [archon, agentic-development, management, workflow, validation]
sources:
  - resource: "record:5d1e098b-24fc-43c6-b2d5-d68237742559"
    title: "Primary Archon routing-stack record"
  - resource: "https://github.com/coleam00/Archon/blob/dev/.archon/architecture.md"
    title: "Archon upstream item admission and orchestration design"
---

# Agentic development management

**Status:** proposed architecture, not a deployed system. This note captures the agreed operating model and the points still requiring implementation. See the [primary Archon routing stack](record:5d1e098b-24fc-43c6-b2d5-d68237742559) for the independently verified runtime, gateway and tracing baseline.

## Responsibilities and boundaries

| Layer | Owns | Does not own |
| --- | --- | --- |
| Human / Manager | Goals, scope, portfolio priorities, meaningful decisions and concise management reporting | CSS fixes, detailed tests or live engineering context |
| Repository Lead | Issue scope, repo architecture, workflow selection, technical acceptance, iterative validation, evidence and escalation | Portfolio strategy or bypassing approval gates |
| Archon workflow executor | Versioned execution graphs, isolated runs, specialist workers, retries, tool calls, validation artifacts and durable work-item history | Changing the goal silently or declaring product success from a passing run |
| Pi / ExtremeRouter / Phoenix | Model execution, routing and observed traces | Task ownership and business acceptance |

A Manager and Lead are **roles invoked on demand**, not permanently running LLM sessions. Existing Archon state, the repository and events carry continuity. An idle Manager should cost zero model tokens.

## Two entry points; one task chain

- **Manual:** the owner converses with the Manager, who defines or changes the goal and delegates to the appropriate repository Lead. The Manager invocation can end while Archon work continues.
- **Automated:** GitHub issue, label, Kanban or scheduled events invoke the repository Lead through an authenticated, deduplicating trigger. Routine events do not require the Manager model.
- Both modes resolve the **same canonical task identity** (for GitHub, repository plus issue number) and reconcile requests against the same active Lead chain.
- The Manager can inspect, interrupt, reprioritize or request evidence for any chain, but does not create a competing Lead for an already owned task.

## One active chain per task

The intended invariant is **at most one active Lead chain for a canonical task**, regardless of manual or automated entry. That chain may launch multiple sequential or intentionally parallel child workflows under its authority.

Archon's documented item admission already prevents two concurrent runs of the **same workflow** on one item; this alone does **not** prove exclusivity across different workflow types. The missing enforcement is task-wide admission/ownership with atomic claim, idempotent event receipt, chain reuse, exclusive delegation authority and safe crash recovery. Pending owner instructions should be folded into the existing chain at the next safe reconciliation point. A lease/fencing generation is a possible mechanism, subject to implementation design and validation.

Do not treat role/model stickiness (A05) as task-chain ownership: its key is workflow/task/role/attempt and solves a different problem.

## What lives where

- **Knowledge Hub:** the Manager's concise diary — goals, important milestones, blockers, strategic decisions and source links. No per-turn transcripts, routine implementation rounds or exhaustive technical logs.
- **GitHub issue / PR:** Lead-owned delivery contract and current scope; acceptance, review and code evidence. One issue can contribute to a larger management goal; do not create one new issue per iteration.
- **Repository OpenWiki:** Lead-owned detailed design, architecture, acceptance rationale, unresolved findings and decisions, with links to issue, commits and evidence.
- **Archon work item / runs:** canonical task link, chain owner, workflow/run identities, validation results, artifacts, attention and external-event waits. Prefer the existing state model over duplicating live state in Knowledge Hub.
- **Phoenix:** privacy-preserving execution diagnostics and evaluations; it is not durable task memory.

## UI failure example: three poor iterations

1. A new issue asks for a UI improvement. The Lead establishes a target, acceptance criteria and visual references; then invokes `ui_development`.
2. A separate `ui_validation` reviews the running UI in a browser, compares viewports/reference images, checks regressions and records specific findings with screenshots and commit references.
3. After three unsuccessful attempts, the Lead reads the accumulated validation ledger. It should **not** blindly call `ui_development` again; it may choose design review, root-cause investigation, a narrower repair, or escalation.
4. The Manager receives only a concise outcome, for example: "Functional fixes landed; visual hierarchy still fails acceptance; Lead switched to design-first investigation." Detailed failures stay with the Lead.
5. Only evidence satisfying the original (or explicitly revised) goal permits completion. Workflow PASS is not automatically goal PASS.

The persistent validation context must include the original goal/version, outstanding findings, attempted approaches, commit/run and screenshot references, decisions and next action. A compact structured handoff is preferable to replaying long LLM transcripts.

## Interaction contracts (proposed)

**Manager → Lead:** canonical goal ID, repo/task reference, outcome and constraints, priorities, permissions/budget, requested decision or status, and correlation ID.

**Lead → Archon:** exact workflow, canonical item/chain identity, versioned acceptance contract, current context/evidence references, safety and budget constraints.

**Lead → Manager:** concise progress, outcome versus goal, material blocker, recommendation/decision request and evidence links — not raw technical details.

All workflows must keep their configured validation and merge gates; an LLM cannot override a deterministic denial or silently change acceptance criteria.

## Verification before adoption

- Confirm installed local Archon version supports required work-item, dispatch, chat and trigger APIs (upstream documentation is not deployment evidence).
- Demonstrate manual and webhook starts for one issue converge on one active Lead chain, including simultaneous duplicate and out-of-order events.
- Verify separate workflow types cannot claim competing chains; intentional child runs remain possible.
- Prove interrupted, restarted and re-triggered Leads recover the same task and complete without stale-owner writes.
- Show a three-round failed UI task preserves findings and changes strategy; no false completion on green implementation tests.
- Verify Knowledge Hub logs a short manager-facing milestone and that all technical evidence remains reachable via repository and Archon links.
- Measure model cost and enforce limits; manager invocations are demand-driven, and routine triggers use deterministic filtering where feasible.

## Open decisions

Task-wide ownership implementation and recovery policy, the exact Manager-to-Lead dispatch interface, lead escalation thresholds, and whether the conversational Manager is hosted in Archon Web/Telegram or a separate authorized client remain to be proven. Do not present these proposals as deployed functionality.
