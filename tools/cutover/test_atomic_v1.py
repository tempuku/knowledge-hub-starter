"""Disposable Git acceptance for the M-04 local source CAS primitive."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from atomic_v1 import CutoverError, compare_and_swap, preflight


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class CASFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        (self.root / "record.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.base = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-qb", "candidate")
        (self.root / "record.txt").write_text("candidate\n", encoding="utf-8")
        git(self.root, "commit", "-qam", "atomic source migration candidate")
        self.candidate = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-q", "main")

    def main(self):
        return git(self.root, "rev-parse", "main")

    def test_no_maintenance_refuses_without_ref_change(self):
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "0"}):
            with self.assertRaises(CutoverError) as err:
                compare_and_swap(self.root, "main", self.base, self.candidate,
                                 validate=lambda _: None)
        self.assertEqual(err.exception.code, "MAINTENANCE")
        self.assertEqual(self.main(), self.base)

    def test_missing_validation_callback_refuses(self):
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaises(CutoverError) as err:
                compare_and_swap(self.root, "main", self.base, self.candidate)
        self.assertEqual(err.exception.code, "VALIDATION_ERROR")
        self.assertEqual(self.main(), self.base)

    def test_validation_rejection_is_atomic(self):
        def reject(_candidate):
            raise CutoverError("INTEGRITY_ERROR", "Missing manifest coverage")
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaises(CutoverError) as err:
                compare_and_swap(self.root, "main", self.base, self.candidate,
                                 validate=reject)
        self.assertEqual(err.exception.code, "INTEGRITY_ERROR")
        self.assertEqual(self.main(), self.base)

    def test_pre_cas_failure_keeps_source_unchanged(self):
        def fail(point):
            if point == "before_cas":
                raise RuntimeError("injected crash")
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaisesRegex(RuntimeError, "injected crash"):
                compare_and_swap(self.root, "main", self.base, self.candidate,
                                 validate=lambda _: None, fault=fail)
        self.assertEqual(self.main(), self.base)

    def test_cas_collision_preserves_concurrent_winner(self):
        git(self.root, "checkout", "-qb", "concurrent")
        (self.root / "other.txt").write_text("concurrent\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "concurrent writer")
        winner = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-q", "main")

        def race(point):
            if point == "before_cas":
                git(self.root, "update-ref", "refs/heads/main", winner, self.base)

        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaises(CutoverError) as err:
                compare_and_swap(self.root, "main", self.base, self.candidate,
                                 validate=lambda _: None, fault=race)
        self.assertEqual(err.exception.code, "CONFLICT")
        self.assertEqual(self.main(), winner)

    def test_post_cas_crash_does_not_rollback_new_source(self):
        def crash(point):
            if point == "after_cas":
                raise RuntimeError("response lost")
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaisesRegex(RuntimeError, "response lost"):
                compare_and_swap(self.root, "main", self.base, self.candidate,
                                 validate=lambda _: None, fault=crash)
        self.assertEqual(self.main(), self.candidate)
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaises(CutoverError) as err:
                compare_and_swap(self.root, "main", self.base, self.candidate,
                                 validate=lambda _: None)
        self.assertEqual(err.exception.code, "CONFLICT")

    def test_exact_one_commit_on_frozen_base(self):
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            preflight(self.root, "main", self.base, self.candidate)
            result = compare_and_swap(self.root, "main", self.base, self.candidate,
                                      validate=lambda c: self.assertEqual(c, self.candidate))
        self.assertEqual(result, {"status": "committed", "previous_head": self.base,
                                  "head": self.candidate})
        self.assertEqual(self.main(), self.candidate)

    def test_two_commits_cannot_disguise_unrehearsed_source(self):
        git(self.root, "checkout", "-q", "candidate")
        (self.root / "extra.txt").write_text("unexpected\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "unrehearsed additional commit")
        second = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-q", "main")
        with patch.dict(os.environ, {"KH_WRITES_MAINTENANCE": "1"}):
            with self.assertRaises(CutoverError) as err:
                compare_and_swap(self.root, "main", self.base, second,
                                 validate=lambda _: None)
        self.assertEqual(err.exception.code, "VALIDATION_ERROR")
        self.assertEqual(self.main(), self.base)


if __name__ == "__main__":
    unittest.main()
