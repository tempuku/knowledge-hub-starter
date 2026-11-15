"""Integrated #31 acceptance tests over committed writer-generated Git data.

These exercise the complete source-to-read-model build. Fixture records and
logs are produced with the real v1 writer and committed to disposable repos;
they are not hand-built mocks of projection output.
"""
from __future__ import annotations

import hashlib
import base64
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

from build import publish
from compose import build_projection
from deterministic import PAGE_BYTES, ProjectionError, json_bytes, query_search, search_shards
from git_source import load_revision
from acceptance_fixture import GitFixture, note, uid
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "records"))
import writer_v1


def decode(files: dict[str, bytes], path: str):
    return json.loads(files[path].decode("utf-8"))


def stable_files(files: dict[str, bytes]):
    """Published JSON bytes exclude the deliberately time-varying manifest."""
    return {path: body for path, body in sorted(files.items())}


class ProjectionAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.repo = GitFixture(self.root)
        self._report_data = {"expected": {}, "observed": {}}
        self._source_tree_hash = None
        self._content_hashes = {}
        self._last_build_files = None

    def tearDown(self):
        report_dir = os.environ.get("KH_ACCEPTANCE_REPORT_DIR")
        if not report_dir or not self.repo.last_revision:
            return
        outcome = getattr(self, "_outcome", None)
        result = getattr(outcome, "result", None)
        test_id = self.id()
        failed = bool(result and any(case.id() == test_id for case, _ in result.failures + result.errors))
        if failed:
            return
        fixture_commit = self.repo.last_revision
        if self._source_tree_hash is None:
            try:
                self._source_tree_hash = subprocess.run(
                    ["git", "rev-parse", fixture_commit + "^{tree}"], cwd=self.root,
                    check=True, capture_output=True, text=True).stdout.strip()
            except Exception:
                self._source_tree_hash = None
        observed = dict(self._report_data.get("observed", {}))
        if "record_count" not in observed:
            observed["fixture_record_count"] = len(self.repo.records)
            observed["fixture_event_count"] = sum(map(len, self.repo.events.values()))
        payload = {
            "schema_version": 1,
            "scenario": self._testMethodName,
            "outcome": "passed",
            "fixture_commit": fixture_commit,
            "source_revision": fixture_commit,
            "source_tree_hash": self._source_tree_hash,
            "expected": self._report_data.get("expected", {}),
            "observed": observed,
            "generation_content_sha256": dict(sorted(self._content_hashes.items())),
        }
        target_dir = Path(report_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / f"{self._testMethodName}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def evidence(self, *, expected: dict, observed: dict,
                 generated_files: dict[str, bytes] | None = None):
        self._report_data = {"expected": expected, "observed": observed}
        if generated_files is not None:
            self._content_hashes = {
                path: hashlib.sha256(raw).hexdigest()
                for path, raw in sorted(generated_files.items())
            }

    def published_files(self, destination: Path, manifest: dict) -> dict[str, bytes]:
        generation = destination / manifest["root"]
        files = {path.relative_to(generation).as_posix(): path.read_bytes()
                 for path in generation.rglob("*") if path.is_file()}
        self._content_hashes = {path: hashlib.sha256(raw).hexdigest()
                                for path, raw in sorted(files.items())}
        return files

    def inputs(self, revision="HEAD"):
        commit, tree, records, histories, summaries = load_revision(self.root, revision)
        self._source_tree_hash = tree
        return commit, tree, records, histories, summaries

    def build(self, revision="HEAD"):
        _, _, records, histories, summaries = self.inputs(revision)
        files = build_projection(records, histories, summaries)
        self._last_build_files = files
        self._content_hashes = {path: hashlib.sha256(raw).hexdigest()
                                for path, raw in sorted(files.items())}
        return files

    def test_p1_complete_generation_is_byte_deterministic(self):
        self.repo.add_record("openwiki/notes/one.md", note("Café", "Résumé body\n"),
                             recorded_at="2026-11-12T08:00:00Z")
        revision = self.repo.commit()
        first = stable_files(self.build(revision))
        second = stable_files(self.build(revision))
        self.assertEqual(first.keys(), second.keys())
        self.assertEqual({k: __import__("hashlib").sha256(v).hexdigest() for k, v in first.items()},
                         {k: __import__("hashlib").sha256(v).hexdigest() for k, v in second.items()})
        self.assertEqual(first, second)
        catalog = decode(first, "catalog.json")
        self.evidence(expected={"record_count": 1, "event_count": 1},
                      observed={"record_count": catalog["record_count"],
                                "event_count": catalog["event_count"]}, generated_files=first)

    def test_p2_bundle_rebuild_survives_without_git_metadata(self):
        """A copied source tree without .git is built using a hash-pinned bundle."""
        self.repo.add_record("openwiki/notes/one.md", note("Portable", "Bundle body\n"),
                             recorded_at="2026-11-12T08:00:00Z")
        revision = self.repo.commit()
        destination = Path(self.temp.name) / "portable"
        copy = Path(self.temp.name) / "copied-source"
        shutil.copytree(self.root, copy, ignore=shutil.ignore_patterns(".git"))
        self.assertFalse((copy / ".git").exists())
        # The bundle/receipt are exported from the source revision by the
        # implementation's bundle helper, then consumed with an external pin.
        from sourcebundle import create_bundle
        bundle = Path(self.temp.name) / "source-bundle.json"
        receipt = Path(self.temp.name) / "source-receipt.json"
        result = create_bundle(self.root, revision, bundle, receipt)
        manifest = publish(None, destination, bundle=bundle, receipt=receipt,
                           receipt_sha256=result["receipt_digest"])
        generation = destination / manifest["root"]
        self.assertTrue((generation / "catalog.json").is_file())
        catalog = decode({p.relative_to(generation).as_posix(): p.read_bytes()
                          for p in generation.rglob("*.json")}, "catalog.json")
        rid = next(iter(self.repo.records))
        self.assertEqual(catalog["record_count"], 1)
        self.assertIn("Bundle body", (generation / f"records/{rid}.json").read_text())
        self.assertTrue((generation / f"events/{self.repo.events[rid][0]['id']}.json").is_file())
        bundled_files = self.published_files(destination, manifest)
        untrusted_destination = Path(self.temp.name) / "untrusted-bundle"
        with self.assertRaises(ProjectionError):
            publish(None, untrusted_destination, bundle=bundle, receipt=receipt,
                    receipt_sha256="0" * 64)
        self.assertFalse((untrusted_destination / "manifest.json").exists())
        self.assertFalse((untrusted_destination / "g").exists())

        # Altering bundle bytes without changing the out-of-band receipt pin
        # is rejected before any publication state is created.
        tampered_bytes_path = Path(self.temp.name) / "tampered-bundle-bytes.json"
        tampered_bytes_path.write_bytes(bundle.read_bytes() + b" ")
        altered_bytes_destination = Path(self.temp.name) / "altered-bundle-bytes"
        with self.assertRaises(ProjectionError):
            publish(None, altered_bytes_destination, bundle=tampered_bytes_path,
                    receipt=receipt, receipt_sha256=result["receipt_digest"])
        self.assertFalse((altered_bytes_destination / "manifest.json").exists())

        # Even if a producer recomputes the bundle digest and detached receipt,
        # changing raw source bytes is caught by recomputing the Git blob OID.
        bundle_obj = json.loads(bundle.read_text(encoding="utf-8"))
        source_entry = next(item for item in bundle_obj["manifest"]
                            if item["path"] == "openwiki/notes/one.md")
        oid = source_entry["oid"]
        blob = base64.b64decode(bundle_obj["blobs"][oid])
        self.assertIn(b"Bundle body", blob)
        bundle_obj["blobs"][oid] = base64.b64encode(
            blob.replace(b"Bundle body", b"Bungle body", 1)).decode("ascii")
        from hashlib import sha256
        rewritten_bundle_bytes = json_bytes(bundle_obj)
        rewritten_bundle = Path(self.temp.name) / "rewritten-blob-bundle.json"
        rewritten_bundle.write_bytes(rewritten_bundle_bytes)
        receipt_obj = json.loads(receipt.read_text(encoding="utf-8"))
        receipt_obj["bundle_digest"] = sha256(rewritten_bundle_bytes).hexdigest()
        rewritten_receipt_bytes = json_bytes(receipt_obj)
        rewritten_receipt = Path(self.temp.name) / "rewritten-blob-receipt.json"
        rewritten_receipt.write_bytes(rewritten_receipt_bytes)
        rewritten_pin = sha256(rewritten_receipt_bytes).hexdigest()
        rewritten_destination = Path(self.temp.name) / "rewritten-blob-publication"
        with self.assertRaises(ProjectionError):
            publish(None, rewritten_destination, bundle=rewritten_bundle,
                    receipt=rewritten_receipt, receipt_sha256=rewritten_pin)
        self.assertFalse((rewritten_destination / "manifest.json").exists())
        self.assertFalse((rewritten_destination / "g").exists())
        self.evidence(expected={"git_metadata_present": False, "record_count": 1,
                                "event_count": 1, "wrong_receipt_pin_rejected": True,
                                "bundle_digest_tamper_rejected": True,
                                "rehashed_blob_tamper_rejected": True},
                      observed={"git_metadata_present": (copy / ".git").exists(),
                                "record_count": catalog["record_count"],
                                "event_count": catalog["event_count"],
                                "wrong_receipt_pin_rejected": not (untrusted_destination / "manifest.json").exists(),
                                "bundle_digest_tamper_rejected": not (altered_bytes_destination / "manifest.json").exists(),
                                "rehashed_blob_tamper_rejected": not (rewritten_destination / "manifest.json").exists()},
                      generated_files=bundled_files)

    def test_p3_fifty_one_writer_events_have_exact_pages_and_counts(self):
        title = "Long chain"
        initial = note(title, "revision 1\n")
        rid = self.repo.add_record("openwiki/notes/chain.md", initial,
                                   recorded_at="2026-11-12T08:00:00Z")
        current = self.repo.records[rid]["content"]
        edits = []
        for index in range(2, 52):
            current = current.replace(f"revision {index - 1}\n", f"revision {index}\n")
            edits.append((current, "2026-11-12T08:00:00Z"))
        # Append actual updates in order by extending the fixture's committed
        # writer state; this keeps all 51 event objects in the canonical log.
        record = self.repo.records.pop(rid)
        events = self.repo.events.pop(rid)
        log = self.repo.files.pop(record["path"][:-3] + ".log.md")
        self.repo.files.pop(record["path"])
        # Rebuild as a single writer operation chain with deterministic IDs.
        for snapshot, at in edits:
            prior = events[-1]
            request = writer_v1.normalized_request({
                "command": "update", "idempotency_key": self.repo._id(),
                "actor": {"id": "fixture-actor", "kind": "agent", "label": "Fixture"},
                "summary": "Update acceptance record", "expected_head": "a" * 40,
                "record_id": rid, "expected_version": prior["id"], "content": snapshot,
            })
            event = writer_v1.make_event(request, record_id=rid,
                event_id=self.repo._id(), operation_id=self.repo._id(),
                sequence=len(events) + 1, action="UPDATED", path_before=record["path"],
                path_after=record["path"], before=prior["after"], after=snapshot,
                previous_event_id=prior["id"], recorded_at=at)
            log = writer_v1.append_log(log, event)
            events.append(event)
        self.repo.events[rid] = events
        self.repo.records[rid] = {**record, "content": current}
        self.repo.files[record["path"]] = current
        self.repo.files[record["path"][:-3] + ".log.md"] = log
        self.repo.commit("51 event chain")
        files = self.build()
        history = decode(files, f"history/{rid}/index.json")
        pages = [decode(files, f"history/{rid}/{item['number']}.json")
                 for item in history["pages"]]
        ids = [event["id"] for page in pages for event in page["items"]]
        self.assertEqual(history["event_count"], 51)
        self.assertEqual([len(page["items"]) for page in pages], [50, 1])
        self.assertEqual(set(ids), {event["id"] for event in events})
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(decode(files, "catalog.json")["event_count"], 51)
        day = decode(files, "days/2026-11-12/index.json")
        self.assertEqual((day["change_count"], day["record_count"]), (51, 1))
        self.evidence(expected={"event_count": 51, "history_page_counts": [50, 1],
                                "day_record_count": 1},
                      observed={"event_count": decode(files, "catalog.json")["event_count"],
                                "history_page_counts": [len(page["items"]) for page in pages],
                                "day_record_count": day["record_count"]},
                      generated_files=files)

    def test_p3_real_record_catalog_splits_at_128_kibibytes(self):
        expected = set()
        for number in range(50):
            tags = ["a" * 54 + f"-{number:04d}-{tag:04d}" for tag in range(32)]
            source = ("---\ntype: note\n"
                      f'title: "Catalog item {number:02d} ' + "T" * 170 + '"\n'
                      'description: "' + "D" * 490 + '"\n'
                      "tags:\n" + "".join(f'  - "{tag}"\n' for tag in tags) +
                      "---\n\nCatalog body\n")
            expected.add(self.repo.add_record(
                f"openwiki/notes/item-{number:02d}.md", source,
                recorded_at="2026-11-12T08:00:00Z"))
        self.repo.commit("catalog page budget")
        files = self.build()
        index = decode(files, "records/catalog/index.json")
        self.assertEqual(index["record_count"], 50)
        self.assertGreater(len(index["pages"]), 1)
        items = []
        for descriptor in index["pages"]:
            page_bytes = files[descriptor["url"]]
            self.assertLessEqual(len(page_bytes), PAGE_BYTES)
            page = json.loads(page_bytes)
            self.assertEqual(len(page["items"]), descriptor["count"])
            items.extend(page["items"])
        self.assertEqual({item["id"] for item in items}, expected)
        self.assertEqual(len(items), len(expected))
        self.evidence(expected={"record_count": 50, "catalog_pages": 2,
                                "page_bytes_max": PAGE_BYTES},
                      observed={"record_count": index["record_count"],
                                "catalog_pages": len(index["pages"]),
                                "page_bytes_max_observed": max(
                                    len(files[item["url"]]) for item in index["pages"])},
                      generated_files=files)

    def test_p4_current_completion_does_not_rewrite_earlier_revision(self):
        draft = note("Milestone", "Draft body\n", status="draft")
        completed = draft.replace("status: draft", "status: completed").replace("Draft body", "Final body")
        self.repo.add_record("openwiki/projects/milestone.md", draft,
            recorded_at="2026-11-12T08:00:00Z", edits=[(completed, "2026-11-12T09:00:00Z")])
        actual_rid = next(iter(self.repo.records))
        self.repo.commit()
        files = self.build()
        current = decode(files, f"records/{actual_rid}.json")
        history = decode(files, f"history/{actual_rid}/1.json")
        self.assertEqual(current["status"], "completed")
        self.assertIn("Final body", current["content"])
        self.assertEqual(history["items"][-1]["status"], "draft")
        self.assertEqual(history["items"][0]["status"], "completed")
        self.evidence(expected={"current_status": "completed", "first_revision_status": "draft"},
                      observed={"current_status": current["status"],
                                "first_revision_status": history["items"][-1]["status"]},
                      generated_files=files)

    def test_p02_full_models_schemas_sizes_links_aliases_and_search_body(self):
        target = self.repo.add_record(
            "openwiki/notes/target.md", note("Target", "## Overview\n\nTarget text\n"),
            recorded_at="2026-11-12T08:00:00Z")
        metadata = ('sources:\n'
                    '  - resource: "https://example.invalid/private-source-token"\n'
                    '    title: "Source page"\n')
        source = self.repo.add_record(
            "openwiki/ideas/source.md",
            note("Source", f"A link [Target](record:{target}#overview).\n", extra=metadata),
            recorded_at="2026-11-12T09:00:00Z")
        self.repo.mark_imported(target, "legacy-entry-003")
        self.repo.move_record(source, "openwiki/ideas/archive/source.md",
                              recorded_at="2026-11-12T10:00:00Z")
        revision = self.repo.commit("links and aliases")
        files = self.build(revision)

        # P-02 gives every generated JSON document a fixed, explicit outer
        # schema and UTF-8/LF serialization.
        for path, raw in files.items():
            if not path.endswith(".json"):
                continue
            self.assertTrue(raw.endswith(b"\n"), path)
            obj = json.loads(raw.decode("utf-8"))
            self.assertEqual(obj.get("schema_version"), 1, path)

        record_raw = files[f"records/{source}.json"]
        record = json.loads(record_raw)
        record_meta = decode(files, f"records/{source}.meta.json")
        self.assertEqual(record_meta["detail_bytes"], len(record_raw))
        self.assertNotIn("detail_bytes", record)
        self.assertEqual(record["content_bytes"], len(record["content"].encode("utf-8")))
        self.assertEqual(record["path"], "openwiki/ideas/archive/source.md")
        self.assertEqual(record["history_index"], f"history/{source}/index.json")
        self.assertEqual(record["links"], [{"target_id": target, "fragment": "overview",
                         "label": "Target", "available": True, "href": f"record:{target}#overview"}])

        aliases = decode(files, "aliases.json")
        self.assertEqual(aliases["paths"]["openwiki/ideas/source.md"], [source])
        self.assertIn("legacy-entry-003", aliases["entries"])
        self.assertEqual(aliases["entries"]["legacy-entry-003"], self.repo.events[target][0]["id"])

        create_id = self.repo.events[source][0]["id"]
        move_id = self.repo.events[source][-1]["id"]
        created = decode(files, f"events/{create_id}.json")
        moved = decode(files, f"events/{move_id}.json")
        self.assertIn("Target", created["diff"]["text"])
        self.assertEqual(moved["diff"]["text"], "")
        self.assertEqual(moved["revision_metadata"]["path_before"], "openwiki/ideas/source.md")
        self.assertEqual(moved["revision_metadata"]["path_after"], "openwiki/ideas/archive/source.md")
        self.assertEqual(decode(files, f"events/{move_id}.meta.json")["detail_bytes"],
                         len(files[f"events/{move_id}.json"]))

        # Frontmatter source URLs stay available in the current source bytes,
        # but only Markdown body fields feed search shards.
        self.assertIn("https://example.invalid/private-source-token", record["content"])
        search_manifest = decode(files, "search/manifest.json")
        indexed_terms = set()
        for shard in search_manifest["shards"]:
            indexed_terms.update(decode(files, shard["url"])["terms"])
        self.assertIn("link", indexed_terms)
        self.assertNotIn("private", indexed_terms)
        self.evidence(expected={"record_count": 2, "source_links": 1,
                                "aliases": {"moved_path": 1, "legacy_entry": 1}},
                      observed={"record_count": decode(files, "catalog.json")["record_count"],
                                "source_links": len(record["links"]),
                                "moved_path_aliases": len(aliases["paths"]),
                                "legacy_entry_aliases": len(aliases["entries"]),
                                "search_term_count": len(indexed_terms)},
                      generated_files=files)

    def test_p02_current_markdown_relative_links_resolve_from_git_path_map(self):
        target = self.repo.add_record("openwiki/notes/target.md",
            note("Relative target", "## Part\n\nTarget text\n"),
            recorded_at="2026-11-12T08:00:00Z")
        source = self.repo.add_record("openwiki/ideas/architecture/source.md",
            note("Relative source", "See [target](../../notes/target.md#part).\n"),
            recorded_at="2026-11-12T09:00:00Z")
        self.repo.commit()
        files = self.build()
        record = decode(files, f"records/{source}.json")
        self.assertEqual(record["links"], [{"target_id": target, "fragment": "part",
                         "label": "target", "available": True, "href": "../../notes/target.md#part"}])
        self.evidence(expected={"record_link_count": 1},
                      observed={"record_link_count": len(record["links"])},
                      generated_files=files)

    def test_relative_link_lookup_preserves_distinct_targets_with_same_label(self):
        first = self.repo.add_record("openwiki/notes/first.md",
            note("First", "First body\n"), recorded_at="2026-11-12T08:00:00Z")
        second = self.repo.add_record("openwiki/notes/second.md",
            note("Second", "## Part\n\nSecond body\n"), recorded_at="2026-11-12T08:01:00Z")
        source = self.repo.add_record("openwiki/notes/source.md",
            note("Source", "[Same](first.md) [Same](second.md#part)\n"),
            recorded_at="2026-11-12T09:00:00Z")
        self.repo.commit()
        record = decode(self.build(), f"records/{source}.json")
        self.assertEqual([(link["href"], link["target_id"]) for link in record["links"]],
                         [("first.md", first), ("second.md#part", second)])

    def test_p03_full_body_unicode_and_filters_use_only_current_search_fields(self):
        winner = self.repo.add_record(
            "openwiki/notes/alpha/winner.md",
            note("Café ranking", "lead\n" + "padding " * 600 +
                 "deepbodyomega visiblelabeltoken [visible linkword](https://example.invalid/bodyurltoken/pathunique)\n",
                 extra=('description: "Coffee map"\n'
                        'tags:\n  - "primary"\n'
                        'x_yaml_noise: "frontmatterghost"\n'
                        'sources:\n  - resource: "https://example.invalid/urlghost"\n')),
            recorded_at="2026-11-12T08:00:00Z")
        description_hit = self.repo.add_record(
            "openwiki/notes/alpha/description-hit.md",
            note("Other record", "ordinary body\n",
                 extra='description: "café omega"\ntags:\n  - "secondary"\n'),
            recorded_at="2026-11-12T09:00:00Z")
        title_hit = self.repo.add_record(
            "openwiki/notes/alpha/title-hit.md",
            note("Café Omega", "ordinary body\n", extra='tags:\n  - "primary"\n'),
            recorded_at="2026-11-12T09:30:00Z")
        body_hit = self.repo.add_record(
            "openwiki/notes/beta/body-hit.md",
            note("Body record", "café omega\n", extra='tags:\n  - "primary"\n'),
            recorded_at="2026-11-12T10:00:00Z")
        archived = self.repo.add_record(
            "openwiki/notes/old.md",
            note("Archived record", "café omega\n", status="deprecated",
                 extra='tags:\n  - "primary"\n'),
            recorded_at="2026-11-12T11:00:00Z")
        self.repo.commit("search coverage")
        _, _, records, _, _ = self.inputs()
        shards = search_shards(records)

        self.assertEqual(query_search("CAFÉ deepbodyomega", records, shards), [winner])
        self.assertEqual(query_search("café omega", records, shards),
                         [title_hit, description_hit, body_hit])
        self.assertEqual(query_search("café omega", records, shards,
                                      include_archived=True),
                         [title_hit, description_hit, archived, body_hit])
        self.assertEqual(query_search("café omega", records, shards, area="notes/alpha"),
                         [title_hit, description_hit])
        self.assertEqual(query_search("café omega", records, shards, tag="primary"),
                         [title_hit, body_hit])
        # Title weight outranks description and body when the other query
        # token is present in every result.
        self.assertEqual(query_search("café omega", records, shards),
                         [title_hit, description_hit, body_hit])
        terms = {term for payload in shards.values()
                 for term in json.loads(payload)["terms"]}
        self.assertNotIn("frontmatterghost", terms)
        self.assertNotIn("urlghost", terms)
        self.assertNotIn("bodyurltoken", terms)
        self.assertNotIn("pathunique", terms)
        self.assertIn("visiblelabeltoken", terms)
        self.assertIn("linkword", terms)
        self.assertIn("deepbodyomega", terms)
        self.assertEqual(len(query_search("one two three four five six seven eight",
                                          records, shards)), 0)
        with self.assertRaises(ProjectionError):
            query_search("one two three four five six seven eight nine", records, shards)
        self.evidence(expected={"and_query_results": 1, "eight_token_query_allowed": True,
                                "nine_token_query_rejected": True},
                      observed={"and_query_results": len(query_search(
                                    "CAFÉ deepbodyomega", records, shards)),
                                "eight_token_query_allowed": True,
                                "nine_token_query_rejected": True},
                      generated_files=self._last_build_files)

    def test_p03_oversized_search_shard_fails_closed(self):
        # Exercise the hard serialized-shard boundary with a large posting set;
        # no output is silently truncated or repartitioned under another rule.
        records = [{"id": f"fixture-record-{number:05d}", "title": "commonterm",
                    "description": "", "tags": [], "body": "", "status": "stable",
                    "area": "notes", "type": "note", "updated_at": "2026-11-12T00:00:00Z"}
                   for number in range(7000)]
        with self.assertRaisesRegex(ProjectionError, "exceeds 512 KiB"):
            search_shards(records)

    def test_public_current_links_require_currently_eligible_target(self):
        public_visibility = 'visibility: "public"\n'
        target = self.repo.add_record("openwiki/notes/target.md",
            note("Public target", "Target content\n", extra=public_visibility),
            recorded_at="2026-11-12T08:00:00Z")
        source = self.repo.add_record("openwiki/notes/source.md",
            note("Public source", f"See [target](record:{target}).\n", extra=public_visibility),
            recorded_at="2026-11-12T09:00:00Z")
        event_ids = [self.repo.events[rid][0]["id"] for rid in (source, target)]
        self.repo.files["config/publication.json"] = json.dumps({
            "schema_version": 1, "record_ids": sorted([source, target]),
            "event_ids": sorted(event_ids), "actor_labels": ["Fixture"],
        }, indent=2) + "\n"
        revision = self.repo.commit("allowlisted public linked records")
        destination = Path(self.temp.name) / "public-linked"
        manifest = publish(self.root, destination, revision, mode="public")
        generation = destination / manifest["root"]
        public_record = json.loads((generation / f"records/{source}.json").read_text())
        self.assertEqual(public_record["links"], [{"target_id": target, "fragment": None,
                         "label": "target", "available": True, "href": f"record:{target}"}])
        public_files = self.published_files(destination, manifest)
        self.evidence(expected={"eligible_current_link_count": 1},
                      observed={"eligible_current_link_count": len(public_record["links"])},
                      generated_files=public_files)

    def test_public_link_to_private_target_is_redacted_without_reference_leak(self):
        private_target_path = "openwiki/notes/private-target.md"
        target = self.repo.add_record(private_target_path,
            note("Private target title", "Private target body\n"),
            recorded_at="2026-11-12T08:00:00Z")
        source = self.repo.add_record("openwiki/notes/public-source.md",
            note("Public source", f"See [secret](record:{target}#private-fragment).\n",
                 extra='visibility: "public"\n'),
            recorded_at="2026-11-12T09:00:00Z")
        self.repo.files["config/publication.json"] = json.dumps({
            "schema_version": 1, "record_ids": [source],
            # The event's exact AFTER snapshot contains the private target ID;
            # keep it unallowlisted while testing the sanitized current view.
            "event_ids": [], "actor_labels": ["Fixture"],
        }, indent=2) + "\n"
        revision = self.repo.commit("public link to private target")
        destination = Path(self.temp.name) / "public-redacted-link"
        manifest = publish(self.root, destination, revision, mode="public")
        generation = destination / manifest["root"]
        redacted_files = self.published_files(destination, manifest)
        public_record = json.loads((generation / f"records/{source}.json").read_text())
        self.assertEqual(public_record["links"], [{
            "target_id": None, "fragment": None,
            "label": "Unavailable in this view", "available": False, "href": None,
        }])
        self.assertEqual(decode(redacted_files, f"history/{source}/index.json")["event_count"], 0)
        artifact_bytes = b"".join(path.read_bytes() for path in generation.rglob("*") if path.is_file())
        self.assertNotIn(target.encode(), artifact_bytes)
        self.assertNotIn(private_target_path.encode(), artifact_bytes)
        self.assertNotIn(b"Private target title", artifact_bytes)
        self.evidence(expected={"redacted_private_link_count": 1,
                                "private_target_reference_bytes": 0},
                      observed={"redacted_private_link_count": len(public_record["links"]),
                                "private_target_reference_bytes": sum(
                                    needle in artifact_bytes for needle in
                                    (target.encode(), private_target_path.encode(),
                                     b"Private target title"))},
                      generated_files=redacted_files)

    def test_p9_malformed_committed_source_keeps_live_manifest_and_generation(self):
        self.repo.add_record("openwiki/notes/valid.md", note("Valid"),
                             recorded_at="2026-11-12T08:00:00Z")
        good_revision = self.repo.commit()
        destination = Path(self.temp.name) / "published"
        prior = publish(self.root, destination, good_revision)
        prior_manifest = (destination / "manifest.json").read_bytes()
        prior_generation = destination / prior["root"]
        self.assertTrue(prior_generation.is_dir())

        log_path = "openwiki/notes/valid.log.md"
        self.repo.files[log_path] = self.repo.files[log_path] + "malformed tail\n"
        bad_revision = self.repo.commit("malformed log")
        with self.assertRaises((ProjectionError, ValueError)):
            publish(self.root, destination, bad_revision)
        self.assertEqual((destination / "manifest.json").read_bytes(), prior_manifest)
        self.assertTrue(prior_generation.is_dir())
        self.assertEqual(len(list((destination / "g").iterdir())), 1)
        prior_files = self.published_files(destination, prior)
        self.evidence(expected={"prior_manifest_preserved": True,
                                "prior_generation_preserved": True,
                                "published_generation_count": 1,
                                "live_source_revision": good_revision},
                      observed={"prior_manifest_preserved": (destination / "manifest.json").read_bytes() == prior_manifest,
                                "prior_generation_preserved": prior_generation.is_dir(),
                                "published_generation_count": len(list((destination / "g").iterdir())),
                                "live_source_revision": prior["source_revision"]},
                      generated_files=prior_files)

    def test_p9_bom_and_crlf_native_headers_fail_closed(self):
        record_path = "openwiki/notes/strict.md"
        log_path = "openwiki/notes/strict.log.md"
        self.repo.add_record(record_path, note("Strict source"),
                             recorded_at="2026-11-12T08:00:00Z")
        good_revision = self.repo.commit()
        destination = Path(self.temp.name) / "strict-headers"
        prior = publish(self.root, destination, good_revision)
        prior_manifest = (destination / "manifest.json").read_bytes()
        source, log = self.repo.files[record_path], self.repo.files[log_path]
        variants = {
            "BOM source": ("\ufeff" + source, log),
            "CRLF source": (source.replace("\n", "\r\n"), log),
            "BOM log": (source, "\ufeff" + log),
            "CRLF log": (source, log.replace("\n", "\r\n")),
        }
        for label, (bad_source, bad_log) in variants.items():
            with self.subTest(label=label):
                self.repo.files[record_path] = bad_source
                self.repo.files[log_path] = bad_log
                bad_revision = self.repo.commit(label)
                with self.assertRaises((ProjectionError, ValueError)):
                    publish(self.root, destination, bad_revision)
                self.assertEqual((destination / "manifest.json").read_bytes(), prior_manifest)
                self.assertTrue((destination / prior["root"]).is_dir())
                self.repo.files[record_path] = source
                self.repo.files[log_path] = log
                self.repo.commit("restore strict fixture")

    def test_p9_orphan_log_keeps_live_manifest_and_generation(self):
        orphan_root = Path(self.temp.name) / "orphan-repo"
        orphan_repo = GitFixture(orphan_root)
        orphan_repo.add_record("openwiki/notes/valid.md", note("Valid"),
                               recorded_at="2026-11-12T08:00:00Z")
        good_revision = orphan_repo.commit()
        destination = Path(self.temp.name) / "orphan-published"
        prior = publish(orphan_root, destination, good_revision)
        prior_manifest = (destination / "manifest.json").read_bytes()
        prior_generation = destination / prior["root"]

        orphan_repo.files["openwiki/notes/orphan.log.md"] = orphan_repo.files[
            "openwiki/notes/valid.log.md"]
        bad_revision = orphan_repo.commit("orphan history")
        with self.assertRaises((ProjectionError, ValueError)):
            publish(orphan_root, destination, bad_revision)
        self.assertEqual((destination / "manifest.json").read_bytes(), prior_manifest)
        self.assertTrue(prior_generation.is_dir())
        self.assertEqual(len(list((destination / "g").iterdir())), 1)
        prior_files = self.published_files(destination, prior)
        self.evidence(expected={"orphan_rejected": True, "prior_manifest_preserved": True,
                                "live_source_revision": good_revision},
                      observed={"orphan_rejected": True,
                                "prior_manifest_preserved": (destination / "manifest.json").read_bytes() == prior_manifest,
                                "live_source_revision": prior["source_revision"]},
                      generated_files=prior_files)

    def test_unresolved_project_reference_fails_before_projection(self):
        missing_project = uid(9000)
        source = ('---\ntype: note\ntitle: "Orphan project"\n'
                  f'project_id: "{missing_project}"\n---\n\nBody\n')
        self.repo.add_record("openwiki/notes/orphan-project.md", source,
                             recorded_at="2026-11-12T08:00:00Z")
        revision = self.repo.commit()
        with self.assertRaises(ProjectionError):
            self.inputs(revision)
        self.evidence(expected={"unresolved_project_rejected": True},
                      observed={"unresolved_project_rejected": True})

    def test_p14_reminder_ranges_preserve_inclusive_months_year_and_offset(self):
        reminders = (
            'reminders:\n'
            '  - [["2026-12-30", "2027-01-02"], "Year boundary"]\n'
            '  - ["2027-01-02T09:30:00-05:00", "Offset meeting"]\n'
        )
        rid = self.repo.add_record("openwiki/notes/reminders.md",
            note("Reminders", "Calendar details\n", extra=reminders),
            recorded_at="2026-12-01T00:00:00Z")
        self.repo.commit()
        files = self.build()
        dec = decode(files, "reminders/2026-12.json")["items"]
        jan = decode(files, "reminders/2027-01.json")["items"]
        self.assertEqual([x["record_id"] for x in dec], [rid])
        self.assertEqual([x["record_id"] for x in jan], [rid, rid])
        self.assertIn("2027-01-02T09:30:00-05:00", [x["when"] for x in jan])
        self.assertEqual(next(x for x in dec if x["text"] == "Year boundary")["end_date"], "2027-01-02")
        self.evidence(expected={"december_items": 1, "january_items": 2,
                                "preserved_offset": "-05:00"},
                      observed={"december_items": len(dec), "january_items": len(jan),
                                "preserved_offset": next(x["when"] for x in jan
                                    if x["text"] == "Offset meeting")[-6:]},
                      generated_files=files)


if __name__ == "__main__":
    unittest.main()
