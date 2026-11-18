"""Local M-04 source-ref CAS primitive, safe to rehearse in disposable Git repos.

This module is NOT a production cutover command. A caller must separately prove
#36/#37 integration gates, writer quiescence, publication policy, manifest and
history reconciliation, and remote branch authorization. Never use this as an
alternative to GitHub branch protection or as a network transaction.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Callable

HEX_HEAD = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class CutoverError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def git(root, *args, checked=True):
    result = subprocess.run(["git", *args], cwd=Path(root), capture_output=True)
    if checked and result.returncode:
        raise CutoverError("GIT_ERROR", "Git operation failed; source may be unchanged or outcome uncertain")
    return (result.stdout.decode("utf-8", "strict").strip()
            if result.returncode == 0 else None)


def _sha(value):
    if type(value) is not str or HEX_HEAD.fullmatch(value) is None:
        raise CutoverError("VALIDATION_ERROR", "Expected exact source SHA")
    return value


def preflight(root, branch, frozen_head, candidate):
    """Check candidate is exactly one prepared commit on the frozen live head."""
    root = Path(root).resolve(strict=True)
    frozen_head = _sha(frozen_head)
    candidate = _sha(candidate)
    if (type(branch) is not str or not branch or branch.startswith("-") or
            git(root, "check-ref-format", "--branch", branch, checked=False) is None):
        raise CutoverError("VALIDATION_ERROR", "Invalid target branch")
    if os.environ.get("KH_WRITES_MAINTENANCE") != "1":
        raise CutoverError("MAINTENANCE", "All trusted writers must be paused before source CAS")
    current = git(root, "rev-parse", "--verify", "refs/heads/" + branch)
    if current != frozen_head:
        raise CutoverError("CONFLICT", "Source head changed; re-inventory and re-rehearse from new frozen head")
    if candidate == frozen_head or git(root, "cat-file", "-t", candidate) != "commit":
        raise CutoverError("VALIDATION_ERROR", "Candidate must be a new commit")
    parents = git(root, "rev-list", "--parents", "-n", "1", candidate).split()
    if parents != [candidate, frozen_head]:
        raise CutoverError("VALIDATION_ERROR", "Candidate must be exactly one non-merge commit on frozen head")
    return current


def compare_and_swap(root, branch, frozen_head, candidate, *,
                     validate: Callable[[str], None] | None = None,
                     fault: Callable[[str], None] | None = None):
    """Commit only a previously prepared, independently validated candidate.

    The validate callback must perform all M-04 content and eligibility checks.
    This primitive does not invent them. If validation is absent, refuse.
    Faults after CAS are deliberately NOT automatically rolled back.
    """
    preflight(root, branch, frozen_head, candidate)
    if validate is None:
        raise CutoverError("VALIDATION_ERROR", "Verified migration and generation gate is required")
    validate(candidate)
    if fault:
        fault("validated")
    # Expected OLD value is the compare-and-swap guard. Never use --force.
    if fault:
        fault("before_cas")
    result = subprocess.run(
        ["git", "update-ref", "refs/heads/" + branch, candidate, frozen_head],
        cwd=Path(root), capture_output=True,
    )
    if result.returncode:
        raise CutoverError("CONFLICT", "CAS rejected; source changed, so repeat rehearsal")
    # No source rollback on an uncertain response or post-cutover writes.
    if fault:
        fault("after_cas")
    if git(root, "rev-parse", "--verify", "refs/heads/" + branch) != candidate:
        raise CutoverError("OUTCOME_UNCERTAIN", "Inspect source ref and durable receipts; do not retry blindly")
    return {"status": "committed", "head": candidate, "previous_head": frozen_head}
