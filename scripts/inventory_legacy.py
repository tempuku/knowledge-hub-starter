#!/usr/bin/env python3
"""Issue #35: fail-closed, reproducible source inventory; never migrates or publishes."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def build(revision):
    paths = git("ls-tree", "-r", "--name-only", revision, "--", "openwiki").splitlines()
    sources = [p for p in paths if p.endswith(".md") and pathlib.PurePosixPath(p).name != "index.md"]
    items = []
    for path in sorted(sources):
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", revision + ":" + path])
        log = path.endswith(".log.md") or pathlib.PurePosixPath(path).name == "log.md"
        sibling = path[:-7] + ".md" if path.endswith(".log.md") else path[:-3] + ".log.md"
        items.append({
            "old_path": path,
            "disposition": None,
            "destination_path": None,
            "allocated_record_id": None,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "legacy_log_path": path if log else (sibling if sibling in sources else None),
            "legacy_event_ids": [],
            "legacy_ui_ids": [],
            "project_mapping": None,
            "metadata_mapping": None,
            "occurrence_source": None,
            "review_notes": "UNREVIEWED: classify and reconcile source bytes and history; do not migrate."
        })
    return {"schema_version": 1, "base_revision": revision, "review_status": "pending",
            "items": items}

def check_snapshots(revision, root=None):
    repository = pathlib.Path(root or ROOT)
    def read_git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args])
    paths = read_git("ls-tree", "-r", "--name-only", "-z", revision, "--", "openwiki").decode().split("\0")
    paths = [path for path in paths if path]
    paired = mismatches = errors = 0
    for log_path in sorted(p for p in paths if p.endswith(".log.md")):
        record_path = log_path[:-7] + ".md"
        if record_path not in paths:
            errors += 1
            print(f"ERROR {log_path}: sibling record {record_path} is missing")
            continue
        log_bytes = read_git("show", revision + ":" + log_path)
        entries = []
        for match in re.finditer(rb"```json\n(.*?)\n```", log_bytes, re.S):
            try:
                entries.append(json.loads(match.group(1)))
            except (ValueError, UnicodeError) as exc:
                errors += 1
                print(f"ERROR {log_path}: malformed JSON event: {exc}")
        if not entries:
            errors += 1
            print(f"ERROR {log_path}: no parseable JSON events")
            continue
        final = entries[-1]
        if type(final) is not dict or type(final.get("after")) is not str:
            errors += 1
            print(f"ERROR {log_path}: final event has no string after snapshot")
            continue
        source = read_git("show", revision + ":" + record_path)
        after = final["after"].encode("utf-8")
        paired += 1
        if source != after:
            mismatches += 1
            print(f"MISMATCH {record_path} source_bytes={len(source)} source_sha256={hashlib.sha256(source).hexdigest()} "
                  f"after_bytes={len(after)} after_sha256={hashlib.sha256(after).hexdigest()}")
    print(f"Snapshot comparison: {paired} paired histories; {paired - mismatches} match; {mismatches} mismatch; {errors} malformed/missing")
    return mismatches + errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True, help="Frozen full commit SHA")
    ap.add_argument("--output", default="migration/records-v1.json")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-snapshots", action="store_true",
                      help="compare every paired native final after snapshot with frozen source bytes")
    args = ap.parse_args()
    if args.check_snapshots:
        sys.exit(1 if check_snapshots(args.revision) else 0)
    data = build(args.revision)
    output = ROOT / args.output
    encoded = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not output.exists() or output.read_text() != encoded:
            sys.exit("FAIL: inventory is stale or was manually modified; regenerate against frozen revision")
        print(f"PASS: {len(data['items'])} sources exactly accounted for; all mappings remain pending review")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded)
        print(f"Wrote {output}: {len(data['items'])} source entries; no migration or publication")
if __name__ == "__main__":
    main()
