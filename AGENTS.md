# Working rules

- Treat `records/` as the writable OKF v0.2 bundle (canonical v1 records, sibling `.log.md` history and structural indexes); `openwiki/` is ordinary hub documentation after the 2026-11-26 root split, and a fork can clear `records/` to start its own knowledge base. `dist/` is generated and ignored by Git. **ADR 0001** (`openwiki/adr/0001-private-records-authenticated-app.md`) defines the target move of private records to a separate private repository; this migration is not yet implemented.
- Read `openwiki/design/overview.md` and its linked contracts before implementing storage or UI changes. The target is hierarchical canonical records plus sibling logs, with the diary generated from logs only. Existing date-folder records are migration input: preserve them until the reviewed migration, and do not create a competing target authoring path.
- Never use Git commit timestamps as factual occurrence dates. The target Diary groups by recorded UTC change time; optional occurred_on/occurred_at are separate author-supplied facts. Correcting a factual date requires a logged update.
- Keep links to original issues, PRs, repositories, decisions and other evidence in `sources` and in Markdown; do not reproduce sources as if they were independent evidence.
- Entries should be `status: draft` until reviewed; do not invent verification.
- All personal records default to `visibility: private`, but this field **does not secure files in a public Git repository**. Do not put new personal notes in this public source repo. No public publishing without explicit authorization and allowlist review.
- Add every new concept to its `records/` directory `index.md`. New directories require an `index.md` and a parent index entry.
- Existing directory `log.md` files are migration input, not the target history store. Use the per-record sibling log contract; structural index pages have no history events.
- Run the same staged OKF checker as `ivanovo_models` before committing. The checker reads staged files.
- Do not duplicate huge `log.md` files, JSON catalog content, or HTML apps for each project.
- Preserve the user-approved visual direction: **early iOS 5–6 skeuomorphic app** (blue glossy navigation, segmented controls, grouped lists, subtle linen texture). Keep one CSS-driven, responsive and accessible shared UI; no new per-project HTML or decorative external image dependencies.

## Owner decision 2026-11-26: records root

Canonical records live under `records/<area>/...` with sibling logs and generated indexes. `openwiki/` is documentation only: design, ADR, guides, journal migration input and plain Markdown notes do not need v1 frontmatter. New writes use `records/...` paths. Legacy v1 records were migrated with `MOVED` events; do not move them back or recreate the old authoring path.

## Owner decision 2026-11-26: notes requested in chat

When the owner asks in chat for a daily, trip or other personal note, write it through the `knowledge-hub-local` MCP writer as `visibility: public` with `publish_current: true`, and let auto-merge land it on `main`. Treat that request as explicit authorization to publish the note in this repository: do not ask for confirmation and do not offer a private/local alternative for this category. Set `status: stable` explicitly; the writer's `draft` create default is only for records that still need review. If the note has a date, include a matching `reminders` tuple, because Today, Upcoming and Calendar are built from reminders rather than `occurred_on`.

## Test execution policy (owner decision 2026-11-18)

Keep `validate-openwiki` as a required **fast** CI check for schema/record/log validation, deterministic projections, privacy/publication checks, build smoke tests and JavaScript syntax. Do **not** re-add Playwright Chromium/WebKit installs, `tools/diary/test_ui.py` or `tools/diary/test_ios12.py` to the required CI job. Run these suites only on demand locally via `sh tools/diary/run_local_ui_checks.sh` after one-time Playwright setup. Physical original iPad Air Safari 12 verification is a separate manual, device-local acceptance tracked by issue #2; neither a CI skip nor modern WebKit proves iPad acceptance. See `docs/acceptance/ipad-local.md`.

`tools/records/check_publication_events.py` is part of that required fast job (#126) and compares `base..HEAD` so historical un-allowlisted events keep passing. It is deliberately **not** part of `.githooks/pre-commit`, because the writer commits the record and its event before the trusted adapter adds the matching allowlist entry in a separate commit, so a staged-file hook would fail the record commit that must come first.

## Pull request CI handoff

- Do not treat a PR with pending checks as complete or promise to resume the same chat spontaneously. After opening/updating a PR, link its checks; let the CI-completion handoff workflow record the final result on the PR and return to that PR for review.
- `.github/workflows/ci-pr-handoff.yml` listens for completion of `Validate OKF and diary` on open same-repository PRs. It updates a single bot comment with the checked commit, result, and run link, skipping stale heads and forks. It never checks out PR code, runs untrusted artifacts, invokes an AI agent, or merges.
- After CI completion, a reviewer/agent should inspect failures, scope, current head and evidence before merging. `knowledge-merge-gate` is advisory and is not a required status; `validate-openwiki` remains required. No GitHub approval is required under the owner amendment in issue #24. New agent auto-dispatch requires an explicitly configured agent integration; a GitHub comment alone cannot resume ChatGPT.
- Owner decision 2026-11-21 (issue #114): pull-request publication is opt-in through trusted launch configuration (`--pr-base`, plus `--auto-merge`). Both default off; non-PR and read-only launches are unchanged. Auto-merge is squash-only for the pull request just ensured and never bypasses required checks, including `validate-openwiki`.
- Owner decision 2026-11-21 (issue #126), amended 2026-11-26: in PR publication mode, a new event of a `visibility: public` record already present in `config/publication.json` is allowlisted automatically as an extra commit on the same publication branch, before the PR is ensured. With the opt-in `--auto-allowlist-new-records` launch flag, a `create` with `publish_current: true` also allowlists the new public record ID and its CREATED event. Only `record_ids`/`event_ids` may change as described, never a private record or wildcard; a failed allowlist push leaves the PR open without auto-merge. See [W-06](openwiki/design/records-and-writes.md).

## Record minimization and one active project per repository (owner decision 2026-11-19)

- Update one existing canonical project record per GitHub repository; at most one project record associated with that repository may have `status: in_progress` within the same authorized source. Persistent active status does not depend on recent activity. Raise a validation error or an explicit deduplication proposal when a second active parent is attempted.
- Capture routine project summaries, stand-ups, PR and issue status, decisions about ongoing work, blockers, next steps and checks by updating that record **with a matching append-only sibling log event**; do not generate a new dated journal record for each update.
- Keep separately addressable design documents, enduring decisions and unique source notes where their independent identity is necessary. Link them from the parent, rather than duplicating its mutable status. Never infer that similar titles or dates mean duplicate content.
- Consolidation must preserve stable IDs, exact source bytes, legacy aliases and all event chains. Deprecate and redirect true duplicates only after migration review and privacy checks; never delete unique history or import `visibility: private` source into public just to reduce a count.
- Transitional public-demo and historical private-labelled records are separate visibility domains until private data migration is complete. `visibility: private` in the public repo provides no confidentiality. See the 2026-11-19 [Knowledge Hub public project recap](openwiki/projects/knowledge-hub-public.md).


## Evidence links and derived backlinks (owner decision 2026-11-19)

- Each canonical project record MUST link to the actual evidence that supports its status: source repository, exact GitHub issues/PRs, commit/revision, validation runs and related record IDs where available. A record link uses stable `record:<uuid>` rather than a mutable file path. Distinguish planned, verified, and stale evidence.
- Link from an existing project to other genuinely related canonical records; do not create an extra record merely for references. Retain the original source URL and stable event/record ID in the log. Do not copy entire issue bodies, PRs, or evidence files into Markdown.
- Reverse links are **derived** from authorized current outgoing links in the read model (the `backlinks` field). Do not independently author reciprocal bookkeeping fields or update unrelated records simply to maintain reverse links. Two project records may mutually link when their relationship is meaningful.
- For source GitHub issues/PRs, place a concise link back to the canonical knowledge record in the issue/PR when appropriate; respect repo permissions and avoid flooding threads with repetitive comments. Always include the exact validation run for any claim that checks passed.
- Generate every incoming-link list **after** the same privacy filtering applied to current records. Exclude unpublished/private source records, hidden targets, and inaccessible metadata. Preserve historical links in immutable logged revisions and alias mappings; a move or deprecation must not destroy the evidence trail.
- Validate traversal: record -> linked record -> source evidence -> logged version; inverse record lookup; missing and revoked references; deterministic sort/dedup; no public/private inference leaks. Pending external integration must be marked unverified, not fabricated.
