# Public projection privacy acceptance map

This file maps the publication boundary to executable tests. It is a test plan, not a report of a passed run. The exact commit and CI run must be recorded by the implementation PR; local test output alone does not establish completion.

The repository CI runs these suites with verbose discovery:

```sh
python -m unittest discover -s tools/records -p 'test_*.py' -v
python -m unittest discover -s tools/projection -p 'test_*.py' -v
```

| Contract | Executable evidence | Required assertion |
|---|---|---|
| P5 / P-04: private-before, public-after event | `test_publication.PolicyTests.test_private_before_public_after_never_exported`; `test_privacy_acceptance.PrivacyAcceptanceTests.test_real_git_public_and_private_generations_have_independent_audit` | A real immutable Git build excludes the transition history and its private snapshot. |
| P6 / P-04: public current record without published history | `test_privacy_acceptance.PrivacyAcceptanceTests.test_real_git_public_and_private_generations_have_independent_audit` | The current public record remains in the catalog with zero published events. |
| P7 / P-04: public allowlist revocation | `test_privacy_acceptance.PrivacyAcceptanceTests.test_real_git_public_and_private_generations_have_independent_audit` | A committed policy change produces a new generation without the revoked record, events, reminders, alias targets or counts. |
| P8 / P-04: actor and reference boundary | `test_privacy_acceptance.PrivacyAcceptanceTests.test_real_git_public_and_private_generations_have_independent_audit`; `test_privacy_acceptance.PrivacyAcceptanceTests.test_missing_unknown_mode_and_missing_policy_fail_closed` | Approved actor labels survive; unapproved labels fall back to Contributor; internal actor, operation and provenance identifiers are redacted; current links to hidden targets are rewritten; an allowed event that still carries a known private ID fails the real build. |
| P15: complete byte and metadata audit | `test_privacy_acceptance.PrivacyAcceptanceTests.test_real_git_public_and_private_generations_have_independent_audit`; `test_publication.PolicyTests.test_public_byte_audit_detects_ids_and_paths`; `test_publication.PolicyTests.test_public_artifact_path_is_audited`; `test_publication.PolicyTests.test_malformed_private_snapshot_audit_fails_closed`; `test_publication.PolicyTests.test_filtered_alias_targets_and_keys_are_forbidden` | Public generated JSON and root manifest are inventoried by SHA-256 under the policy digest; known private IDs, paths, bodies and metadata are denied in artifact bytes and paths. Private output receives a separate inventory and retains the private fixture. |
| S20 / W-04: default-private write to a public checkout | `test_service_v1.ServiceFixtures.test_public_default_private_denied`; `test_service_v1.ServiceFixtures.test_public_writes_never_modify_publication_policy`; `test_writer_v1.WriterPrimitiveFixtures.test_public_capability_fails_closed` | A real writer service rejects a default-private create in public repository mode; authorized public create/update leave the committed publication policy byte-for-byte unchanged and return pending. Frontmatter visibility alone does not grant permission. |

The real-Git acceptance fixture is synthetic and contains no user data. It records public and private generations independently. The test verifies every generated JSON path, each artifact SHA-256, the root manifest bytes, policy digests, and a populated moved-path alias before and after revocation. No deployment, external publication, erasure claim, or human content review is implied by these tests.

CI may set `KH_ACCEPTANCE_REPORT_DIR` to preserve `privacy-builds.json` as an artifact. It contains the synthetic fixture revision/tree hash, generation IDs, expected and observed record/event/reminder/alias counts, policy digests, and SHA-256 inventories for the public, private, and revoked-public generations. Artifact names include the actual `g/<generation>/...` prefix plus `manifest.json`. It never stores source bodies or raw snapshots.
