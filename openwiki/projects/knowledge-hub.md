---
type: project
title: Knowledge Hub
status: draft
project_id: knowledge-hub
tags: [knowledge-management, diary, okf]
visibility: private
sources:
  - resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
    title: OKF specification
---

# Knowledge Hub

A Git-backed home for projects, ideas and decisions. Initial entry: [kickoff record](../journal/2026/11/09/knowledge-hub-kickoff.md). Store dated records as atomic OKF concepts; generate a day/week/month static diary from date-sharded JSON.

**Current phase:** [live public diary](https://tempuku.github.io/knowledge-hub-starter/) provides unrestricted, read-only access to four selected project-planning entries; their original source files are also public. New personal records must **not** be committed to this public source repository. [ADR 0001](../adr/0001-private-records-authenticated-app.md) records the accepted future move to separate private OKF storage and authenticated editing. Those capabilities are not implemented yet.
