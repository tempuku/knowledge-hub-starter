"""Immutable Git-tree source loader for the native v1 projection (#31).

Uses git show <commit>:<path> only; never reads mutable working-tree files.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from deterministic import ProjectionError


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode:
        raise ProjectionError("Git source failure: " + result.stderr.decode("utf-8", "replace"))
    return result.stdout


def load_revision(root: Path, revision: str):
    """Return (commit, tree, records, histories, summaries) after v1 validation."""
    source_root = Path(root).resolve()
    tools_dir = Path(__file__).resolve().parents[1] / "records"
    sys.path.insert(0, str(tools_dir))
    import validate_v1 as validator

    commit = git(source_root, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    tree = git(source_root, "rev-parse", commit + "^{tree}").decode().strip()
    paths = git(source_root, "ls-tree", "-r", "--name-only", "-z", commit, "--", "openwiki").decode("utf-8").split("\0")
    records, histories, summaries = [], {}, {}
    seen_ids = set()
    for path in sorted(filter(None, paths)):
        if not path.endswith(".md") or path.endswith(".log.md") or path.rsplit("/", 1)[-1] in ("index.md", "log.md"):
            continue
        raw = git(source_root, "show", f"{commit}:{path}")
        if not raw.startswith(b"---\n"):
            continue
        head = raw[:4096].split(b"\n---\n", 1)[0]
        if b"schema_version:" not in head or b"id:" not in head:
            continue  # v0 legacy record; migration is a separate gate
        meta, canonical = validator.parse_record(raw, path)
        log_path = path[:-3] + ".log.md"
        events = validator.parse_log(git(source_root, "show", f"{commit}:{log_path}"), log_path)
        validator.validate_chain(events, path, meta, canonical, seen_ids)
        rid = meta["id"]
        if rid in histories:
            raise ProjectionError("duplicate canonical record ID")
        histories[rid] = events
        record = {"id": rid, "title": meta["title"], "description": meta.get("description", ""),
                  "type": meta["type"], "status": meta["status"],
                  "project_id": meta.get("project_id"), "tags": meta.get("tags", []),
                  "area": path[len("openwiki/"):].rsplit("/", 1)[0],
                  "updated_at": events[-1]["recorded_at"], "version": len(events),
                  "content_bytes": len(raw), "content": canonical, "path": path,
                  "reminders": meta.get("reminders", [])}
        records.append(record)
        for event in events:
            after_meta, _ = validator.frontmatter(event["after"])
            summaries[event["id"]] = {
                "id": event["id"], "record_id": rid, "operation_id": event["operation_id"],
                "sequence": event["sequence"], "action": event["action"],
                "recorded_at": event["recorded_at"], "occurred_on": event["occurred_on"],
                "occurred_at": event["occurred_at"], "summary": event["summary"],
                "title": after_meta.get("title", "Unknown"),
                "status": after_meta.get("status", "Unknown"),
                "project_id": after_meta.get("project_id"),
                "tags": after_meta.get("tags", []),
                "actor_label": event["actor"]["label"],
                "provenance_kind": event["provenance"]["kind"],
                "type": after_meta.get("type", "Unknown"),
                "area": event["path_after"][len("openwiki/"):].rsplit("/", 1)[0]}
    return commit, tree, records, histories, summaries
