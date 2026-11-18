#!/usr/bin/env python3
"""#36 frozen-source migration rehearsal. Disposable candidate ONLY.

Never write to the source repository or a deployment. Archive legacy evidence
ONLY in the disposable private candidate; do not push that candidate or upload
its source/archive/bundle as a public CI artifact.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_inventory import validate as validate_inventory
sys.path.insert(0, str(ROOT / "tools/records"))
from validate_v1 import parse_record, parse_log, validate_chain, date_or_time

DEFAULT_TIME = "2026-11-18T12:00:00Z"
FENCE = re.compile(r"## Entry ([^\n]+)\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60(?:\n|$)", re.DOTALL)
MARKDOWN_LINK = re.compile(r"(?P<before>!?\[[^\]\n]*\]\()(?P<target>[^)\s]+)(?P<after>\))")


class RehearsalError(ValueError):
    pass


def demand(predicate, reason):
    if not predicate:
        raise RehearsalError(reason)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *argv, binary=False, env=None):
    proc = subprocess.run(["git", *argv], cwd=root, capture_output=True, env=env)
    if proc.returncode:
        raise RehearsalError("git " + " ".join(argv) + ": " +
                             proc.stderr.decode("utf-8", "replace")[:180])
    return proc.stdout if binary else proc.stdout.decode().strip()


def source_bytes(root, base, relative):
    demand(relative.startswith("openwiki/") and ".." not in PurePosixPath(relative).parts,
           "unsafe source path")
    return git(root, "show", base + ":" + relative, binary=True)


def legacy_log(raw, name):
    text = raw.decode("utf-8", "strict")
    demand(text.startswith("# OKF Record Change Log\n"), "unknown legacy log format: " + name)
    events = []
    for match in FENCE.finditer(text):
        obj = json.loads(match.group(2))
        demand(type(obj) is dict and obj.get("id") == match.group(1),
               "legacy event heading mismatch: " + name)
        for part in ("before", "after"):
            snapshot = obj.get(part)
            expected = obj.get(part + "_sha256")
            demand((snapshot is None and expected is None) or
                   (type(snapshot) is str and sha256(snapshot.encode()) == expected),
                   "unverified legacy snapshot digest: " + name)
        events.append(obj)
    demand(len(events) == text.count("## Entry "), "unparsed legacy log entries: " + name)
    return events


def normalized_body(raw, item, old_to_id, base):
    source = raw.decode("utf-8", "strict").replace("\r\n", "\n")
    if source.startswith("---\n"):
        end = source.find("\n---\n", 4)
        demand(end != -1, "unclosed legacy frontmatter")
        body = source[end + 5:]
    else:
        body = source
    output = []
    in_fence = False
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("\x60\x60\x60", "~~~")):
            in_fence = not in_fence
        if in_fence:
            output.append(line)
            continue

        def replace(match):
            target = match.group("target")
            if (match.group("before").startswith("!") or
                    target.startswith(("#", "record:", "https://", "http://", "mailto:"))):
                return match.group(0)
            demand(not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) and
                   not target.startswith("/") and
                   not any(c in target for c in ("%", "?", "\\")),
                   "unsafe legacy relative Markdown link: " + target)
            part, sep, fragment = target.partition("#")
            resolved = posixpath.normpath(posixpath.join(
                posixpath.dirname(item["old_path"]), part))
            suffix = ("#" + fragment) if sep else ""
            if resolved in old_to_id:
                updated = "record:" + old_to_id[resolved] + suffix
            elif resolved.startswith("openwiki/") and resolved.endswith("/index.md"):
                updated = posixpath.relpath(resolved, posixpath.dirname(item["destination_path"])) + suffix
            else:
                # Preserve non-record/removed legacy references as frozen evidence.
                demand(".." not in PurePosixPath(resolved).parts, "escaped source link")
                updated = ("https://github.com/tempuku/knowledge-hub-starter/blob/" +
                           base + "/" + quote(resolved, safe="/") + suffix)
            return match.group("before") + updated + match.group("after")

        output.append(MARKDOWN_LINK.sub(replace, line))
    return "".join(output).rstrip("\n") + "\n"


def normalized_record(raw, item, old_to_id, base):
    meta = item["metadata_mapping"]
    demand(type(meta) is dict, "missing approved metadata")
    fields = {"id": item["allocated_record_id"], "schema_version": 1}
    for name in ("type", "title", "description", "status", "visibility", "tags",
                 "sources", "reminders", "occurred_on", "occurred_at", "x_legacy"):
        if name in meta:
            fields[name] = meta[name]
    if item.get("project_mapping"):
        mapping = item["project_mapping"]
        project_id = mapping.get("record_id")
        if fields["type"] != "project" and project_id is not None:
            fields["project_id"] = project_id
        elif mapping.get("x_legacy_project") is not None:
            # Reviewed external project has no v1 project record.
            fields.setdefault("x_legacy", {})["project"] = mapping["x_legacy_project"]
        elif fields["type"] == "project" and mapping.get("x_legacy_project_id"):
            # Project identity is its record UUID, not a self-reference.
            fields.setdefault("x_legacy", {})["project_id"] = mapping["x_legacy_project_id"]
        else:
            demand(False, "unresolved project mapping")
    body = normalized_body(raw, item, old_to_id, base)
    converted = "---\n" + yaml.safe_dump(fields, sort_keys=False, allow_unicode=True,
                                            width=10000) + "---\n" + body
    parse_record(converted.encode(), item["destination_path"])
    return converted


def reviewed_occurrence(snapshot, item):
    """Keep factual dates only if actually present in a historical snapshot."""
    if not snapshot.startswith("---\n"):
        return None, None
    end = snapshot.find("\n---\n", 4)
    if end == -1:
        return None, None
    try:
        original = yaml.load(snapshot[4:end], Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise RehearsalError("invalid legacy occurrence metadata") from exc
    if not isinstance(original, dict):
        return None, None
    day, when = original.get("occurred_on"), original.get("occurred_at")
    if day is not None:
        date_or_time(day, "original occurred_on")
    if when is not None:
        date_or_time(when, "original occurred_at", False)
        demand(day == when[:10], "inconsistent historical occurrence")
    return day, when


def event(record_id, allocation, sequence, action, before, after, dest,
          timestamp, kind, ref, original_time, actor, summary, previous,
          occurred_on=None, occurred_at=None):
    return {
        "schema_version": 1, "id": allocation["allocated_event_id"],
        "record_id": record_id, "operation_id": allocation["allocated_operation_id"],
        "sequence": sequence, "action": action, "recorded_at": timestamp,
        "occurred_on": occurred_on, "occurred_at": occurred_at,
        "actor": actor, "summary": summary[:240],
        "path_before": dest if before is not None else None, "path_after": dest,
        "before": before, "after": after,
        "before_sha256": sha256(before.encode()) if before is not None else None,
        "after_sha256": sha256(after.encode()), "previous_event_id": previous,
        "idempotency_key": allocation["allocated_idempotency_key"],
        "request_sha256": sha256(json.dumps(
            [record_id, allocation["allocated_event_id"], ref], ensure_ascii=False).encode()),
        "provenance": {"kind": kind, "source_ref": ref, "original_time": original_time},
    }


def encode_log(events):
    return "# Record history\n\n" + "\n".join(
        "## Entry " + e["id"] + "\n\x60\x60\x60json\n" +
        json.dumps(e, ensure_ascii=False, indent=2) + "\n\x60\x60\x60\n"
        for e in events)


def history(root, manifest, item, time):
    base = manifest["base_revision"]
    record_id = item["allocated_record_id"]
    dest = item["destination_path"]
    mappings = [m for m in manifest["legacy_event_mappings"] if m["record_id"] == record_id]
    repairs = [r for r in manifest["backfill_repair_plan"] if r["record_id"] == record_id]
    if not item["legacy_log_path"]:
        baseline = next((a for a in manifest["imported_baseline_allocations"]
                         if a["record_id"] == record_id), None)
        demand(baseline is not None and not mappings, "unreviewed missing history")
        raw = source_bytes(root, base, item["old_path"])
        demand(sha256(raw) == baseline["source_sha256"], "unreviewed baseline content")
        return [event(record_id, baseline, 1, "IMPORTED", None, raw.decode("utf-8"),
                      dest, time, "legacy-journal", baseline["source_ref"], None,
                      {"id": "migration", "kind": "migration", "label": "Migration"},
                      "Preserve independent legacy journal summary", None)]
    originals = legacy_log(source_bytes(root, base, item["legacy_log_path"]),
                           item["legacy_log_path"])
    demand([o["id"] for o in originals] == item["legacy_event_ids"] ==
           [m["legacy_event_id"] for m in mappings], "unreviewed history mapping: " + dest)
    sequence = [("legacy", obj, m) for obj, m in zip(originals, mappings)]
    for repair in repairs:
        before = git(root, "show", repair["git_commit"] + "^:" + item["old_path"], binary=True)
        after = git(root, "show", repair["git_commit"] + ":" + item["old_path"], binary=True)
        demand(sha256(before) == repair["before_sha256"] and
               sha256(after) == repair["after_sha256"] and
               len(before) == repair["before_bytes"] and
               len(after) == repair["after_bytes"], "Git repair does not match original evidence")
        anchor = next((n for n, (_kind, obj, _) in enumerate(sequence)
                       if obj["id"] == repair["insert_after_legacy_event_id"]), None)
        demand(anchor is not None, "missing Git repair anchor")
        following = repair["insert_before_legacy_event_id"]
        if following:
            demand(anchor + 1 < len(sequence) and sequence[anchor+1][1]["id"] == following,
                   "invalid Git repair insertion order")
        synthetic = {"id": repair["allocated_event_id"],
                     "before": before.decode(), "after": after.decode()}
        sequence.insert(anchor + 1, ("repair", synthetic, repair))
    events = []
    for kind, obj, mapping in sequence:
        n = len(events) + 1
        demand(mapping["target_sequence"] == n, "reviewed sequence allocation mismatch")
        before, after = obj.get("before"), obj["after"]
        demand(type(after) is str and
               (not events and before is None or events and before == events[-1]["after"]),
               "history gap not covered by approved Git repair: " + dest)
        if kind == "legacy":
            demand(all(obj.get(key) == mapping[mkey] for key, mkey in
                       (("timestamp", "original_time"), ("action", "source_action"),
                        ("actor", "source_actor"), ("summary", "source_summary"))),
                   "legacy provenance mismatch")
            rule = mapping["recorded_at_rule"]
            demand(rule in {"fixed-migration-time", "preserve-original-recording-time"},
                   "unknown reviewed timestamp rule")
            when = time if rule == "fixed-migration-time" else mapping["original_time"]
            action = "IMPORTED" if mapping["source_action"] == "BASELINED" else mapping["source_action"]
            actor_label = str(mapping["source_actor"]).replace("\n", " ")[:100]
            actor = {"id": "legacy-agent", "kind": "agent", "label": actor_label}
            if action == "IMPORTED":
                actor = {"id": "migration", "kind": "migration", "label": actor_label}
            provenance = mapping["provenance_kind"]
            ref = mapping["source_ref"]
            original_time = mapping["original_time"]
            summary = mapping["source_summary"]
        else:
            when, action, provenance, original_time = time, "UPDATED", "git-backfill", None
            ref = item["old_path"] + "#git-backfill-" + mapping["git_commit"]
            actor = {"id": "migration", "kind": "migration", "label": "Git backfill"}
            summary = "Recover exact reviewed Git-backed revision"
        demand(not events or when >= events[-1]["recorded_at"],
               "nonmonotonic converted timestamp")
        factual_day, factual_time = (reviewed_occurrence(after, item)
                                    if kind == "legacy" else (None, None))
        events.append(event(record_id, mapping, n, action, before, after, dest,
                            when, provenance, ref, original_time, actor, summary,
                            events[-1]["id"] if events else None,
                            occurred_on=factual_day, occurred_at=factual_time))
    return events


def update_indexes(candidate):
    """Maintain exact direct-child coverage; preserve non-list index prose."""
    files = sorted(p.relative_to(candidate).as_posix()
                   for p in (candidate / "openwiki").rglob("*.md")
                   if not p.name.endswith(".log.md") and p.name != "log.md")
    folders = defaultdict(set)
    for path in files:
        folder, leaf = path.rsplit("/", 1)
        if leaf != "index.md":
            folders[folder].add(leaf)
        # Existing structural index-only directories still count as children:
        # the v1 validator traverses their ancestors, even without records.
        while folder != "openwiki":
            parent, name = folder.rsplit("/", 1)
            folders[parent].add(name + "/")
            folder = parent
    for folder, names in sorted(folders.items()):
        target = candidate / folder / "index.md"
        if target.exists():
            original = target.read_text(encoding="utf-8")
            # Preserve explanatory text but drop stale structural link bullets.
            original = re.sub(r"(?m)^[*-] \[[^\]\n]+\]\([^)]+\)\s*\n?", "", original)
            preamble = original.rstrip("\n") + "\n\n"
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            preamble = "# " + folder.rsplit("/", 1)[-1].replace("-", " ").title() + "\n\n"
        target.write_text(preamble + "".join(
            "- [" + name + "](" + name + ")\n" for name in sorted(names)), encoding="utf-8")


def convert(source, manifest_file, output, expected_head, time=DEFAULT_TIME):
    source, output = Path(source).resolve(), Path(output).resolve()
    demand(not output.exists(), "disposable output already exists; refusing overwrite")
    demand(source != output and source not in output.parents and output not in source.parents,
           "output must not overlap source")
    date_or_time(time, "fixed migration time", False)
    demand(time.endswith("Z"), "migration clock must be UTC")
    manifest_bytes = Path(manifest_file).read_bytes()
    manifest = json.loads(manifest_bytes)
    base = manifest["base_revision"]
    demand(expected_head == base and git(source, "rev-parse", "HEAD") == expected_head,
           "EXPECTED_HEAD_MISMATCH: re-inventory/re-dry-run before migration")
    demand(git(source, "status", "--porcelain") == "", "frozen source checkout is dirty")
    problems = validate_inventory(manifest, source)
    demand(not problems, "reviewed manifest validation failed: " + "; ".join(problems[:5]))
    items = manifest["items"]
    old_to_id = {i["old_path"]: i["allocated_record_id"] for i in items
                 if i["disposition"] in ("record", "summary-note")}
    targets = list(i["destination_path"] for i in items if i["destination_path"])
    demand(len(targets) == len(set(targets)), "duplicate destination")
    source_copy = {}
    for item in items:
        raw = source_bytes(source, base, item["old_path"])
        demand(sha256(raw) == item["source_sha256"], "source sha256 mismatch: " + item["old_path"])
        source_copy[item["old_path"]] = raw
    git(source, "clone", "--no-hardlinks", "--quiet", str(source), str(output))
    try:
        git(output, "checkout", "--detach", "--quiet", base)
        demand(git(output, "rev-parse", "HEAD") == expected_head,
               "source changed during clone")
        archived = {}
        all_events = {}
        for item in items:
            old = item["old_path"]
            raw = source_copy[old]
            # Original bytes are PRIVATE candidate evidence, not public exported data.
            archive_path = "migration/legacy/" + old
            archived[old] = sha256(raw)
            archive_file = output / archive_path
            archive_file.parent.mkdir(parents=True, exist_ok=True)
            archive_file.write_bytes(raw)
            if item["disposition"] == "structural":
                # Legacy sibling history is superseded; its exact bytes were archived.
                (output / old).unlink()
                continue
            dest = item["destination_path"]
            converted = normalized_record(raw, item, old_to_id, base)
            events = history(source, manifest, item, time)
            allocation = next((a for a in manifest["normalization_event_allocations"]
                               if a["record_id"] == item["allocated_record_id"]), None)
            demand(allocation is not None and allocation["target_sequence"] == len(events) + 1,
                   "missing final normalization allocation")
            final = event(item["allocated_record_id"], allocation, len(events) + 1,
                          "IMPORTED", events[-1]["after"], converted, dest, time,
                          "legacy-journal" if item["disposition"] == "summary-note" else "legacy-log",
                          old, None,
                          {"id": "migration", "kind": "migration", "label": "Migration"},
                          "Migrate record to hierarchical storage", events[-1]["id"])
            events.append(final)
            # Validate converted chain before mutating source candidate paths.
            meta, text = parse_record(converted.encode(), dest)
            validate_chain(events, dest, meta, text, set())
            all_events[item["allocated_record_id"]] = events
            if old != dest:
                (output / old).unlink()
            record = output / dest
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_bytes(converted.encode())
            log_path = output / (dest[:-3] + ".log.md")
            log_path.write_bytes(encode_log(events).encode())
        # Keep frozen reviewed aliases, separate from historical snapshots.
        aliases = {"schema_version": 1, "source_revision": base,
                   "paths": {i["old_path"]: [i["allocated_record_id"]] for i in items
                             if i["disposition"] in ("record", "summary-note")},
                   "entries": {a["legacy_ui_id"]: a["event_id"]
                               for a in manifest["legacy_ui_mappings"] if a["event_id"] is not None},
                   "current_entries": {a["legacy_ui_id"]: a["record_id"]
                                       for a in manifest["legacy_ui_mappings"] if a["event_id"] is None}}
        path_aliases = output / "migration" / "aliases-v1.json"
        path_aliases.write_text(json.dumps(aliases, indent=2, ensure_ascii=False,
                                           sort_keys=True) + "\n", encoding="utf-8")
        (output / "migration" / "legacy" / "sha256.json").write_text(
            json.dumps(archived, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        policy = manifest["publication_eligibility"]
        demand(policy["policy"] == "reviewed-proposal-only-no-deployment-authorization",
               "public eligibility requires new review")
        (output / "config" / "publication.json").write_text(
            json.dumps({"schema_version": 1, "record_ids": policy["record_ids"],
                        "event_ids": policy["event_ids"],
                        "actor_labels": policy["actor_labels"]},
                       indent=2, sort_keys=True) + "\n", encoding="utf-8")
        update_indexes(output)
        git(output, "add", "-A")
        from validate_v1 import repository
        result = repository(output, strict_indexes=True)
        demand(result["records"] >= len(all_events), "not all migrated records validated")
        demand(result["events"] >= sum(len(x) for x in all_events.values()), "lost migrated events")
        env = dict(__import__("os").environ)
        env.update({"GIT_AUTHOR_NAME": "Knowledge Hub rehearsal",
                    "GIT_AUTHOR_EMAIL": "rehearsal@example.invalid",
                    "GIT_COMMITTER_NAME": "Knowledge Hub rehearsal",
                    "GIT_COMMITTER_EMAIL": "rehearsal@example.invalid",
                    "GIT_AUTHOR_DATE": time, "GIT_COMMITTER_DATE": time})
        git(output, "commit", "-qm", "Disposable #36 frozen-source migration candidate", env=env)
        report = {"schema_version": 1, "scope": "DISPOSABLE-PRIVATE-ONLY",
                  "base_revision": base, "expected_head": expected_head,
                  "manifest_sha256": sha256(manifest_bytes),
                  "candidate_tree": git(output, "rev-parse", "HEAD^{tree}"),
                  "candidate_commit": git(output, "rev-parse", "HEAD"),
                  "source_count": len(items), "record_count": len(all_events),
                  "legacy_event_count": len(manifest["legacy_event_mappings"]),
                  "backfill_count": len(manifest["backfill_repair_plan"]),
                  "normalization_count": len(manifest["normalization_event_allocations"]),
                  "migrated_event_count": sum(len(events) for events in all_events.values()),
                  "legacy_ui_mapping_count": len(manifest["legacy_ui_mappings"]),
                  "archived_source_hashes": archived,
                  "validation": result,
                  "publication_policy": "preview-only; never deploy"}
        return report
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="clean disposable Git checkout at manifest's frozen revision")
    parser.add_argument("--manifest", default=str(ROOT / "migration/records-v1.json"), type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--fixed-time", default=DEFAULT_TIME)
    parser.add_argument("--report", type=Path, help="write digest-only report outside public deployment")
    args = parser.parse_args()
    try:
        result = convert(args.source, args.manifest, args.output,
                         args.expected_head, args.fixed_time)
        text = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if args.report:
            args.report.write_text(text, encoding="utf-8")
        print(text)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, "rehearsal failed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
