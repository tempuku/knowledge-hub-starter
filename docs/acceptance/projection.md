# Projection acceptance map

This file maps the requested #31 scenarios to real-Git tests. It describes executable coverage, not a claim of deployed acceptance. CI runs the projection tests through `python -m unittest discover -s tools/projection -p 'test_*.py' -v`.

| Contract | Executable evidence | Required assertion |
|---|---|---|
| P1: deterministic build | `test_acceptance_p31.ProjectionAcceptance.test_p1_complete_generation_is_byte_deterministic` | Repeated builds from one immutable Git source, exporter and policy have identical generated file bytes and hashes. |
| P2: no-Git native projection | `test_acceptance_p31.ProjectionAcceptance.test_p2_bundle_rebuild_survives_without_git_metadata` | Complete source bundle and externally pinned receipt rebuild the same current record, history, diff, catalog, search, reminder and alias views after `.git` is unavailable. Tampered bundle/blob/receipt inputs fail closed. |
| P2: complete output schemas and source-derived links | `test_acceptance_p31.ProjectionAcceptance.test_p02_full_models_schemas_sizes_links_aliases_and_search_body`; `test_acceptance_p31.ProjectionAcceptance.test_p02_current_markdown_relative_links_resolve_from_git_path_map` | Generated JSON follows explicit schema/count/size contracts; body search excludes frontmatter and history; canonical and relative current links resolve; moved paths and legacy source references produce validated aliases. |
| P3: 51-event paging and counts | `test_acceptance_p31.ProjectionAcceptance.test_p3_fifty_one_writer_events_have_exact_pages_and_counts` | Page boundaries are 50 and 1, totals remain 51 changes/1 distinct record, and every event occurs once. |
| P3: 128-KiB paging boundary | `test_acceptance_p31.ProjectionAcceptance.test_p3_real_record_catalog_splits_at_128_kibibytes` | Record catalog pages split before the uncompressed byte budget and preserve all rows/counts. |
| P3: current body-only search | `test_acceptance_p31.ProjectionAcceptance.test_p03_full_body_unicode_and_filters_use_only_current_search_fields`; `test_acceptance_p31.ProjectionAcceptance.test_p03_oversized_search_shard_fails_closed` | Unicode body tokens, ranking and filters are deterministic; metadata noise, Markdown link destinations, source URLs and historical snapshots are not indexed, while visible link labels remain searchable; oversized shards fail rather than truncate. |
| P4: historical status from each snapshot | `test_acceptance_p31.ProjectionAcceptance.test_p4_current_completion_does_not_rewrite_earlier_revision` | Current record reports completed while earlier event/revision remains draft. |
| P9: failed publication preserves live data | `test_acceptance_p31.ProjectionAcceptance.test_p9_malformed_committed_source_keeps_live_manifest_and_generation`; `test_acceptance_p31.ProjectionAcceptance.test_p9_bom_and_crlf_native_headers_fail_closed`; `test_acceptance_p31.ProjectionAcceptance.test_p9_orphan_log_keeps_live_manifest_and_generation` | Malformed source/logs (including BOM/CRLF headers) and orphan native logs fail without replacing the last manifest or mutating its generation. |
| P14: reminders across calendar boundaries | `test_acceptance_p31.ProjectionAcceptance.test_p14_reminder_ranges_preserve_inclusive_months_year_and_offset` | Inclusive written-date ranges cover each intersecting month/year and preserve exact timestamp offset strings. |
| Source validation gaps | `test_acceptance_p31.ProjectionAcceptance.test_unresolved_project_reference_fails_before_projection` | A project reference must resolve to a current record of type project before projection. |
| Current public link boundary | `test_acceptance_p31.ProjectionAcceptance.test_public_current_links_require_currently_eligible_target`; `test_acceptance_p31.ProjectionAcceptance.test_public_link_to_private_target_is_redacted_without_reference_leak` | Eligible links keep their record IDs. Ineligible targets become “Unavailable in this view” without target ID, path, title or fragment in the public output. |

The tests use disposable synthetic repositories and do not read or publish user records. A successful local test run does not establish live publication, UI behavior, migration reconciliation or performance acceptance.

## No-Git bundle interface

Export the immutable source tree and detached receipt from a Git checkout:

```sh
python3 tools/projection/sourcebundle.py \
  --root /path/to/knowledge-hub-starter --revision <commit> \
  --output /secure/source-bundle.json --receipt-output /secure/source-receipt.json
```

The receipt digest must be carried through a trusted channel independently of the bundle. The no-Git build requires that exact lowercase SHA-256 pin and reads policy, canonical records and sibling histories only from the verified bundle:

```sh
python3 tools/projection/build.py --destination /secure/read-model \
  --bundle /secure/source-bundle.json --receipt /secure/source-receipt.json \
  --receipt-sha256 <trusted-receipt-sha256>
```

The bundle contains the complete recursive tree manifest and embedded blobs. Its loader reconstructs the Git tree hash, verifies every embedded Git blob object ID and size, validates the detached receipt, then reparses raw record and log bytes through the same schema and chain validators used for Git builds. It never trusts serialized record summaries from the bundle.
