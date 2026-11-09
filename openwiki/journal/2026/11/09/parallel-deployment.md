---
type: diary-entry
title: Deployment foundation can be implemented independently
description: GitHub Actions CI and safe preview-site packaging can be built before the final 3D viewer is integrated.
occurred_on: "2026-11-09"
project: ivanovo-models
tags: [decision, deployment, ci-cd]
status: draft
visibility: private
sources:
  - resource: https://github.com/tempuku/ivanovo_models/issues/4
    title: Deployment issue
---

# Parallel GitHub Pages deployment

Phase A — workflow, packaging, publication allowlist and synthetic-site CI — can start immediately. Phase B — real model assets and viewer integration — follows the completion of the production asset schema and viewer. Publishing to a public GitHub Pages site must receive explicit approval; model sources and private reference photographs must not be published by default.

[Issue #4](https://github.com/tempuku/ivanovo_models/issues/4).
