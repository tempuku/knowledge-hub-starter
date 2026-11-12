"""Transactional Git-backed Knowledge Hub writer (W-01/W-02, issue #28).

No public network endpoint. Capability is injected by trusted local launch code.
The Git ref is the commit point; no writes are made to the caller's worktree.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from validate_v1 import IntegrityError, parse_log, parse_record, repository
from writer_v1 import (WriterError, append_log, create_source, make_event,
                       normalized_request, receipt_from_logs, require_capability,
                       reject)


def git(root, *args, check=True):
    result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if check and result.returncode:
        raise WriterError("WRITE_FAILED", "Git operation failed", retryable=False)
    return result.stdout.decode("utf-8").rstrip("\n") if result.returncode == 0 else None


def _index_content(directory, entries, previous=None):
    # Indexes are structural, not v1 records, and never generate history events.
    # Keep the root declaration and a stable heading, regenerate exact links.
    if directory == "openwiki":
        prefix = '---\nokf_version: "0.2"\n---\n\n# Knowledge Hub\n\n'
    else:
        prefix = "# " + directory.rsplit("/", 1)[-1].replace("-", " ").title() + "\n\n"
    return prefix + "".join(
        "* [" + name.rstrip("/").replace("-", " ").title() + "](" + name + ")\n"
        for name in sorted(entries)
    )


def _rebuild_indexes(root):
    wiki = root / "openwiki"
    if not wiki.exists():
        wiki.mkdir()
    directories = {"openwiki": set()}
    for source in wiki.rglob("*.md"):
        rel = source.relative_to(root).as_posix()
        if source.name.endswith(".log.md") or source.name in ("index.md", "log.md"):
            continue
        parent = source.parent.relative_to(root).as_posix()
        directories.setdefault(parent, set()).add(source.name)
        while parent != "openwiki":
            ancestor, child = parent.rsplit("/", 1)
            directories.setdefault(ancestor, set()).add(child + "/")
            parent = ancestor
    for folder, children in directories.items():
        index = root / folder / "index.md"
        index.parent.mkdir(parents=True, exist_ok=True)
        # Preserve legacy indexes until the separate migration; target writer
        # can only safely regenerate indexes in a fully migrated repository.
        if index.exists() and "journal/" in index.read_text(encoding="utf-8"):
            reject("INTEGRITY_ERROR", "Legacy indexes require reviewed migration")
        index.write_text(_index_content(folder, children), encoding="utf-8")
    return directories


class GitRecordWriter:
    def __init__(self, root, capability, *, branch="main", remote=None,
                 staged_checker=None, clock=None, fault=None):
        self.root = Path(root).resolve()
        self.capability = capability
        self.branch = branch
        self.remote = remote
        self.staged_checker = staged_checker
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.fault = fault

    def _fault(self, point):
        if self.fault:
            self.fault(point)

    @contextlib.contextmanager
    def _lock(self):
        # Stable lock is outside the worktree and never enters the commit.
        lock_path = Path(git(self.root, "rev-parse", "--git-path", "knowledge-writer.lock"))
        if not lock_path.is_absolute():
            lock_path = self.root / lock_path
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _head(self):
        return git(self.root, "rev-parse", "--verify", "refs/heads/" + self.branch)

    def _logs(self, commit):
        paths = git(self.root, "ls-tree", "-r", "--name-only", commit, "--", "openwiki").splitlines()
        return {
            p: subprocess.check_output(["git", "show", commit + ":" + p], cwd=self.root)
            for p in paths if p.endswith(".log.md") and
            subprocess.check_output(["git", "show", commit + ":" + p], cwd=self.root).startswith(
                b"# Record history\n\n")
        }

    def _find_record(self, commit, record_id):
        paths = git(self.root, "ls-tree", "-r", "--name-only", commit, "--", "openwiki").splitlines()
        found = []
        for path in paths:
            if not path.endswith(".md") or path.endswith(".log.md") or path.endswith("/index.md"):
                continue
            raw = subprocess.check_output(["git", "show", commit + ":" + path], cwd=self.root)
            if not raw.startswith(b"---\n") or b"\nschema_version:" not in raw[:4096]:
                continue
            meta, source = parse_record(raw, path)
            if meta["id"] == record_id:
                found.append((path, source, meta))
        if len(found) > 1:
            reject("INTEGRITY_ERROR", "Duplicate record ID")
        return found[0] if found else None

    def read(self, record_id):
        try:
            uuid.UUID(record_id)
        except (ValueError, TypeError):
            reject("VALIDATION_ERROR", "Invalid record ID")
        with self._lock():
            head = self._head()
            found = self._find_record(head, record_id)
            if not found:
                reject("NOT_FOUND", "Record not found")
            path, source, meta = found
            if self.capability.get("repository_mode") == "public" and meta["visibility"] != "public":
                reject("NOT_FOUND", "Record not found")
            log = self._logs(head).get(path[:-3] + ".log.md")
            if not log:
                reject("INTEGRITY_ERROR", "Missing canonical record history")
            events = parse_log(log, path)
            if events[-1]["after"] != source:
                reject("INTEGRITY_ERROR", "Record and history disagree")
            return {"record_id": record_id, "path": path, "content": source,
                    "version": events[-1]["id"], "head": head}

    def write(self, request):
        normalized = normalized_request(request)
        # Authorization before revealing any committed receipt.
        require_capability(normalized, self.capability)
        with self._lock():
            head = self._head()
            logs = self._logs(head)
            receipt = receipt_from_logs(logs, normalized)
            if receipt:
                # Find the original commit, not current head after later changes.
                origin = self._receipt_commit(head, receipt["id"])
                return self._response(receipt, origin, "already_committed")
            if normalized["expected_head"] != head:
                reject("CONFLICT", "Expected repository head is stale")
            command = normalized["command"]
            if command == "create":
                path = normalized["path"]
                if git(self.root, "cat-file", "-e", head + ":" + path, check=False) is not None:
                    reject("VALIDATION_ERROR", "Record path already exists")
                existing_paths = git(self.root, "ls-tree", "-r", "--name-only",
                                     head, "--", "openwiki").splitlines()
                if any(p.casefold() == path.casefold() for p in existing_paths):
                    reject("VALIDATION_ERROR", "Case-insensitive record path collision")
                record_id = str(uuid.uuid4())
                before = None
                after = create_source(normalized["content"], record_id)
                previous = None
                sequence = 1
            else:
                record_id = normalized["record_id"]
                found = self._find_record(head, record_id)
                if not found:
                    reject("NOT_FOUND", "Record not found")
                path, before, meta = found
                if self.capability["repository_mode"] == "public" and meta["visibility"] != "public":
                    reject("NOT_FOUND", "Record not found")
                events = parse_log(logs[path[:-3] + ".log.md"], path)
                previous = events[-1]
                if normalized["expected_version"] != previous["id"]:
                    reject("CONFLICT", "Expected record version is stale")
                after = normalized["content"]
                new_meta, _ = parse_record(after.encode("utf-8"), path)
                if new_meta["id"] != record_id:
                    reject("VALIDATION_ERROR", "Record identity cannot change")
                if meta["status"] == "deprecated" or new_meta["status"] == "deprecated":
                    reject("VALIDATION_ERROR", "Use archive/reopen lifecycle commands")
                if before == after:
                    reject("NO_CHANGE", "Record content is unchanged")
                if self.capability["repository_mode"] == "public" and new_meta["visibility"] != "public":
                    reject("PUBLICATION_DENIED", "Private snapshot in public repository")
                sequence = len(events) + 1
            timestamp = self.clock().astimezone(timezone.utc).replace(
                microsecond=0).isoformat().replace("+00:00", "Z")
            if previous and timestamp < previous["recorded_at"]:
                reject("CLOCK_SKEW", "Writer clock precedes last event")
            event = make_event(normalized, record_id=record_id,
                               event_id=str(uuid.uuid4()), operation_id=str(uuid.uuid4()),
                               sequence=sequence, action="CREATED" if command == "create" else "UPDATED",
                               path_before=None if command == "create" else path,
                               path_after=path, before=before, after=after,
                               previous_event_id=previous["id"] if previous else None,
                               recorded_at=timestamp)
            with tempfile.TemporaryDirectory(prefix="knowledge-writer-") as tmp:
                workspace = Path(tmp) / "checkout"
                git(self.root, "worktree", "add", "--detach", str(workspace), head)
                try:
                    destination = workspace / path
                    for component in (workspace / Path(*Path(path).parts[:i])
                                      for i in range(1, len(Path(path).parts) + 1)):
                        if component.is_symlink():
                            reject("VALIDATION_ERROR", "Symlink at record path component")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(after, encoding="utf-8", newline="")
                    log_path = path[:-3] + ".log.md"
                    existing = logs.get(log_path)
                    (workspace / log_path).write_text(
                        append_log(existing.decode("utf-8") if existing else None, event),
                        encoding="utf-8", newline="")
                    # Rebuild target indexes only; legacy tree indexes are not
                    # safe to rewrite before migration. Detect and reject.
                    self._reindex_target(workspace, path)
                    git(workspace, "add", "--", path, log_path, *self._changed_indexes(workspace))
                    self._fault("staged")
                    repository(workspace, base=head, strict_indexes=True)
                    if self.staged_checker:
                        self.staged_checker(workspace)
                    self._fault("validated")
                    git(workspace, "-c", "user.name=Knowledge Writer",
                        "-c", "user.email=writer@localhost.invalid",
                        "commit", "-m", "knowledge: " + normalized["summary"][:70])
                    commit = git(workspace, "rev-parse", "HEAD")
                    self._fault("committed")
                    if self.remote:
                        # GitHub server must accept the expected ref as lease.
                        result = subprocess.run([
                            "git", "push", "--force-with-lease=refs/heads/" +
                            self.branch + ":" + head, self.remote,
                            commit + ":refs/heads/" + self.branch,
                        ], cwd=workspace, capture_output=True)
                        if result.returncode:
                            reject("CONFLICT", "Remote compare-and-swap rejected")
                        # Remote is the commit point. A failed local ref update
                        # after this point is an uncertain receipt, not rollback.
                    result = subprocess.run([
                        "git", "update-ref", "refs/heads/" + self.branch, commit, head
                    ], cwd=self.root, capture_output=True)
                    if result.returncode:
                        if self.remote:
                            raise WriterError("WRITE_FAILED",
                                              "Remote may have committed; retry same key",
                                              retryable=True)
                        reject("CONFLICT", "Local compare-and-swap rejected")
                    self._fault("published")
                    return self._response(event, commit, "committed")
                finally:
                    git(self.root, "worktree", "remove", "--force", str(workspace),
                        check=False)

    def _reindex_target(self, workspace, record_path):
        # Rebuild exact sorted direct-child links only along the affected
        # ancestry. Never overwrite a legacy index that still carries content
        # requiring the separate migration.
        parent = Path(record_path).parent
        while True:
            folder = workspace / parent
            folder.mkdir(parents=True, exist_ok=True)
            index = folder / "index.md"
            entries = set()
            for child in folder.iterdir():
                if child.is_symlink():
                    reject("INTEGRITY_ERROR", "Symlink in structural index directory")
                if child.is_dir():
                    entries.add(child.name + "/")
                elif child.is_file() and child.name.endswith(".md") and (
                        child.name not in ("index.md", "log.md") and
                        not child.name.endswith(".log.md")):
                    entries.add(child.name)
            if index.exists():
                old = index.read_text(encoding="utf-8")
                if "journal/" in old:
                    reject("INTEGRITY_ERROR", "Legacy indexes require reviewed migration")
                # Preserve historical indexes with unrelated prose; those are
                # migration input and must not be silently rewritten.
                if index.as_posix().endswith("/openwiki/index.md"):
                    if not old.startswith('---\nokf_version: "0.2"\n---\n'):
                        reject("INTEGRITY_ERROR", "Unexpected root index format")
            index.write_text(_index_content(parent.as_posix(), entries),
                             encoding="utf-8")
            if str(parent) == "openwiki":
                break
            parent = parent.parent

    def _changed_indexes(self, workspace):
        return [p for p in git(workspace, "status", "--porcelain", "--untracked-files=all").splitlines()
                if p[3:].endswith("/index.md")]

    def _receipt_commit(self, head, event_id):
        # Search from oldest to newest for the commit introducing the event.
        for commit in reversed(git(self.root, "rev-list", head).splitlines()):
            for log in self._logs(commit).values():
                if event_id in log.decode("utf-8"):
                    return commit
        reject("INTEGRITY_ERROR", "Receipt event has no introducing commit")

    def _response(self, event, head, status):
        path = event["path_after"]
         # URLs are relative and transport-neutral; the adapter may resolve them
        # against its configured repository URL.
        return {"status": status, "record_id": event["record_id"],
                "event_id": event["id"], "operation_id": event["operation_id"],
                "version": event["id"], "head": head,
                "record_url": path, "event_url": path[:-3] + ".log.md#" + event["id"],
                "diff_url": head, "publication": "pending"}
