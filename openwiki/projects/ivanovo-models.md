---
type: project
title: Ivanovo architectural 3D models
status: draft
project_id: ivanovo-models
tags: [architecture, openscad, 3d-printing, viewer]
visibility: private
sources:
  - resource: https://github.com/tempuku/ivanovo_models
    title: Source repository
---

# Ivanovo architectural 3D models

Canonical development source: [tempuku/ivanovo_models](https://github.com/tempuku/ivanovo_models).

## Implementation issues

- [#1 — Documentation, master model and workflow](https://github.com/tempuku/ivanovo_models/issues/1)
- [#2 — Template, production pipeline and printer profiles](https://github.com/tempuku/ivanovo_models/issues/2)
- [#3 — Unified dynamic viewer](https://github.com/tempuku/ivanovo_models/issues/3)
- [#4 — GitHub Pages CI/CD, parallel infrastructure then integration](https://github.com/tempuku/ivanovo_models/issues/4)

## Key decisions

- Detailed, fully colored master independent of HTML; derived printable variants retain maximum architectural detail.
- Five required print configurations: Big 1-color, Big 4-color, Big LED; Small 1-color, Small 4-color. No Small LED.
- Printer profile defaults to Bambu Lab P2S, but other profiles can be added; unknown AMS/accessories stay unconfirmed.
- One DRY viewer app loads reusable model assets and can show real multipart assemblies/exploded views.
- Deployment infrastructure can start before the final viewer/asset schema is ready.

Development status is tracked in the linked GitHub issues, not copied into this knowledge note as an automatically updated claim.
