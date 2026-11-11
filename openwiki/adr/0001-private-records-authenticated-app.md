---
type: decision
title: "Separate public application code from private knowledge records"
description: "Authenticated, Git-backed Knowledge Hub with a public demo and private production diary."
status: stable
tags:
  - architecture
  - security
  - privacy
  - authentication
  - knowledge-hub
sources:
  - resource: "https://github.com/tempuku/knowledge-hub-starter"
  - resource: "https://github.com/tempuku/knowledge-hub-starter/issues/2"
---

# ADR 0001: Public app, private records, authenticated reading and editing

Storage/UI addendum: [the implementation design](../design/overview.md) supersedes the date-directory source convention in section 6 and fixes the record/log writer contract. Historical rollout descriptions below remain evidence of earlier behavior, not current authoring instructions.

- **Date:** 2026-11-09
- **Decision status:** Accepted as the target architecture; **implementation pending**.
- **Scope:** [Knowledge Hub](../projects/knowledge-hub.md), including the diary and future Projects, Search and Timeline views.
- **Related work:** [Hosting and real-device acceptance, issue #2](https://github.com/tempuku/knowledge-hub-starter/issues/2).

## Context

The Knowledge Hub is a Google Open Knowledge Format (OKF) v0.2 archive of ideas, project links, decisions and dated diary entries. It has a classic iOS/iPad web UI targeting, among other devices, the **original iPad Air on iOS 12**. The current public GitHub Pages app is a **read-only, public-only export**: it does not authenticate a user, securely fetch private content or persist edits.

An OKF frontmatter field such as `visibility: private` is **not access control**. The repository `tempuku/knowledge-hub-starter` was made public while it contained records bearing that label. Those files and their Git history are publicly accessible even though the Pages exporter omits them. Moving or deleting files in a later commit cannot guarantee that already published history, forks or copies disappear.

The user wants to keep an internet-accessible, installable iPad application, protect the knowledge records, and **read and edit** them through the web UI after signing in. The deployment must be validated with a **real working HTTPS URL**, not a screenshot, mock or CI-only result.

## Decision

**Separate the public application from the private knowledge data and authenticate all production access to personal records.**

1. **Public app source:** Keep `tempuku/knowledge-hub-starter` as the codebase for the shared iPhone/iPad/desktop UI, OKF checker, build tools and public demo. The demo is limited to explicit public or synthetic test content. Do **not** place personal records, production API tokens or private generated JSON in this repo.
2. **Private data source:** Create a separate **private** repository (proposed name: `tempuku/knowledge-hub-data`) containing the authoritative `openwiki/` OKF bundle: diary concepts, projects, ADRs and their Git history. This name describes a **future repository**, not one claimed to exist.
3. **Authenticated production site:** Put the actual private application behind **Cloudflare Access** (or an equivalently enforced login gate) using an HTTPS hostname. Serve the frontend and backend/API through the same authenticated origin where practical. The current GitHub Pages site remains an optional public demo; **Pages alone is not private hosting**.
4. **Server-side API:** Implement a **Cloudflare Worker** (or equivalent backend) that validates authenticated identity and authorization **on every private read and write**, including API endpoints; do not rely on client navigation state or a hidden URL for security. Do not ship GitHub credentials to browser JavaScript, HTML, assets or service workers.
5. **Git-backed editing:** The backend uses a narrowly scoped GitHub App installation or equivalent short-lived server-side credential with **Contents read/write permission only on the private data repository**. It reads and writes atomic Markdown concepts, validates OKF metadata and relative indexes, uses Git blob SHA/conditional updates to detect conflicts, and commits edits with an audit trail. Treat concurrent edits and authorization failures as explicit user-visible errors.
6. **Diary browsing (storage decision superseded):** The [hierarchical record design](../design/overview.md) replaces date-folder source storage with subject-area records and sibling logs. The diary projects recorded changes into paginated day/week/month indexes and lazy-loads bodies. Factual occurrence metadata remains distinct. Existing dated files are preserved until the reviewed migration. All authentication and private-storage requirements in this ADR remain in force.
7. **Device support:** Keep the early-iOS 5–6 visual style and JavaScript compatible with **Safari 12 / iOS 12.5.x** for the original iPad Air. Validate on physical hardware before declaring that device supported.

### Authentication and security requirements

- All private API endpoints require a verified login/session and an authorized identity. The backend must independently validate the Access assertion/token according to the provider's current recommendations; a public Worker URL or bypassed path must not provide unauthenticated access.
- Use HTTPS and secure cookie/session semantics. Use CSRF protection for cookie-authenticated write operations, reject unexpected origins where applicable, and enforce least privilege for provider and GitHub credentials. Secrets belong only in managed backend secret storage.
- Read, create, update and delete operations must check authorization, validate filenames, record IDs, input lengths and the OKF document schema. Prevent directory traversal and access outside the designated private repository or namespace.
- Do not automatically put private API responses into a **public or shared cache**. The current network-first service worker should bypass private API requests and avoid caching authenticated pages or record bodies; future optional offline private reading requires a separate, reviewed threat model and encrypted device storage.
- Keep detailed server-side error logging free of secrets and private note bodies. Git history remains the audit trail for document updates; record edit provenance without claiming it establishes the date an event happened.
- Public publishing is a **separate explicit action per record**, subject to allowlist review and content validation; never infer permission from a tag, a URL being known, or a repository being public.

### Migration and exposure handling

Before publishing additional personal material:

1. Inventory all files and Git history already visible in the now-public `knowledge-hub-starter` repository, including supposedly private concepts. Treat that historical exposure as irreversible for confidentiality purposes; check for credentials and rotate any that were exposed.
2. Establish the private data repo, preserving the OKF structure and source links, and verify its privacy and credentials. Do not claim it exists until it has actually been created and checked.
3. Remove personal records and generated private data from the public app's **current tree**, stop adding them there, and review the history-remediation options without claiming a force-push erases existing forks, caches or copies.
4. Change the build pipeline so a public demo uses **only explicitly public/synthetic fixtures**, while the private production app fetches records through the authenticated backend.
5. Verify that anonymous requests cannot read or modify private entries. Test authenticated reads and edits, authorization errors, editing conflicts, link traversal, and the original iPad Air's Safari behavior.

## Phased rollout — unrestricted reading before authentication

On 2026-11-09, the owner authorized **unrestricted reading of the initial project-planning records through the hosted HTML web diary** as an interim step. The four existing dated journal concepts have been marked `visibility: public`; the public GitHub Pages workflow publishes only explicitly public concepts. That implementation is **read-only**, without login or web-based editing. The public front end and the underlying public Git repository do not protect those records from other internet users. New private thoughts must **not** be added to the public source repository. The longer-term decision above—separate private data, authenticated read/write API, and secure editing—remains in force but is not yet implemented.

## Alternatives considered

- **Single public GitHub repository plus `visibility: private` flags:** Rejected. Metadata and website filters do not protect public source files.
- **Single private repository plus GitHub Pages:** Insufficient on its own. A publicly served Pages site is not an authenticated private API or editor, and publication may expose generated data.
- **Direct GitHub API from browser with a personal access token:** Rejected. Browser-distributed secrets and broad tokens create unacceptable exposure and revocation risks.
- **Copying giant `log.md` files into HTML:** Rejected. Duplicates source data and makes day/week/month navigation inefficient.

## Consequences and implementation plan

**Benefits:** Publicly inspectable app code; private, versioned OKF records; a single responsive UI; secure browser reading and editing; narrowly scoped access; optional explicit public sharing.

**Costs/tradeoffs:** Authentication and backend hosting now require operations, security reviews and credential rotation; the old iPad's browser may constrain identity-provider flows and caching; Git-based edits require concurrency handling. The GitHub Pages public demo and production private app are different deployment contexts, but share the **same UI code**.

**Implementation order:** (1) audit public exposure; (2) create private data repository; (3) implement authentication and read-only API; (4) implement authenticated create/edit with OKF validation and Git commits; (5) explicitly separate public demo vs private production deployments; (6) test live HTTPS URLs, unauthenticated access denial and **physical iPad Air 1** login/read/edit.

**Acceptance:** This ADR documents the chosen direction; it **does not** claim the authentication service, private repo, secure deployment or editing features have been built. Completion requires a live, verified HTTPS production page where the owner can sign in, read actual private records, add/edit a record, and observe the resulting private Git commit; anonymous access must fail.

## Related architecture reuse — Ivanovo private 3D viewer (2026-11-09)

The separate [Ivanovo models project](../projects/ivanovo-models.md) uses the **same security principle**, not the same application or data store. Its canonical repository `tempuku/ivanovo_models` is already private; no additional knowledge-data repository is required merely to secure that viewer. This **does not** implement the private Knowledge Hub diary/authenticated editing described by this ADR.

- [Ivanovo issue #4](https://github.com/tempuku/ivanovo_models/issues/4) changed from a public-only Pages preview target to **authenticated private production viewing**, with public Pages limited to an explicitly approved synthetic/public demo.
- [PR #7](https://github.com/tempuku/ivanovo_models/pull/7) merged safe public-demo packaging/validation but did not publish.
- [PR #20](https://github.com/tempuku/ivanovo_models/pull/20) merged a **read-only Cloudflare Worker gateway implementation** that requires a verified Access identity, configured audience and explicit email authorization for HTML, JS, catalog, Markdown and GLB requests, and keeps the GitHub read credential server-side. The [fresh private-auth workflow run](https://github.com/tempuku/ivanovo_models/actions/runs/42677163711) passed after earlier runs failed before starting jobs.
- The shared renderer remains [draft PR #19](https://github.com/tempuku/ivanovo_models/pull/19). The merged gateway is **not deployed**: no live Access-protected URL, external secrets, real building GLBs or physical device acceptance has been verified.

**Security boundary:** UI/path filtering or a `visibility: private` flag cannot secure public GitHub files. The Ivanovo Worker uses server-side enforcement; existing Access configuration and real anonymous-denial testing must be completed before calling the site private. Its read-only gateway does not supply the Knowledge Hub's planned editing permissions, OKF record store, conflict handling or signed-in diary functionality.
