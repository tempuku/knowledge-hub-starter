"""Read-only candidate migration reconciliation report (M-04).

Requires a fully migrated native-only candidate and the reviewed frozen-source
manifest. It never writes to Git refs or publishes a generation; all source
content stays in local memory and only aggregate counts/digests leave the tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projection"))
from git_source import load_revision
from reconcile_v1 import ReconciliationError, reconcile


def git_bytes(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode:
        raise ReconciliationError("Required reviewed source or candidate Git blob missing")
    return result.stdout


def _load_reviewed(root, revision):
    try:
        data = git_bytes(root, "show", revision + ":migration/records-v1.json")
        review = json.loads(data.decode("utf-8", "strict"))
    except (ValueError, UnicodeError) as exc:
        raise ReconciliationError("Reviewed manifest invalid") from exc
    return review, hashlib.sha256(data).hexdigest()


def report(root, revision):
    root = Path(root).resolve(strict=True)
    commit, tree, records, histories, _ = load_revision(
        root, revision, strict_native=True)
    review, digest = _load_reviewed(root, commit)
    base = review.get("base_revision")
    if not isinstance(base, str) or len(base) not in (40, 64):
        raise ReconciliationError("Reviewed manifest missing frozen source revision")
    sources = {}
    for item in review["items"]:
        path = item["old_path"]
        if (not isinstance(path, str) or not path.startswith("openwiki/") or
                "\\" in path or ":" in path or ".." in path.split("/")):
            raise ReconciliationError("Unsafe reviewed source path")
        sources[path] = git_bytes(root, "show", base + ":" + path)

    # Archive may preserve old path spelling, but matching requires exact
    # original bytes, not a substring, title or similar content.
    archived_paths = git_bytes(
        root, "ls-tree", "-r", "--name-only", "-z",
        commit, "--", "migration/legacy").split(b"\0")
    archive_hashes = set()
    for value in filter(None, archived_paths):
        path = value.decode("utf-8", "strict")
        archive_hashes.add(hashlib.sha256(
            git_bytes(root, "show", commit + ":" + path)).hexdigest())
    outcome = reconcile(review, sources, archive_hashes, records, histories)
    return {"schema_version": 1, "source_revision": commit,
            "source_tree": tree, "reviewed_base_revision": base,
            "reviewed_manifest_sha256": digest, **outcome}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = report(args.root, args.revision)
        target = args.report_json.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print("cutover reconciliation OK: " + json.dumps(result, sort_keys=True))
    except (ReconciliationError, ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"cutover reconciliation: FAIL: {exc}\n")


if __name__ == "__main__":
    main()
