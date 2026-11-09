---
type: diary-entry
title: Decide to reuse 3D model assets in one dynamic viewer
description: A single shared viewer should load existing model assets and real part assemblies, not embed duplicate meshes in separate HTML applications.
occurred_on: "2026-11-09"
project: ivanovo-models
tags: [decision, dry, viewer]
status: draft
visibility: private
sources:
  - resource: https://github.com/tempuku/ivanovo_models/issues/3
    title: Unified viewer implementation issue
---

# One viewer, many buildings

The House-Ship viewer establishes the desired visual language. Horseshoe contributes the ability to hide/show parts and explode/assemble actual multipart models. The app loads reusable independently colored master geometry and variant assets dynamically, with no normal per-building HTML duplication.

[Implementation checklist and status](https://github.com/tempuku/ivanovo_models/issues/3).
