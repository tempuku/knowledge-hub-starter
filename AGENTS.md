# Working rules

- Treat `openwiki/` as the authoritative OKF v0.2 bundle; `dist/` is generated and ignored by Git.
- Preserve dated entries as atomic concept files in `openwiki/journal/YYYY/MM/DD/<slug>.md`.
- Never parse Git commit timestamps to claim event occurrence dates. Use `occurred_on` (YYYY-MM-DD) and preserve the original value on later revisions.
- Keep links to original issues, PRs, repositories, decisions and other evidence in `sources` and in Markdown; do not reproduce sources as if they were independent evidence.
- Entries should be `status: draft` until reviewed; do not invent verification.
- All personal records default to `visibility: private`. No public publishing without explicit authorization and allowlist review.
- Add every new concept to its directory `index.md`. New directories require an `index.md` and a parent index entry.
- Keep `log.md` scopes short (e.g. per month); it is optional human-readable change history, not the website's database.
- Run the same staged OKF checker as `ivanovo_models` before committing. The checker reads staged files.
- Do not duplicate huge `log.md` files, JSON catalog content, or HTML apps for each project.
- Preserve the user-approved visual direction: **early iOS 5–6 skeuomorphic app** (blue glossy navigation, segmented controls, grouped lists, subtle linen texture). Keep one CSS-driven, responsive and accessible shared UI; no new per-project HTML or decorative external image dependencies.
