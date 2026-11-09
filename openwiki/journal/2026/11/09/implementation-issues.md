---
type: diary-entry
title: Four implementation issues created for Ivanovo models
description: Documentation, production tooling, unified viewer and GitHub Pages deployment are tracked as separate issues.
occurred_on: "2026-11-09"
project: ivanovo-models
tags: [planning, github, architecture]
status: draft
visibility: public
sources:
  - resource: https://github.com/tempuku/ivanovo_models/issues/1
    title: Issue 1
  - resource: https://github.com/tempuku/ivanovo_models/issues/2
    title: Issue 2
  - resource: https://github.com/tempuku/ivanovo_models/issues/3
    title: Issue 3
  - resource: https://github.com/tempuku/ivanovo_models/issues/4
    title: Issue 4
  - resource: https://github.com/tempuku/ivanovo_models/pull/5
    title: Standards PR
  - resource: https://github.com/tempuku/ivanovo_models/pull/8
    title: Building foundation PR
  - resource: https://github.com/tempuku/ivanovo_models/pull/15
    title: Viewer groundwork PR
  - resource: https://github.com/tempuku/ivanovo_models/pull/7
    title: Deployment CI PR
---

# Four implementation issues created

The architectural-model project was split into four GitHub issues; the full manufacturing scope of #2 was subsequently split into [#9–#14](https://github.com/tempuku/ivanovo_models/issues). See each issue for its acceptance criteria:

- [#1 — shared documentation and standards](https://github.com/tempuku/ivanovo_models/issues/1)
- [#2 — reusable template and printer-profile foundation](https://github.com/tempuku/ivanovo_models/issues/2)
- [#3 — unified dynamic viewer with House-Ship appearance and Horseshoe disassembly](https://github.com/tempuku/ivanovo_models/issues/3)
- [#4 — safe GitHub Pages deployment, independently implementable Phase A](https://github.com/tempuku/ivanovo_models/issues/4)

## Same-day implementation check — 2026-11-09

GitHub shows #1 and foundation-only #2 closed after [PR #5](https://github.com/tempuku/ivanovo_models/pull/5) and [PR #8](https://github.com/tempuku/ivanovo_models/pull/8) merged. The independent colored master, mesh/bed/slicer evidence gates and legacy catalog subsequently merged in [#9](https://github.com/tempuku/ivanovo_models/issues/9), [#12](https://github.com/tempuku/ivanovo_models/issues/12) and [#14](https://github.com/tempuku/ivanovo_models/issues/14).

**Do not equate issue closure with full product completion:** #3 is marked closed, but [PR #15](https://github.com/tempuku/ivanovo_models/pull/15) only implemented viewer-state groundwork; the root shared browser renderer was not delivered. [Deployment PR #7](https://github.com/tempuku/ivanovo_models/pull/7) has green CI for a synthetic private fixture, but remains open with conflicts; no Ivanovo Pages preview was published. Four-color manufacturing (#10), Big LED (#11) and production orchestration (#13) are still open.

For **commands, current evidence links, outstanding physical checks and acceptance tests**, use the [Ivanovo project verification guide](../../../../projects/ivanovo-models.md). The snapshot is manual, not live-synchronized. All private repository links require the viewer's authorized GitHub session.
