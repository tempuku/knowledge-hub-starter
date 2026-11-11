# Working rules

- Treat `openwiki/` as the current OKF v0.2 bundle; `dist/` is generated and ignored by Git. **ADR 0001** (`openwiki/adr/0001-private-records-authenticated-app.md`) defines the target move of private records to a separate private repository; this migration is not yet implemented.
- Read `openwiki/design/overview.md` and its linked contracts before implementing storage or UI changes. The target is hierarchical canonical records plus sibling logs, with the diary generated from logs only. Existing date-folder records are migration input: preserve them until the reviewed migration, and do not create a competing target authoring path.
- Never use Git commit timestamps as factual occurrence dates. The target Diary groups by recorded UTC change time; optional occurred_on/occurred_at are separate author-supplied facts. Correcting a factual date requires a logged update.
- Keep links to original issues, PRs, repositories, decisions and other evidence in `sources` and in Markdown; do not reproduce sources as if they were independent evidence.
- Entries should be `status: draft` until reviewed; do not invent verification.
- All personal records default to `visibility: private`, but this field **does not secure files in a public Git repository**. Do not put new personal notes in this public source repo. No public publishing without explicit authorization and allowlist review.
- Add every new concept to its directory `index.md`. New directories require an `index.md` and a parent index entry.
- Existing directory `log.md` files are migration input, not the target history store. Use the per-record sibling log contract; structural index pages have no history events.
- Run the same staged OKF checker as `ivanovo_models` before committing. The checker reads staged files.
- Do not duplicate huge `log.md` files, JSON catalog content, or HTML apps for each project.
- Preserve the user-approved visual direction: **early iOS 5–6 skeuomorphic app** (blue glossy navigation, segmented controls, grouped lists, subtle linen texture). Keep one CSS-driven, responsive and accessible shared UI; no new per-project HTML or decorative external image dependencies.

## Pull request CI handoff

- Do not treat a PR with pending checks as complete or promise to resume the same chat spontaneously. After opening/updating a PR, link its checks; let the CI-completion handoff workflow record the final result on the PR and return to that PR for review.
- `.github/workflows/ci-pr-handoff.yml` listens for completion of `Validate OKF and diary` on open same-repository PRs. It updates a single bot comment with the checked commit, result, and run link, skipping stale heads and forks. It never checks out PR code, runs untrusted artifacts, invokes an AI agent, or merges.
- After CI completion, an authorized reviewer/agent must inspect failures, scope, approvals and current head before merging. New agent auto-dispatch requires an explicitly configured agent integration; a GitHub comment alone cannot resume ChatGPT.
