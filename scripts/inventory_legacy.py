#!/usr/bin/env python3
"""Issue #35: fail-closed, reproducible source inventory; never migrates or publishes."""
import argparse
import hashlib
import json
import pathlib
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True, help="Frozen full commit SHA")
    ap.add_argument("--output", default="migration/records-v1.json")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
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
