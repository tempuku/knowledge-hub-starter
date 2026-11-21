#!/usr/bin/env python3
"""Pull-request publication mode for the trusted local MCP adapter (issue #114).

The Git writer commits to a branch; this module turns that branch into a pull
request so a protected base branch can run required checks before merge. It
never merges directly, never bypasses required checks and never rewrites the
record/log writer contracts.

Every shell command receives an argument list (never ``shell=True``), an
explicit working directory, captured text output and a timeout. Tests inject a
fake ``runner`` with the same call shape.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess

BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
GH_TIMEOUT = 120
RUN_TIMEOUT = 60
WRITER_VALIDATORS = (
    "staged OKF checker (`tools/okf/verify.mjs`)",
    "v1 chain/schema/baseline-prefix validation "
    "(`tools/records/validate_v1.py`, `repository(..., strict_indexes=True)`)",
)
PRIVACY_NOTE = (
    "`visibility` is record metadata, not an access control. It does not "
    "protect files in a public Git repository; review this pull request "
    "before it is merged or published."
)


class PublicationError(Exception):
    """A transport-safe publication failure, returned before any commit."""

    def __init__(self, code, message, *, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable

    def response(self):
        return {"code": self.code, "message": str(self),
                "field_errors": [], "retryable": self.retryable}


def run(argv, *, cwd, timeout=RUN_TIMEOUT):
    """Default command runner; injected fakes must accept the same shape."""
    return subprocess.run(list(argv), cwd=str(cwd), capture_output=True,
                          text=True, timeout=timeout, check=False)


def _detail(result):
    text = (result.stderr or result.stdout or "").strip()
    return text[:400] if text else "command failed"


def _slug(path):
    name = (path or "").rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return slug[:40].strip("-") or "record"


def publication_branch(idempotency_key, path=None):
    """Stable branch per idempotency key, e.g. agent/knowledge/note-1a2b3c4d.

    Retrying the same request therefore targets the same branch and can replay
    the writer's durable receipt instead of creating a second commit.
    """
    if type(idempotency_key) is not str or not idempotency_key.strip():
        raise PublicationError("VALIDATION_ERROR",
                               "Invalid idempotency key for publication branch")
    digest = re.sub(r"[^0-9a-fA-F]", "", idempotency_key)
    suffix = (digest[:8].lower() if len(digest) >= 8 else
              hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:8])
    name = "agent/knowledge/" + _slug(path) + "-" + suffix
    if not BRANCH.fullmatch(name) or ".." in name or len(name) > 120:
        raise PublicationError("VALIDATION_ERROR",
                               "Invalid publication branch name")
    return name


def _git(root, runner, *args, timeout=RUN_TIMEOUT):
    return runner(["git", *args], cwd=root, timeout=timeout)


def _local_tip(root, head, runner):
    result = _git(root, runner, "rev-parse", "--verify", "--quiet",
                  "refs/heads/" + head)
    return result.stdout.strip() if result.returncode == 0 else None


def _remote_tip(root, remote, head, runner):
    result = _git(root, runner, "ls-remote", "--heads", remote,
                  "refs/heads/" + head)
    if result.returncode:
        raise PublicationError("WRITE_FAILED", "Trusted remote is unavailable",
                               retryable=True)
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    parts = lines[0].split("\t")
    if (len(lines) != 1 or len(parts) != 2 or
            parts[1] != "refs/heads/" + head or
            not COMMIT.fullmatch(parts[0])):
        raise PublicationError("WRITE_FAILED", "Invalid trusted remote ref",
                               retryable=True)
    return parts[0]


def _push(root, remote, head, expected_head, runner):
    result = _git(root, runner, "push", remote,
                  expected_head + ":refs/heads/" + head, timeout=GH_TIMEOUT)
    if result.returncode:
        raise PublicationError("WRITE_FAILED",
                               "Could not push publication branch: " +
                               _detail(result), retryable=True)


def _fetch(root, remote, head, runner):
    result = _git(root, runner, "fetch", "--no-tags", remote,
                  "refs/heads/" + head + ":refs/heads/" + head,
                  timeout=GH_TIMEOUT)
    if result.returncode:
        raise PublicationError("CONFLICT",
                               "Publication branch cannot be reconciled with "
                               "the trusted remote")


def merged_publication(root, head, runner=run):
    """Return the merged PR number for this head branch, if one exists.

    Used only before creating a completely fresh branch so a merged-and-
    deleted publication cannot become a silent second commit. A failed or
    unavailable `gh` query returns None rather than blocking the write.
    """
    argv = ["gh", "pr", "list", "--head", head, "--state", "all",
            "--json", "number,state"]
    try:
        result = runner(argv, cwd=root, timeout=GH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    try:
        entries = json.loads(result.stdout or "[]")
    except ValueError:
        return None
    if type(entries) is list:
        for entry in entries:
            if (type(entry) is dict and
                    str(entry.get("state", "")).casefold() == "merged"):
                return entry.get("number")
    return None


def prepare_publication_branch(root, remote, head, expected_head,
                               runner=run, merged_check=None):
    """Create/push the deterministic head branch before the writer commits.

    No writer is called by this function. A branch left behind after a merge
    is reused so the writer can replay its receipt; a branch that was deleted
    after merge raises CONFLICT instead of silently creating a second commit.
    """
    if type(head) is not str or not BRANCH.fullmatch(head) or ".." in head:
        raise PublicationError("VALIDATION_ERROR",
                               "Invalid publication branch")
    if type(remote) is not str or not remote.strip() or any(
            c.isspace() or ord(c) < 32 for c in remote):
        raise PublicationError("VALIDATION_ERROR", "Invalid trusted remote")
    if type(expected_head) is not str or not COMMIT.fullmatch(expected_head):
        raise PublicationError("VALIDATION_ERROR",
                               "Invalid expected head for publication")

    local = _local_tip(root, head, runner)
    remote_tip = _remote_tip(root, remote, head, runner)
    if local is None:
        if remote_tip is None:
            if merged_check is not None:
                merged = merged_check()
                if merged is not None:
                    raise PublicationError(
                        "CONFLICT",
                        "Publication branch was merged and deleted; retrying "
                        "this idempotency key is not recoverable")
            result = _git(root, runner, "branch", head, expected_head)
            if result.returncode:
                raise PublicationError("WRITE_FAILED",
                                       "Could not create publication branch: " +
                                       _detail(result), retryable=True)
            _push(root, remote, head, expected_head, runner)
        else:
            _fetch(root, remote, head, runner)
            if _local_tip(root, head, runner) != remote_tip:
                raise PublicationError("CONFLICT",
                                       "Publication branch does not match the "
                                       "trusted remote")
    elif local != expected_head:
        if remote_tip is None:
            raise PublicationError(
                "CONFLICT",
                "Publication branch was deleted after merge; retrying this "
                "idempotency key is not recoverable")
        if remote_tip != local:
            _fetch(root, remote, head, runner)
            if _local_tip(root, head, runner) != remote_tip:
                raise PublicationError("CONFLICT",
                                       "Publication branch does not match the "
                                       "trusted remote")
    elif remote_tip is None:
        _push(root, remote, head, expected_head, runner)
    elif remote_tip != expected_head:
        _fetch(root, remote, head, runner)
        if _local_tip(root, head, runner) != remote_tip:
            raise PublicationError("CONFLICT",
                                   "Publication branch does not match the "
                                   "trusted remote")
    return head


def ensure_pull_request(root, base, head, title, body, runner=run):
    """Reuse one open PR for this head/base, otherwise create it."""
    if (type(base) is not str or not BRANCH.fullmatch(base) or ".." in base or
            type(head) is not str or not BRANCH.fullmatch(head) or
            ".." in head or type(title) is not str or not title.strip() or
            type(body) is not str):
        raise PublicationError("VALIDATION_ERROR",
                               "Invalid pull request parameters")
    list_args = ["gh", "pr", "list", "--head", head, "--base", base,
                 "--state", "open", "--json", "number,url"]
    try:
        listed = runner(list_args, cwd=root, timeout=GH_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"state": "failed", "detail": "gh CLI unavailable: " + str(exc)[:200]}
    if listed.returncode:
        return {"state": "failed",
                "detail": "gh pr list failed: " + _detail(listed)}
    try:
        found = json.loads(listed.stdout or "[]")
    except ValueError:
        return {"state": "failed", "detail": "gh pr list returned invalid JSON"}
    if type(found) is list and found:
        first = found[0]
        number = first.get("number") if type(first) is dict else None
        url = first.get("url") if type(first) is dict else None
        if type(number) is int and type(url) is str and url:
            return {"state": "open", "number": number, "url": url}
        return {"state": "failed",
                "detail": "gh pr list returned invalid pull request metadata"}

    create_args = ["gh", "pr", "create", "--base", base, "--head", head,
                   "--title", title, "--body", body]
    try:
        created = runner(create_args, cwd=root, timeout=GH_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"state": "failed", "detail": "gh CLI unavailable: " + str(exc)[:200]}
    if created.returncode:
        return {"state": "failed",
                "detail": "gh pr create failed: " + _detail(created)}
    url = ""
    for line in reversed((created.stdout or "").strip().splitlines()):
        if line.strip().startswith("http"):
            url = line.strip()
            break
    match = re.search(r"/pull/(\d+)", url)
    return {"state": "open", "number": int(match.group(1)) if match else None,
            "url": url or None}


def enable_auto_merge(root, number, runner=run):
    """Opt-in squash auto-merge for exactly the PR just ensured.

    GitHub still enforces required checks; this only enables auto-merge for
    that PR number and never names a different head.
    """
    if type(number) is not int or number < 1:
        raise PublicationError("VALIDATION_ERROR",
                               "Invalid pull request number")
    argv = ["gh", "pr", "merge", str(number), "--auto", "--squash",
            "--delete-branch"]
    try:
        result = runner(argv, cwd=root, timeout=GH_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"state": "failed", "detail": "gh CLI unavailable: " + str(exc)[:200]}
    if result.returncode == 0:
        detail = (result.stdout or "").strip()[:400]
        return {"state": "enabled",
                "detail": detail or "Auto-merge enabled with squash"}
    text = _detail(result)
    lowered = text.casefold()
    reason = ("auto_merge_not_allowed"
              if ("auto-merge" in lowered or "auto merge" in lowered) and
              ("not allowed" in lowered or "disabled" in lowered or
               "not enabled" in lowered) else "command_failed")
    return {"state": "failed", "reason": reason, "detail": text}


def build_body(record, event, summary, validators):
    """Markdown PR body with exactly the facts the adapter can verify."""
    record = record if type(record) is dict else {}
    event = event if type(event) is dict else {}

    def one(value):
        return " ".join(str(value or "").split())

    path = one(record.get("path"))
    title = one(record.get("title"))
    record_id = one(record.get("record_id") or record.get("id"))
    event_id = one(event.get("event_id") or event.get("id"))
    head = one(event.get("head"))
    status = one(record.get("status"))
    visibility = one(record.get("visibility"))
    summary_text = one(summary)
    lines = [
        "# Knowledge Hub record change",
        "",
        "## Record",
        "",
        "- Path: `" + path + "`",
        "- Title: " + title,
        "- Record ID: `" + record_id + "`",
        "- Event ID: `" + event_id + "`",
        "- Commit: `" + head + "`",
        "- Status: " + status,
        "- Visibility: " + visibility,
        "",
        "## Summary",
        "",
        summary_text,
        "",
        "## Validators run",
        "",
    ]
    lines.extend("- " + one(item) for item in (validators or ()))
    lines.extend([
        "",
        "The repository's `validate-openwiki` CI check runs on this pull "
        "request; the validators above ran in the trusted writer before the "
        "commit was created.",
        "",
        "## Privacy",
        "",
        PRIVACY_NOTE,
        "",
    ])
    return "\n".join(lines)
