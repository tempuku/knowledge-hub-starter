# Private Knowledge Hub: Cloudflare gateway, Phase 1

**Status: source and unit tests only; not deployed.** This is an intentionally
read-only first slice of [ADR 0001](../../openwiki/adr/0001-private-records-authenticated-app.md).
It does not create `tempuku/knowledge-hub-data`, move previously exposed records,
configure Cloudflare, or enable browser editing. The existing GitHub Pages diary
remains public and shows only separately approved records.

## Four-repository boundary

| Purpose | Repository | Visibility / status |
| --- | --- | --- |
| Knowledge app + public-only demo | `tempuku/knowledge-hub-starter` | Existing **public** repository and public Pages |
| Authoritative private OKF + private generated JSON | `tempuku/knowledge-hub-data` | **Proposed private repository; not yet created** |
| Models/CAD + private authenticated viewer | `tempuku/ivanovo_models` | Existing **private** repository; read-only Worker source in `tools/private_viewer/` |
| Optional synthetic/public model preview | `tempuku/ivanovo-preview` | **Proposed separate public repo; not yet created or approved for publication** |

The model gateway is **not** a knowledge editor, and the public model preview
must not receive private GLBs, photographs, sources or manufacturing records.

## What this Worker implements

A *direct* Cloudflare Worker (no `[assets]`) checks its trusted `ctx.access`
identity, an exact configured Access audience and an explicit approved-email
allowlist **before** any request, including HTML, CSS, icons, manifest and JSON.
The Worker authenticates the complete private origin; an identity header sent
by the browser is never accepted as proof.

* The unchanged **public UI** is loaded from the existing Pages deployment,
  through **exact UI-asset routes only**. This route cannot request public JSON.
* The **private diary JSON** is loaded from the separate private repository via
  GitHub Contents API using a server-only, narrowly scoped read token.
  Only `site-data/data/calendar.json`, paginated date files and individual
  entry JSON are allowed. Raw `openwiki/`, Markdown, secrets, Git history and
  arbitrary paths are **never** proxied.
* A private data retrieval failure is an error, never fallback to public Pages.
  Query tricks, traversal, unexpected paths and all writes fail closed.
  Every reply is non-cacheable, with restrictive CSP and no wildcard CORS.
* The old site's `/sw.js` is **not served** from the private origin; therefore
  the public network-first service worker cannot cache private JSON through
  this gateway. The public site's existing service worker is unchanged.
* The server-side GitHub token is never bundled into HTML, JavaScript, a Pages
  artifact or a GitHub Actions PR run. The Worker cannot create/edit records.

This first slice intentionally reuses the existing public Pages UI without
duplicating it. It depends on public Pages being live. Private JSON format must
continue matching the existing `tools/diary/build.py` output.

## Private-repository contract (pending provisioning)

Create **private** `tempuku/knowledge-hub-data` with default branch `main`,
and put authoritative `openwiki/` records there. Verify its private visibility,
GitHub App access and repository-scoped credentials before using it. This
repository has **not** been created by this PR.

The read-only Worker expects *only these generated paths* in the **private**
repo (no private JSON is committed to the public app repo):

```text
openwiki/journal/YYYY/MM/DD/<slug>.md    # authoritative OKF data
site-data/data/calendar.json             # derived private index
site-data/data/days/YYYY-MM-DD.json
site-data/data/days/YYYY-MM-DD/1.json    # up to 50 summaries
site-data/data/entries/YYYY-MM-DD-<slug>.json
```

For a first manual fixture build, use an **isolated temporary directory**, never
stage private files in a working copy or branch of the public repository:

```sh
# Run locally after YOU have created/cloned the private repo. Paths are examples.
PUBLIC_CHECKOUT="$HOME/src/knowledge-hub-starter"
PRIVATE_CHECKOUT="$HOME/src/knowledge-hub-data"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git -C "$PUBLIC_CHECKOUT" archive main | tar -x -C "$WORK"
rm -rf "$WORK/openwiki"
cp -R "$PRIVATE_CHECKOUT/openwiki" "$WORK/openwiki"
(
  cd "$WORK"
  python3 -m pip install -r tools/diary/requirements.txt
  python3 tools/diary/build.py --output-dir dist-private
)
mkdir -p "$PRIVATE_CHECKOUT/site-data"
rm -rf "$PRIVATE_CHECKOUT/site-data/data"
cp -R "$WORK/dist-private/data" "$PRIVATE_CHECKOUT/site-data/data"
# Review/commit ONLY in the PRIVATE repo; do not upload this artifact anywhere.
git -C "$PRIVATE_CHECKOUT" status --short
```

A reviewed private-only generation workflow, validation and change-triggered
refresh are follow-up tasks. Do not assume the private JSON exists before
building it. The private repository must remain the authoritative record store;
generated indexes are derived, not a substitute for the original Markdown.

## Cloudflare preparation and fail-closed deployment

1. Provision a Cloudflare Zero Trust organization. Deploy this *direct Worker*
   with `tools/private_hub/wrangler.toml` only after confirming which account
   and hostname are intended. Do not attach Workers Static Assets; the
   internal assets router does **not** forward `ctx.access` to the user Worker.
2. In **Workers & Pages → knowledge-hub-private → Access**, protect **All
   traffic** for this Worker, not just previews. Verify the policy covers
   the Worker route, `workers.dev`, custom domains and any version/preview
   URL. Set a policy admitting only explicit intended user identities.
3. Store `ACCESS_AUD` (exact Access application audience),
   `ALLOWED_EMAILS` (explicit comma-separated email addresses, no wildcard)
   and `GITHUB_READ_TOKEN` as **Cloudflare Worker secrets**, not checked-in
   Wrangler vars. Use a short-lived GitHub App installation token where
   possible; a fine-grained expiring token must have **Contents: Read**
   permission on **only** `tempuku/knowledge-hub-data` (not the models repo).
   A missing secret or missing verified `ctx.access` means no data is served.
4. Test without login: `/`, `/app.js`, `/data/calendar.json`, a daily
   shard and entry URL must all deny access. Test an invalid email and wrong
   audience. Test both production and preview/version hosts. Authenticated
   `GET` of actual private JSON should work; `POST`/other writes, raw
   Markdown and `/sw.js` must not. Verify no public CDN/cache storage.
5. Test the real hosted page in iPad Air 1 Safari 12 separately; mock unit
   tests and modern browser CI do not establish iOS 12 login compatibility.

**Do not mark this deployed or private-data migration complete merely because
the Worker tests are green.** Never publish private records or a production
endpoint as a public Pages artifact. Existing Git history in the public repo
may have exposed records marked `visibility: private`; moving them later
cannot undo old clones, caches or forks. Audit and rotate exposed secrets.

Cloudflare references: [Worker-level Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/),
[verified `ctx.access` and JWT guidance](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/),
[Static Assets caveat](https://developers.cloudflare.com/workers/static-assets/routing/worker-script/).

## Verification and next implementation slices

```sh
node --check tools/private_hub/worker.mjs
node --test tools/private_hub/worker.test.mjs
```

`.github/workflows/private-hub-auth.yml` runs these mocks on PRs and main.
It must remain independent of real GitHub/Cloudflare credentials and must
never deploy from an unreviewed PR.

**Remaining before real read/write use:** create and verify the private data
repo; migrate source files without copying private records back to the public
repo; build/validate private JSON; configure Access and secrets; verify live
anonymous denial and authenticated reads; then add authenticated Git-backed
create/edit with OKF validation, CSRF controls, SHA conflict handling and audit
commits. Add an explicit per-record public export pipeline only after separate
approval. For the models project, finish its existing private viewer integration
and Cloudflare live checks, keeping optional public demo publication separate.
