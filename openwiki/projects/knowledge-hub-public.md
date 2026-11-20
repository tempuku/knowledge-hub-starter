---
id: "9a2f68b9-a1a9-40c6-ae1c-6224e1630011"
schema_version: 1
type: project
title: "Knowledge Hub (public demo)"
description: "Published read-only project overview for the Knowledge Hub interface."
status: in_progress
visibility: public
tags: [demo, knowledge-hub]
---
# Knowledge Hub - public project recap

**Snapshot: 2026-11-20.** This is the public-safe current overview for [the Knowledge Hub source repository](https://github.com/tempuku/knowledge-hub-starter). GitHub evidence was checked on this date. CI, a merged change, and a deployed and visually verified application are different validation stages. No private data or real personal notes are included here.

## Current state

- **Lifecycle:** in_progress. Public generated-v1 UI and 28 approved public records were merged via [PR #76](https://github.com/tempuku/knowledge-hub-starter/pull/76) on November 18. The compact mobile/tablet shell and Diary folding shipped in [PR #96](https://github.com/tempuku/knowledge-hub-starter/pull/96) (`ac3c520`); the amber `in_progress` status and PWA shell refresh shipped in [PR #97](https://github.com/tempuku/knowledge-hub-starter/pull/97) (`8d6a3bc`). The [Pages deployment](https://github.com/tempuku/knowledge-hub-starter/actions/runs/44623011857) succeeded, and live Chromium checks at 320-1440px found no horizontal overflow, one expanded non-empty Diary day, and the amber status chip. Physical iPad Air acceptance remains separate and unverified.
- **Agent discovery:** [PR #108](https://github.com/tempuku/knowledge-hub-starter/pull/108) adds read-only `knowledge_search` and `knowledge_history` MCP tools over the existing P-03 search primitives, with OpenCode V2 global onboarding in the [#104 acceptance record](https://github.com/tempuku/knowledge-hub-starter/blob/main/docs/acceptance/agent-client-104.md). Public capability filters matches, totals and history events by `visibility`; this is not website allowlist parity. The PR is open, not merged, and a live model-driven search -> read -> history journey remains manual and unverified.
- **Storage and diary:** the approved design uses one canonical record with a sibling append-only history log; Diary is a projection of logs, not a collection of manually authored daily copies. Legacy dated notes and historical logs still exist pending reviewed migration. [Design #24](https://github.com/tempuku/knowledge-hub-starter/issues/24); [migration design](https://github.com/tempuku/knowledge-hub-starter/issues/36).
- **Migration blocker:** [issue #36](https://github.com/tempuku/knowledge-hub-starter/issues/36) and draft [PR #82](https://github.com/tempuku/knowledge-hub-starter/pull/82) contain a reproducible dry-run candidate, but production cutover is not authorized. Reviewed frozen inventory preserves 23 canonical records, history, source aliases, and source bytes; do not compress it by deleting unique evidence. [Inventory review](https://github.com/tempuku/knowledge-hub-starter/issues/35).
- **Remaining work:** [#38 atomic cutover](https://github.com/tempuku/knowledge-hub-starter/issues/38), [#39 deployed browser/HTTPS verification](https://github.com/tempuku/knowledge-hub-starter/issues/39), [#72 persistent cross-repository stand-up](https://github.com/tempuku/knowledge-hub-starter/issues/72), and [#46 traceable Topics design](https://github.com/tempuku/knowledge-hub-starter/issues/46) remain open. Private authenticated deployment remains independently blocked by provisioning and real denial tests ([ADR 0001](https://github.com/tempuku/knowledge-hub-starter/issues/2), [#2](https://github.com/tempuku/knowledge-hub-starter/issues/2), [#12](https://github.com/tempuku/knowledge-hub-starter/issues/12)).
- **Open integration PRs at this snapshot:** [#82](https://github.com/tempuku/knowledge-hub-starter/pull/82), [#47](https://github.com/tempuku/knowledge-hub-starter/pull/47), [#11](https://github.com/tempuku/knowledge-hub-starter/pull/11), and [#9](https://github.com/tempuku/knowledge-hub-starter/pull/9). Their open state is not acceptance evidence.

## Next actions and acceptance

1. Review and rebase the migration rehearsal against current main; preserve its private/public eligibility, exact source inventory, and required checks before considering a merge.
2. Complete cutover acceptance before changing the production source, removing legacy records, or declaring the log-only diary authoritative.
3. Verify deployed mobile/desktop UI, authenticated private access, and a genuine agent MCP round trip separately; record evidence in linked issues and append meaningful progress here as log events.

## Owner decision: minimal records, maximum history (2026-11-19)

- Maintain **at most one `in_progress` project record per GitHub repository** in the canonical authorized source. Keep that same record open while its repo has unfinished work, even during quiet days; never equate inactivity with completion.
- Update the existing project record and append one complete event to its sibling log for status reports, stand-ups, PR/issue progress, acceptance, blockers and next actions. Do not manufacture a fresh knowledge record or dated diary source for each update.
- Create a separate record only for knowledge that must be independently addressable and maintained: an enduring decision, distinct concept or genuinely separate subject. Prefer links/sections and tags over overlapping project records. A repository may have independent reference records, but only one active parent project status.
- Consolidate only after exact content, source IDs, privacy permissions, inbound links, append-only event chains and migration aliases are accounted for. Mark a superseded record `deprecated` with a redirect/evidence log event rather than destroying a unique record or collapsing a private record into the public demo.
- For this public repository, the `Knowledge Hub (public demo)` and `Ivanovo Models (public demo)` records are the two `in_progress` public project views; earlier `visibility: private` legacy project records stay unchanged for the reviewed migration. A frontmatter privacy label does not protect source in public Git.

**Audit outcome:** 27 current record-like Markdown files were enumerated (excluding structural indexes and sibling logs); two pairs describe the same project across public-demo and legacy-private contexts. Nine independently substantive dated notes must not be discarded as mere duplicate updates. Synthetic public/private recovery test fixtures are intentionally segregated by visibility. No historical record or log was deleted by this recap.

## Linked records and evidence

- [Ivanovo Models public project overview](record:1e26b8e8-cc64-46dd-923b-ea0163480012) - related project using the shared private/public access design; this link does not disclose private model data.
- [This project's complete append-only history](https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/projects/knowledge-hub-public.log.md) - revisions and source snapshots; individual log events remain the evidence trail.
- [Traceable topics and evidence traversal (#46)](https://github.com/tempuku/knowledge-hub-starter/issues/46) - design and acceptance tracking.
- [Cross-repository stand-up and record identity (#72)](https://github.com/tempuku/knowledge-hub-starter/issues/72) - persistent active-record policy.
- [Consolidation and recap PR #87](https://github.com/tempuku/knowledge-hub-starter/pull/87) - baseline review and CI evidence.
