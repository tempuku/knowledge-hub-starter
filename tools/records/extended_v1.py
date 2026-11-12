"""W-03 operations on the same transactional GitRecordWriter as W-02.

No alternate repository writer: GitRecordWriter.write delegates to this helper
only for move/archive/reopen. Every changed record gets exactly one native event,
all events in a move share one transaction operation ID and idempotency key.
"""
from __future__ import annotations

import subprocess
import tempfile
import uuid
from datetime import timezone
from pathlib import Path

from links_v1 import repair_relative_links
from validate_v1 import IntegrityError, parse_log, parse_record, repository
from writer_v1 import (WriterError, append_log, make_event, receipt_from_logs,
                       reject, require_record_permission)


def _status_source(source, status):
    """Change the current canonical status line without rewriting other bytes."""
    parsed, _ = parse_record(source.encode("utf-8"), "status candidate")
    lines = source.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        if line.strip() == "---" and idx > 0:
            break
        if line.startswith("status:"):
            right = line[len("status:"):].strip()
            quote = right[0] if right.startswith(("'", '"')) else ""
            changed = "status: " + quote + status + quote + "\n"
            lines[idx] = changed
            result = "".join(lines)
            meta, _ = parse_record(result.encode("utf-8"), "status candidate")
            if meta["id"] != parsed["id"] or meta["status"] != status:
                reject("INTEGRITY_ERROR", "Lifecycle changed unexpected metadata")
            return result
    reject("INTEGRITY_ERROR", "Canonical record has no status field")


def _current_records(writer, head):
    """Return strict v1 tracked records, not legacy v0.2 migration inputs."""
    from service_v1 import git
    paths = git(writer.root, "ls-tree", "-r", "--name-only",
                head, "--", "openwiki").splitlines()
    result = {}
    for path in paths:
        if (not path.endswith(".md") or path.endswith(".log.md") or
                path.rsplit("/", 1)[-1] in {"index.md", "log.md"}):
            continue
        raw = subprocess.check_output(
            ["git", "show", head + ":" + path], cwd=writer.root)
        if b"\nschema_version:" not in raw[:4096]:
            continue
        meta, content = parse_record(raw, path)
        if meta["id"] in {old[0]["id"] for old in result.values()}:
            reject("INTEGRITY_ERROR", "Duplicate canonical record identity")
        result[path] = (meta, content)
    return result, paths


def _write_permission(writer, meta, operation):
    require_record_permission(writer.capability, meta["id"])
    if (writer.capability["repository_mode"] == "public" and
            meta["visibility"] != "public"):
        reject("PUBLICATION_DENIED", "Private history cannot enter public Git repository")
    if operation not in writer.capability["operations"]:
        reject("PUBLICATION_DENIED", "Trusted record operation scope denied")


def _clean_old_parent(workspace, prior_path):
    """Remove now-empty directories; reindex retained old ancestors."""
    from service_v1 import _index_content
    parent = (workspace / prior_path).parent
    while parent != workspace / "openwiki":
        if not parent.exists():
            parent = parent.parent
            continue
        remaining = [p for p in parent.iterdir() if p.name != "index.md"]
        if remaining:
            # Recompute only this ancestor's exact direct children.
            entries = {p.name + "/" if p.is_dir() else p.name for p in remaining
                       if p.is_dir() or (p.is_file() and p.name.endswith(".md") and
                                          not p.name.endswith(".log.md") and
                                          p.name not in {"log.md", "index.md"})}
            (parent / "index.md").write_text(
                _index_content(parent.relative_to(workspace).as_posix(), entries),
                encoding="utf-8")
            return
        (parent / "index.md").unlink(missing_ok=True)
        parent.rmdir()
        parent = parent.parent


def _event(writer, normalized, meta, old_path, new_path, before, after,
           old_events, action, operation_id, timestamp, *, summary=None):
    request = dict(normalized)
    if summary is not None:
        request["summary"] = summary
    # Every event in one transaction carries the SAME request digest computed
    # from the exact original command; only its human summary differs.
    event = make_event(normalized, record_id=meta["id"],
                       event_id=str(uuid.uuid4()), operation_id=operation_id,
                       sequence=len(old_events) + 1, action=action,
                       path_before=old_path, path_after=new_path,
                       before=before, after=after,
                       previous_event_id=old_events[-1]["id"],
                       recorded_at=timestamp)
    if summary is not None:
        event["summary"] = summary
    return event


def _stage_validate_commit(writer, normalized, head, edits, old_path=None, new_path=None):
    """Commit one complete transaction through W-02's same checks and CAS."""
    from service_v1 import git
    with tempfile.TemporaryDirectory(prefix="knowledge-lifecycle-") as tmp:
        workspace = Path(tmp) / "checkout"
        git(writer.root, "worktree", "add", "--detach", str(workspace), head)
        try:
            # Only source and sibling log paths in the computed transaction
            # may change. All files are written in the isolated worktree.
            if old_path is not None and new_path is not None:
                for name in (old_path, old_path[:-3] + ".log.md"):
                    original = workspace / name
                    target = workspace / (new_path if name == old_path else
                                          new_path[:-3] + ".log.md")
                    if target.exists() or target.is_symlink():
                        reject("VALIDATION_ERROR", "Move destination already exists")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    original.rename(target)
            for path, (source, log) in edits.items():
                for portion in list(Path(path).parents)[:-1]:
                    component = workspace / portion
                    if component.is_symlink():
                        reject("VALIDATION_ERROR", "Symlink in transaction path")
                target = workspace / path
                if target.is_symlink():
                    reject("VALIDATION_ERROR", "Symlink in record destination")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, encoding="utf-8", newline="")
                (workspace / (path[:-3] + ".log.md")).write_text(
                    log, encoding="utf-8", newline="")
            if old_path is not None:
                _clean_old_parent(workspace, old_path)
            # Exact old and new ancestry; never generate a sibling log for index.
            for path in sorted(edits):
                writer._reindex_target(workspace, path)
            if old_path is not None:
                parent = (workspace / old_path).parent
                if parent.exists():
                    writer._reindex_target(workspace, str(
                        Path(old_path).parent / "placeholder.md"))
            git(workspace, "add", "-A", "--", "openwiki")
            writer._fault("staged")
            repository(workspace, base=head, strict_indexes=True)
            if writer.staged_checker is not None:
                if not callable(writer.staged_checker):
                    reject("WRITE_FAILED", "Invalid staged OKF checker")
                try:
                    writer.staged_checker(workspace)
                except Exception as exc:
                    raise WriterError(
                        "INTEGRITY_ERROR", "Staged OKF validation failed") from exc
            else:
                checker = workspace / ".githooks" / "pre-commit"
                if not checker.is_file():
                    reject("WRITE_FAILED", "Required staged OKF checker is missing")
                outcome = subprocess.run(
                    ["sh", str(checker)], cwd=workspace, capture_output=True)
                if outcome.returncode:
                    reject("INTEGRITY_ERROR", "Staged OKF validation failed")
            writer._fault("validated")
            git(workspace, "-c", "user.name=Knowledge Writer",
                "-c", "user.email=writer@localhost.invalid", "commit",
                "-m", "knowledge: " + normalized["summary"][:70])
            commit = git(workspace, "rev-parse", "HEAD")
            writer._fault("committed")
            if writer.remote:
                pushed = subprocess.run([
                    "git", "push", "--force-with-lease=refs/heads/" +
                    writer.branch + ":" + head, writer.remote,
                    commit + ":refs/heads/" + writer.branch
                ], cwd=workspace, capture_output=True)
                if pushed.returncode:
                    reject("CONFLICT", "Remote compare-and-swap rejected")
                writer._fault("remote_published")
            publish = subprocess.run([
                "git", "update-ref", "refs/heads/" + writer.branch, commit, head
            ], cwd=writer.root, capture_output=True)
            if publish.returncode:
                if writer.remote:
                    raise WriterError("WRITE_FAILED",
                                      "Remote may have committed; retry same key",
                                      retryable=True)
                reject("CONFLICT", "Local compare-and-swap rejected")
            writer._fault("published")
            receipt = receipt_from_logs(writer._logs(writer._head()), normalized)
            if receipt is None:
                raise WriterError("WRITE_FAILED", "Commit receipt uncertain; retry same key",
                                  retryable=True)
            return writer._response(receipt, commit, "committed")
        finally:
            git(writer.root, "worktree", "remove", "--force", str(workspace),
                check=False)


def execute(writer, normalized):
    """Execute W-03 mutation using the same writer lock, receipts and CAS."""
    from service_v1 import git
    command = normalized["command"]
    if command not in ("move", "archive", "reopen"):
        reject("VALIDATION_ERROR", "Unsupported lifecycle command")
    with writer._lock():
        head = writer._head()
        remote_head = writer._remote_tip() if writer.remote else None
        receipt_head = remote_head or head
        logs = writer._logs(receipt_head)
        receipt = receipt_from_logs(logs, normalized)
        if receipt:
            origin = writer._receipt_commit(receipt_head, receipt["id"])
            return writer._response(receipt, origin, "already_committed")
        if remote_head is not None and remote_head != head:
            reject("CONFLICT", "Local branch is stale relative to remote")
        if normalized["expected_head"] != head:
            reject("CONFLICT", "Expected repository head is stale")
        found = writer._find_record(head, normalized["record_id"])
        if not found:
            reject("NOT_FOUND", "Record not found")
        old_path, before, meta = found
        _write_permission(writer, meta, command)
        originals = parse_log(logs[old_path[:-3] + ".log.md"], old_path)
        if originals[-1]["id"] != normalized["expected_version"]:
            reject("CONFLICT", "Expected record version is stale")
        timestamp = writer.clock().astimezone(timezone.utc).replace(
            microsecond=0).isoformat().replace("+00:00", "Z")
        op_id = str(uuid.uuid4())
        edits = {}
        destination = None
        if command in ("archive", "reopen"):
            old_status = meta["status"]
            if command == "archive":
                if old_status == "deprecated":
                    reject("NO_CHANGE", "Record is already archived")
                target_status, action = "deprecated", "ARCHIVED"
            else:
                if old_status != "deprecated":
                    reject("VALIDATION_ERROR", "Only archived records can reopen")
                target_status, action = normalized["status"], "REOPENED"
            after = _status_source(before, target_status)
            if after == before:
                reject("NO_CHANGE", "Record content is unchanged")
            if timestamp < originals[-1]["recorded_at"]:
                reject("CLOCK_SKEW", "Writer clock precedes last record event")
            event = _event(writer, normalized, meta, old_path, old_path,
                           before, after, originals, action, op_id, timestamp)
            edits[old_path] = (after, append_log(logs[old_path[:-3] + ".log.md"].decode(),
                                                 event))
        else:
            destination = normalized["destination"]
            if destination == old_path:
                reject("NO_CHANGE", "Move destination equals current path")
            records, tracked = _current_records(writer, head)
            if any(p.casefold() == destination.casefold() for p in tracked):
                reject("VALIDATION_ERROR", "Move destination is occupied")
            existing = {p: source for p, (_, source) in records.items()}
            post = dict(existing)
            post[destination] = post.pop(old_path)
            paths = {old_path: destination}
            for source_path, (record_meta, old_source) in records.items():
                after_path = paths.get(source_path, source_path)
                try:
                    updated, _ = repair_relative_links(
                        old_source, before_path=source_path, after_path=after_path,
                        moved_paths=paths, current_sources=post)
                except IntegrityError as exc:
                    reject("INTEGRITY_ERROR", str(exc))
                if updated == old_source and source_path != old_path:
                    continue
                _write_permission(writer, record_meta, command)
                history = parse_log(logs[source_path[:-3] + ".log.md"],
                                    source_path)
                if timestamp < history[-1]["recorded_at"]:
                    reject("CLOCK_SKEW", "Writer clock precedes affected record")
                action = "MOVED" if source_path == old_path else "UPDATED"
                summary = None if action == "MOVED" else (
                    "Update links after moving " + meta["title"])[:240]
                event = _event(writer, normalized, record_meta,
                               source_path, after_path, old_source, updated,
                               history, action, op_id, timestamp, summary=summary)
                edits[after_path] = (
                    updated, append_log(logs[source_path[:-3] + ".log.md"].decode(),
                                        event))
            if destination not in edits:
                reject("INTEGRITY_ERROR", "Move plan has no primary event")
        return _stage_validate_commit(
            writer, normalized, head, edits,
            old_path=old_path if destination is not None else None,
            new_path=destination)
