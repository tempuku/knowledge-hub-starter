---
id: 820d2f86-8f25-486d-afc0-214c5291f4bf
schema_version: 1
type: guide
title: Agent workflow for the knowledge bundle
description: "How an agent should create, update, validate and publish records in this repository."
status: draft
visibility: public
tags: [agents, openwiki, workflow, ci, publication]
---

# Agent workflow for this knowledge bundle

Operational checklist for an agent editing this repository. Read `AGENTS.md`,
`openwiki/index.md`, `openwiki/design/overview.md` and
`openwiki/design/records-and-writes.md` before writing. When this note and the
normative design disagree, the design wins.

## 1. Record model

- One Markdown record plus one sibling `<slug>.log.md` file. The log is the
  append-only history; the record is the current snapshot.
- New records use v1: `id` (UUIDv4), `schema_version: 1`, `type`, `title`,
  `status`, `visibility`, optional `description`, `tags`, `sources`.
- Allowed status values: `draft`, `stable`, `in_progress`, `completed`,
  `deprecated`. Default new records to `draft`.
- `visibility` is `private` or `public`. In this public repository the label is
  metadata, not confidentiality.
- Every new page needs an entry in its directory `index.md`; a new directory
  needs an `index.md` and a parent index entry.
- Never rewrite or delete history. No hard delete, no editing earlier events.

## 2. Create a record

1. Generate a fresh UUIDv4 for the record and one for the event.
2. Write the record with a final newline and LF endings.
3. Write the log. It starts with the `# Record history` title, then one section
   per event: an H2 heading whose text is `Entry` plus the event UUID, followed
   by a fenced `json` block containing the event object. The JSON is indented
   with two spaces and ends with a blank line before the next section.

4. The event object uses exactly these keys: `schema_version`, `id`,
   `record_id`, `operation_id`, `sequence`, `action`, `recorded_at`,
   `occurred_on`, `occurred_at`, `actor`, `summary`, `path_before`,
   `path_after`, `before`, `after`, `before_sha256`, `after_sha256`,
   `previous_event_id`, `idempotency_key`, `request_sha256`, `provenance`.
5. `action: CREATED`, `sequence: 1`, `path_before: null`, `before: null`,
   `before_sha256: null`, `previous_event_id: null`.
6. `after` is the exact record text; `after_sha256` is its SHA-256.
   `recorded_at` is UTC `YYYY-MM-DDTHH:MM:SSZ`.
   `provenance` is `{"kind": "native", "source_ref": null, "original_time": null}`.
7. Serialize the event with two-space indentation and literal non-ASCII
   (`json.dumps(event, ensure_ascii=False, indent=2)`). The validator compares
   bytes to that canonical form.

## 3. Update a record

- Append one `UPDATED` event. `sequence` increments, `previous_event_id` is the
  prior event's `id`, `path_before` equals `path_after` for an in-place edit.
- `before` is the previous event's `after`; `before_sha256` must match it.
- Change `status` only with an explicit write and a summary that says why.
- Marking a record superseded is an `UPDATED` with a body note. `ARCHIVED`
  requires `status: deprecated`; beware that free-text tokens from a hidden
  record can poison unrelated public pages (see section 5).

## 4. Validate before committing

```sh
sh tools/okf/setup.sh                  # once per checkout
git add <paths>
sh .githooks/pre-commit                # staged OKF + index check
python3 tools/records/validate_v1.py --base "$(git merge-base HEAD origin/main)"
```

For anything that may be published, also run the exporter locally:

```sh
python3 tools/diary/build.py --public-only --output-dir /tmp/kh-public
python3 tools/diary/publish_v1.py --output-dir /tmp/kh-public
python3 tools/diary/test_build.py --output-dir /tmp/kh-public --public-only
python3 tools/diary/test_publication.py /tmp/kh-public
```

The v1 validator needs PyYAML; install it outside the repository if needed.

## 5. Publication rules and traps

Publishing is an explicit allowlist in `config/publication.json`: sorted,
unique `record_ids`, `event_ids` and `actor_labels`. A record is exported only
when its ID is allowlisted **and** its current visibility is `public`. An event
is exported only when its ID is allowlisted, its `after` snapshot is public and
its `before` is null or public.

Consequences an agent must plan for:

- **A record created private cannot publish its history later.** The first
  publishable event after a private interval would reference a denylisted event
  ID in `previous_event_id`. Create the public record with a public `CREATED`
  snapshot; do not try to promote a private draft.
- **Do not rewrite the CREATED snapshot or delete a record.** CI's trusted-base
  check rejects a changed history prefix and a removed record identity.
  Supersede with a body note, or create a separate `*-public` record.
- **Denylisted strings are matched as substrings.** Omitting a private record
  forbids its whole snapshot, body and every metadata value of 8+ characters,
  plus actor IDs and operation digests. A shorter URL is contained in a longer
  one, so use genuinely non-overlapping values.
- **Short common metadata is safer.** A status such as `deprecated` (10
  characters) becomes a forbidden token and can match unrelated public prose.
- **Redaction happens for selected events only.** Actor IDs and command digests
  are replaced with `redacted` in exported events; do not rely on them being
  hidden if you also copy them into prose.

## 6. Pull request and CI

- Work on a branch, commit with a conventional message, push, and open a PR
  against `main`. Do not force-push `main`.
- `validate-openwiki` is the required status. `knowledge-merge-gate` is
  advisory: it requires a linked issue with checked evidence boxes. Under the
  owner policy it does not block a merge, but do not describe a red gate as
  green.
- The Pages job rebuilds the public projection. A passing `validate-openwiki`
  does not prove the publish audit passes; run section 4 locally first.

## 7. Content and privacy

- No credentials, tokens, prompts, payloads, personal data or private project
  content in any record, log, summary or evidence link.
- `visibility: private` files are still readable in this public repository.
- Link sources; do not paste whole issues or private evidence.

## 8. When blocked

If the publication audit rejects a record, do not bypass it or disable the
check. Record the exact failure, prefer a new public record over rewriting
history, and escalate the design gap in a PR description.
