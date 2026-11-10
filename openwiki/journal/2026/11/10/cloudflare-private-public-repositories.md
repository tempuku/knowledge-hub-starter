---
type: diary-entry
title: Begin Cloudflare access work for public and private knowledge and model repositories
description: Reviewed the November 9 architecture, opened two draft Cloudflare-related PRs, and distinguished passing CI from live authenticated deployment.
occurred_on: "2026-11-10"
project: knowledge-hub
tags: [cloudflare, architecture, security, deployment, knowledge-hub, ivanovo-models]
status: draft
visibility: public
sources:
  - resource: https://github.com/tempuku/knowledge-hub-starter/blob/main/openwiki/adr/0001-private-records-authenticated-app.md
    title: Accepted Knowledge Hub private-records architecture
  - resource: https://github.com/tempuku/knowledge-hub-starter/pull/9
    title: Knowledge Hub private Cloudflare gateway draft PR
  - resource: https://github.com/tempuku/ivanovo_models/pull/30
    title: Ivanovo live Access verification draft PR
  - resource: https://github.com/tempuku/ivanovo_models/pull/20
    title: Previously merged private Ivanovo viewer gateway
---

# Cloudflare access for knowledge and model repositories

Reviewed the November 9 Knowledge Hub records and the accepted public-app/private-data decision. The direction is to use Cloudflare Access and direct Workers for authenticated private production access, while keeping any public demos separate from confidential source records and 3D assets.

## Repository boundaries

- **Knowledge Hub public app:** `tempuku/knowledge-hub-starter` is public. Its existing GitHub Pages diary serves only explicitly approved public entries.
- **Knowledge Hub private records:** `tempuku/knowledge-hub-data` is the proposed private OKF source and generated diary-data repository. It has **not** been created or migrated yet.
- **Ivanovo private models:** `tempuku/ivanovo_models` is private. Its read-only Cloudflare Worker gateway was merged in [PR #20](https://github.com/tempuku/ivanovo_models/pull/20), but it has not been deployed and tested against live Cloudflare Access.
- **Optional public model demo:** `tempuku/ivanovo-preview` is a proposed separate public destination for approved synthetic or public assets only. It has not been created or authorized for publication.

## Implementation work on November 10

- Opened [Knowledge Hub draft PR #9](https://github.com/tempuku/knowledge-hub-starter/pull/9): a direct, fail-closed Cloudflare Worker with verified Access identity, an exact audience and an explicit user allowlist. The gateway serves the existing public UI through restricted routes and reads private date-sharded JSON from the **future** private repository with a server-only, repository-scoped credential. It has no editing endpoint, no private-data fallback to public Pages and no service-worker route for caching private records. CI also checks that new private-marked OKF notes are not added to public Git source.
- Opened [Ivanovo draft PR #30](https://github.com/tempuku/ivanovo_models/pull/30): an anonymous live-Access probe for the model viewer's HTML, JavaScript, catalog, GLB and Markdown routes, plus mock tests and safer Worker preview defaults. The probe must be run later against actual provisioned HTTPS hostnames.
- At the last check, **both Knowledge Hub PR #9 checks passed** and **all four Ivanovo PR #30 workflows passed**. These are code/CI results, not proof of working Cloudflare login or private website deployment.

## Remaining work

Create and verify the private Knowledge Hub data repository; audit prior public-repository exposure before migrating records; privately build the diary JSON indexes; configure Cloudflare Access for production and all relevant Worker/preview hostnames; install narrowly scoped credentials; and test anonymous denial plus authenticated reading at real HTTPS URLs. Git-backed Knowledge Hub editing needs its own validation, CSRF protection and Git conflict checks. The Ivanovo shared 3D renderer remains in [draft PR #19](https://github.com/tempuku/ivanovo_models/pull/19); live viewer acceptance and real building-model checks are separate.

**Status:** Foundation PRs are open and draft. No private Cloudflare deployment, data migration or actual iPad Air login is claimed. This entry records public technical decisions and implementation status only; it contains no personal diary data, credentials or private model assets.
