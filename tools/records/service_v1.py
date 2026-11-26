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
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECTION = Path(__file__).resolve().parents[1] / "projection"
if str(PROJECTION) not in sys.path:
    sys.path.insert(0, str(PROJECTION))

from validate_v1 import (IntegrityError, frontmatter, parse_log, parse_record,
                         repository)
from maintenance_v1 import writes_paused
from writer_v1 import (WriterError, append_log, create_source, make_event,
                       normalized_request, receipt_from_logs, require_capability,
                       reject)
from deterministic import ProjectionError, query_search, search_shards, tokenize


def git(root, *args, check=True):
    result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if check and result.returncode:
        raise WriterError("WRITE_FAILED", "Git operation failed", retryable=False)
    return result.stdout.decode("utf-8").rstrip("\n") if result.returncode == 0 else None


def _area(path):
    """Containment area used by search filters; root-level records are 'root'."""
    relative = path
    for root in ("records", "openwiki"):
        prefix = root + "/"
        if path.startswith(prefix):
            relative = path[len(prefix):]
            break
    return relative.rsplit("/", 1)[0] if "/" in relative else "root"


INDEX_ENTRY = re.compile(r"^[*-] \[([^\]]+)\]\(([^)]+)\)\s*$")


def _entry_line(name, label=None):
    if label is None:
        label = name.rstrip("/").replace("-", " ").title()
    return "* [" + label + "](" + name + ")\n"


def _index_entry_targets(text):
    return [match.group(2) for match in
            (INDEX_ENTRY.match(line) for line in text.splitlines()) if match]


def _previous_index(index):
    """Read an existing index, failing closed for symlinks and duplicates."""
    if not index.exists():
        return None
    if index.is_symlink():
        reject("INTEGRITY_ERROR", "Symlink structural index")
    previous = index.read_text(encoding="utf-8")
    targets = _index_entry_targets(previous)
    if len(targets) != len(set(targets)):
        reject("INTEGRITY_ERROR", "Duplicate structural index entries")
    return previous


def _is_journal_index(directory):
    return "journal" in Path(directory).parts


def _index_content(directory, entries, previous=None):
    # Indexes are structural, not v1 records, and never generate history events.
    # With previous text, preserve every non-entry line (frontmatter, heading,
    # prose, blank-line structure) and regenerate only the sorted entry block.
    if previous is not None:
        labels, kept, block_at = {}, [], None
        for line in previous.splitlines(keepends=True):
            match = INDEX_ENTRY.match(line.rstrip("\n"))
            if match:
                labels.setdefault(match.group(2), match.group(1))
                if block_at is None:
                    block_at = len(kept)
                continue
            kept.append(line)
        block = "".join(_entry_line(name, labels.get(name))
                        for name in sorted(entries))
        if block_at is None:
            head = "".join(kept)
            if head and not head.endswith("\n"):
                head += "\n"
            if head and not head.endswith("\n\n"):
                head += "\n"
            return head + block
        result = "".join(kept[:block_at]) + block + "".join(kept[block_at:])
        return result if result.endswith("\n") else result + "\n"
    # No previous index: keep the exact generated output for new directories.
    if directory in ("openwiki", "records"):
        prefix = '---\nokf_version: "0.2"\n---\n\n# Knowledge Hub\n\n'
    else:
        prefix = "# " + directory.rsplit("/", 1)[-1].replace("-", " ").title() + "\n\n"
    return prefix + "".join(_entry_line(name) for name in sorted(entries))


def _rebuild_indexes(root, skip_journal=False):
    directories = {}
    for root_name in ("records", "openwiki"):
        base = root / root_name
        if not base.exists():
            continue
        directories.setdefault(root_name, set())
        for source in base.rglob("*.md"):
            if source.is_symlink():
                reject("INTEGRITY_ERROR", "Symlink in structural index directory")
            rel = source.relative_to(root).as_posix()
            if source.name.endswith(".log.md") or source.name in ("index.md", "log.md"):
                continue
            parent = source.parent.relative_to(root).as_posix()
            directories.setdefault(parent, set()).add(source.name)
            while parent != root_name:
                ancestor, child = parent.rsplit("/", 1)
                directories.setdefault(ancestor, set()).add(child + "/")
                parent = ancestor
    for folder, children in directories.items():
        # Legacy journal trees stay migration input. Ordinary writes leave them
        # byte-identical; migration tooling rejects them instead of guessing.
        if _is_journal_index(folder):
            if skip_journal:
                continue
            reject("INTEGRITY_ERROR", "Legacy journal indexes require reviewed migration")
        index = root / folder / "index.md"
        index.parent.mkdir(parents=True, exist_ok=True)
        previous = _previous_index(index)
        index.write_text(_index_content(folder, children, previous), encoding="utf-8")
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

    def _remote_tip(self):
        """Read a trusted remote tip and fetch its object without moving local refs.

        This permits durable receipt replay when a prior remote CAS succeeded
        but the local ref update or the response was lost.
        """
        ref = "refs/heads/" + self.branch
        result = subprocess.run(["git", "ls-remote", "--heads", self.remote, ref],
                                cwd=self.root, capture_output=True, text=True)
        if result.returncode:
            raise WriterError("WRITE_FAILED", "Trusted remote is unavailable",
                              retryable=True)
        entries = result.stdout.strip().splitlines()
        if len(entries) != 1:
            raise WriterError("WRITE_FAILED", "Trusted remote ref is missing",
                              retryable=True)
        parts = entries[0].split("\t")
        if len(parts) != 2 or parts[1] != ref or not re.fullmatch(
                r"[0-9a-f]{40}|[0-9a-f]{64}", parts[0]):
            raise WriterError("WRITE_FAILED", "Invalid trusted remote ref",
                              retryable=True)
        remote_sha = parts[0]
        if git(self.root, "cat-file", "-e", remote_sha + "^{commit}",
               check=False) is None:
            fetch = subprocess.run(["git", "fetch", "--no-tags", self.remote,
                                    remote_sha], cwd=self.root, capture_output=True)
            if fetch.returncode:
                raise WriterError("WRITE_FAILED", "Cannot fetch remote receipt",
                                  retryable=True)
        return remote_sha

    def _logs(self, commit):
        paths = []
        for root_name in ("records", "openwiki"):
            paths.extend(git(self.root, "ls-tree", "-r", "--name-only", commit,
                             "--", root_name).splitlines())
        return {
            p: subprocess.check_output(["git", "show", commit + ":" + p], cwd=self.root)
            for p in paths if p.endswith(".log.md") and
            subprocess.check_output(["git", "show", commit + ":" + p], cwd=self.root).startswith(
                b"# Record history\n\n")
        }

    def _find_record(self, commit, record_id):
        paths = []
        for root_name in ("records", "openwiki"):
            paths.extend(git(self.root, "ls-tree", "-r", "--name-only", commit,
                             "--", root_name).splitlines())
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

    def list_records(self, include_archived=False):
        """Browse current records without exposing deprecated items by default."""
        if (type(include_archived) is not bool or
                type(self.capability) is not dict or
                self.capability.get("repository_mode") not in ("private", "public") or
                "read" not in self.capability.get("operations", [])):
            reject("NOT_FOUND", "Record collection not available")
        from extended_v1 import _current_records
        with self._lock():
            records, _ = _current_records(self, self._head())
            visible = []
            for path, (meta, _) in sorted(records.items()):
                if meta["status"] == "deprecated" and not include_archived:
                    continue
                if (self.capability["repository_mode"] == "public" and
                        meta["visibility"] != "public"):
                    continue
                visible.append({"record_id": meta["id"], "path": path,
                                "title": meta["title"], "status": meta["status"]})
            return visible

    def _require_read(self, message):
        # Authorization is a trusted launch capability, never caller-supplied.
        # A missing/unknown capability must not permit reading private records.
        if (type(self.capability) is not dict or
                self.capability.get("repository_mode") not in ("public", "private") or
                type(self.capability.get("operations")) not in (list, tuple, set) or
                "read" not in self.capability["operations"]):
            reject("NOT_FOUND", message)

    def search(self, query, *, limit=8, include_archived=False):
        """Rank current records by tokens; never return bodies or private paths."""
        self._require_read("Record collection not available")
        if type(query) is not str or not 1 <= len(query) <= 256:
            reject("VALIDATION_ERROR", "Invalid search query")
        tokens = list(dict.fromkeys(tokenize(query)))
        if not tokens or len(tokens) > 8:
            reject("VALIDATION_ERROR", "Invalid search query tokens")
        if type(limit) is not int or not 1 <= limit <= 25:
            reject("VALIDATION_ERROR", "Invalid search result limit")
        if type(include_archived) is not bool:
            reject("VALIDATION_ERROR", "Invalid include_archived flag")
        from extended_v1 import _current_records
        with self._lock():
            head = self._head()
            records, _ = _current_records(self, head)
            candidates, paths = [], {}
            for path, (meta, source) in sorted(records.items()):
                # Filter before indexing: public ranking and totals must never
                # count snapshots that view is not allowed to reveal.
                if (self.capability["repository_mode"] == "public" and
                        meta["visibility"] != "public"):
                    continue
                candidates.append({
                    "id": meta["id"], "title": meta["title"],
                    "description": meta.get("description", ""),
                    "tags": meta.get("tags", []),
                    "body": frontmatter(source)[1],
                    "status": meta["status"], "type": meta["type"],
                    "area": _area(path),
                    "project_id": meta.get("project_id"),
                    "updated_at": "",
                })
                paths[meta["id"]] = path
            try:
                shards = search_shards(candidates)
                matches = query_search(query, candidates, shards,
                                       include_archived=include_archived)
            except ProjectionError as exc:
                reject("VALIDATION_ERROR", str(exc))
            page = matches[:limit]
            by_id = {record["id"]: record for record in candidates}
            results = [{"record_id": record_id, "path": paths[record_id],
                        "title": by_id[record_id]["title"],
                        "status": by_id[record_id]["status"]}
                       for record_id in page]
            return {"query": query, "head": head, "total": len(matches),
                    "count": len(results), "results": results}

    def history(self, record_id, *, limit=20, before_sequence=None):
        """Return event metadata newest first; snapshots and hashes stay hidden."""
        self._require_read("Record not found")
        try:
            uuid.UUID(record_id)
        except (AttributeError, TypeError, ValueError):
            reject("VALIDATION_ERROR", "Invalid record ID")
        if type(limit) is not int or not 1 <= limit <= 50:
            reject("VALIDATION_ERROR", "Invalid history limit")
        if before_sequence is not None and (
                type(before_sequence) is not int or before_sequence < 1):
            reject("VALIDATION_ERROR", "Invalid history cursor")
        with self._lock():
            head = self._head()
            found = self._find_record(head, record_id)
            if not found:
                reject("NOT_FOUND", "Record not found")
            path, source, meta = found
            if (self.capability["repository_mode"] == "public" and
                    meta["visibility"] != "public"):
                reject("NOT_FOUND", "Record not found")
            log_path = path[:-3] + ".log.md"
            # Read only this record's log from the trusted commit; never scan.
            raw = git(self.root, "show", head + ":" + log_path, check=False)
            if raw is None:
                reject("INTEGRITY_ERROR", "Missing canonical record history")
            try:
                events = parse_log((raw + "\n").encode("utf-8"), log_path)
            except (IntegrityError, UnicodeError) as exc:
                reject("INTEGRITY_ERROR", "Canonical record history is unreadable")
            if events[-1]["after"] != source:
                reject("INTEGRITY_ERROR", "Record and history disagree")
            eligible = [event for event in events
                        if self._visible_snapshot(event)]
            eligible.sort(key=lambda event: event["sequence"], reverse=True)
            total = len(eligible)
            if before_sequence is not None:
                eligible = [event for event in eligible
                            if event["sequence"] < before_sequence]
            page = eligible[:limit]
            return {"record_id": record_id, "path": path,
                    "title": meta["title"], "status": meta["status"],
                    "head": head, "total": total,
                    "next": page[-1]["sequence"] if len(eligible) > limit else None,
                    "events": [self._event_metadata(event, path)
                               for event in page]}

    def _visible_snapshot(self, event):
        # History is filtered by the snapshot each event produced, so a public
        # view cannot even infer the existence of private revisions. A snapshot
        # that cannot be parsed is excluded rather than revealed.
        if self.capability["repository_mode"] != "public":
            return True
        try:
            meta, _ = frontmatter(event["after"])
        except (IntegrityError, UnicodeError):
            return False
        return meta.get("visibility") == "public"

    @staticmethod
    def _event_metadata(event, path):
        # Explicit allowlist: before/after snapshots and digests never leave.
        return {"event_id": event["id"], "sequence": event["sequence"],
                "action": event["action"], "recorded_at": event["recorded_at"],
                "summary": event["summary"],
                "occurred_on": event["occurred_on"],
                "occurred_at": event["occurred_at"],
                "actor_label": event["actor"]["label"],
                "path_before": event["path_before"],
                "path_after": event["path_after"],
                "record_url": path,
                "event_url": path[:-3] + ".log.md#" + event["id"]}

    def read(self, record_id):
        self._require_read("Record not found")
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
        # M-04: reject every domain mutation before validating or executing it.
        # This includes durable idempotent retries and extended move commands.
        if writes_paused():
            raise WriterError("MAINTENANCE", "Knowledge Hub writes are paused for cutover",
                              retryable=True)
        normalized = normalized_request(request)
        # Authorization before revealing any committed receipt.
        require_capability(normalized, self.capability)
        if normalized["command"] in ("move", "archive", "reopen"):
            from extended_v1 import execute
            return execute(self, normalized)
        with self._lock():
            head = self._head()
            # A remote CAS may have succeeded while the local ref update failed.
            # Consult the trusted remote's committed log FIRST so a retry
            # returns its original receipt without making a second commit.
            remote_head = self._remote_tip() if self.remote else None
            receipt_head = remote_head or head
            logs = self._logs(receipt_head)
            receipt = receipt_from_logs(logs, normalized)
            if receipt:
                origin = self._receipt_commit(receipt_head, receipt["id"])
                return self._response(receipt, origin, "already_committed")
            if remote_head is not None and remote_head != head:
                reject("CONFLICT", "Local branch is stale relative to remote")
            if normalized["expected_head"] != head:
                reject("CONFLICT", "Expected repository head is stale")
            command = normalized["command"]
            if command == "create":
                path = normalized["path"]
                if git(self.root, "cat-file", "-e", head + ":" + path, check=False) is not None:
                    reject("VALIDATION_ERROR", "Record path already exists")
                existing_paths = []
                for root_name in ("records", "openwiki"):
                    existing_paths.extend(git(self.root, "ls-tree", "-r",
                                              "--name-only", head, "--",
                                              root_name).splitlines())
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
                    # Rebuild only the affected ancestry: the record's own
                    # directory up to the root. Unrelated indexes must not be
                    # touched, so concurrent writers do not conflict.
                    self._reindex_target(workspace, path)
                    git(workspace, "add", "--", path, log_path, *self._changed_indexes(workspace))
                    self._fault("staged")
                    repository(workspace, base=head, strict_indexes=True)
                    # The existing staged OKF checker is a second mandatory
                    # validator, not a best-effort optional hook.
                    if self.staged_checker is not None:
                        if not callable(self.staged_checker):
                            reject("WRITE_FAILED", "Invalid staged OKF checker")
                        try:
                            self.staged_checker(workspace)
                        except Exception as exc:
                            raise WriterError(
                                "INTEGRITY_ERROR", "Staged OKF validation failed"
                            ) from exc
                    else:
                        checker = workspace / ".githooks" / "pre-commit"
                        if not checker.is_file():
                            reject("WRITE_FAILED", "Required staged OKF checker is missing")
                        checked = subprocess.run(["sh", str(checker)], cwd=workspace,
                                                 capture_output=True)
                        if checked.returncode:
                            reject("INTEGRITY_ERROR", "Staged OKF validation failed")
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
                        self._fault("remote_published")
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
                    # Treat a successful ref change as a commit point only
                    # after verifying that the durable log still contains
                    # precisely this operation. Never return an unverified
                    # success receipt.
                    verified = receipt_from_logs(self._logs(self._head()), normalized)
                    if verified is None or verified["id"] != event["id"]:
                        raise WriterError("WRITE_FAILED",
                                          "Committed receipt is uncertain; retry same key",
                                          retryable=True)
                    return self._response(event, commit, "committed")
                finally:
                    git(self.root, "worktree", "remove", "--force", str(workspace),
                        check=False)

    def _reindex_target(self, workspace, record_path):
        # Rebuild exact sorted direct-child links only along the affected
        # ancestry, preserving unrelated prose already present in each index.
        parent = Path(record_path).parent
        while True:
            if _is_journal_index(parent.as_posix()):
                reject("INTEGRITY_ERROR", "Legacy journal indexes require reviewed migration")
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
            previous = _previous_index(index)
            if previous is not None and (index.as_posix().endswith("/openwiki/index.md") or
                                          index.as_posix().endswith("/records/index.md")):
                if not previous.startswith('---\nokf_version: "0.2"\n---\n'):
                    reject("INTEGRITY_ERROR", "Unexpected root index format")
            index.write_text(_index_content(parent.as_posix(), entries, previous),
                             encoding="utf-8")
            if parent.as_posix() in ("openwiki", "records"):
                break
            parent = parent.parent

    def _changed_indexes(self, workspace):
        return [p[3:] for p in git(workspace, "status", "--porcelain", "--untracked-files=all").splitlines()
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
