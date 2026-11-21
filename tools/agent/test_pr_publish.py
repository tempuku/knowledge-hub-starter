#!/usr/bin/env python3
"""Offline tests for pull-request publication mode (issue #114).

All `git` and `gh` calls go through an injected fake runner: no network, no
real GitHub CLI and no real repository is touched by these unit tests.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcp_server  # noqa: E402
import pr_publish  # noqa: E402

HEAD = "a" * 40
OTHER = "b" * 40
RECORD_ID = "11111111-1111-4111-8111-111111111111"
EVENT_ID = "22222222-2222-4222-8222-222222222222"
PATH = "openwiki/notes/alpha.md"
CONTENT = ('---\ntype: note\ntitle: "Alpha note"\nstatus: draft\n'
           'visibility: private\n---\n\nBody\n')


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def __call__(self, argv, *, cwd=None, timeout=None):
        argv = list(argv)
        self.calls.append((argv, str(cwd), timeout))
        return self.handler(argv)

    def commands(self):
        return [call[0] for call in self.calls]


def branch_handler(*, branch_rc=0, push_rc=0, local=None, remote=None):
    def handler(argv):
        if argv[:2] == ["git", "rev-parse"]:
            return Result(0, local + "\n") if local else Result(1, "")
        if argv[:2] == ["git", "ls-remote"]:
            return Result(0, (remote + "\t" + argv[4] + "\n") if remote
                          else "")
        if argv[:2] == ["git", "branch"]:
            return Result(branch_rc, "", "" if branch_rc == 0 else "exists")
        if argv[:2] == ["git", "push"]:
            return Result(push_rc, "", "" if push_rc == 0 else "rejected")
        raise AssertionError("unexpected git command: " + repr(argv))
    return handler


class BuildBodyTest(unittest.TestCase):
    def test_body_states_verifiable_facts_and_privacy(self):
        body = pr_publish.build_body(
            {"path": PATH, "title": "Alpha note", "record_id": RECORD_ID,
             "status": "draft", "visibility": "private"},
            {"event_id": EVENT_ID, "head": HEAD},
            "Created alpha note",
            ["staged OKF checker", "v1 chain validation"],
        )
        for value in (PATH, "Alpha note", RECORD_ID, EVENT_ID, HEAD, "draft",
                      "private", "Created alpha note", "staged OKF checker",
                      "v1 chain validation"):
            self.assertIn(value, body)
        self.assertIn("does not protect files in a public Git repository",
                      body)
        self.assertIn("validate-openwiki", body)
        self.assertNotIn("Body", body)


class BranchNameTest(unittest.TestCase):
    def test_name_is_deterministic_per_idempotency_key(self):
        key = "1a2b3c4d-0000-4000-8000-000000000000"
        first = pr_publish.publication_branch(key, PATH)
        second = pr_publish.publication_branch(key, PATH)
        self.assertEqual(first, second)
        self.assertEqual(first, "agent/knowledge/alpha-1a2b3c4d")
        self.assertNotEqual(first, pr_publish.publication_branch(
            "9f8e7d6c-0000-4000-8000-000000000000", PATH))
        self.assertEqual(pr_publish.publication_branch(key, None),
                         "agent/knowledge/record-1a2b3c4d")
        self.assertRegex(first, pr_publish.BRANCH)

    def test_invalid_key_rejected(self):
        with self.assertRaises(pr_publish.PublicationError) as caught:
            pr_publish.publication_branch(None, PATH)
        self.assertEqual(caught.exception.code, "VALIDATION_ERROR")


class PrepareBranchTest(unittest.TestCase):
    def test_branch_is_created_and_pushed_at_expected_head(self):
        runner = FakeRunner(branch_handler())
        head = "agent/knowledge/alpha-1a2b3c4d"
        self.assertEqual(pr_publish.prepare_publication_branch(
            "/repo", "origin", head, HEAD, runner=runner), head)
        self.assertEqual(runner.commands(), [
            ["git", "rev-parse", "--verify", "--quiet",
             "refs/heads/" + head],
            ["git", "ls-remote", "--heads", "origin",
             "refs/heads/" + head],
            ["git", "branch", head, HEAD],
            ["git", "push", "origin", HEAD + ":refs/heads/" + head],
        ])

    def test_branch_creation_failure_is_structured_and_no_push(self):
        runner = FakeRunner(branch_handler(branch_rc=1))
        with self.assertRaises(pr_publish.PublicationError) as caught:
            pr_publish.prepare_publication_branch(
                "/repo", "origin", "agent/knowledge/alpha-1a2b3c4d", HEAD,
                runner=runner)
        self.assertEqual(caught.exception.code, "WRITE_FAILED")
        self.assertFalse(any(cmd[:2] == ["git", "push"]
                             for cmd in runner.commands()))

    def test_push_failure_is_structured(self):
        runner = FakeRunner(branch_handler(push_rc=1))
        with self.assertRaises(pr_publish.PublicationError) as caught:
            pr_publish.prepare_publication_branch(
                "/repo", "origin", "agent/knowledge/alpha-1a2b3c4d", HEAD,
                runner=runner)
        self.assertEqual(caught.exception.code, "WRITE_FAILED")

    def test_deleted_branch_after_merge_conflicts(self):
        runner = FakeRunner(branch_handler(local=OTHER))
        with self.assertRaises(pr_publish.PublicationError) as caught:
            pr_publish.prepare_publication_branch(
                "/repo", "origin", "agent/knowledge/alpha-1a2b3c4d", HEAD,
                runner=runner)
        self.assertEqual(caught.exception.code, "CONFLICT")

    def test_merged_deleted_publication_conflicts_before_branch(self):
        runner = FakeRunner(branch_handler())
        with self.assertRaises(pr_publish.PublicationError) as caught:
            pr_publish.prepare_publication_branch(
                "/repo", "origin", "agent/knowledge/alpha-1a2b3c4d", HEAD,
                runner=runner, merged_check=lambda: 3)
        self.assertEqual(caught.exception.code, "CONFLICT")
        self.assertFalse(any(cmd[:2] in (["git", "branch"], ["git", "push"])
                             for cmd in runner.commands()))


class MergedPublicationTest(unittest.TestCase):
    def test_merged_pr_for_head_is_reported(self):
        runner = FakeRunner(lambda argv: Result(0, json.dumps(
            [{"number": 3, "state": "MERGED"}])))
        self.assertEqual(pr_publish.merged_publication(
            "/repo", "agent/knowledge/alpha-1a2b3c4d", runner=runner), 3)
        self.assertEqual(runner.commands()[0], [
            "gh", "pr", "list", "--head", "agent/knowledge/alpha-1a2b3c4d",
            "--state", "all", "--json", "number,state",
        ])

    def test_unavailable_gh_does_not_block(self):
        runner = FakeRunner(lambda argv: (_ for _ in ()).throw(
            FileNotFoundError("gh")))
        self.assertIsNone(pr_publish.merged_publication(
            "/repo", "agent/knowledge/alpha-1a2b3c4d", runner=runner))


class EnsurePullRequestTest(unittest.TestCase):
    def test_existing_open_pr_is_reused(self):
        runner = FakeRunner(lambda argv: Result(
            0, json.dumps([{"number": 7,
                            "url": "https://example.invalid/pull/7"}])))
        result = pr_publish.ensure_pull_request(
            "/repo", "main", "agent/knowledge/alpha-1a2b3c4d", "Title", "Body",
            runner=runner)
        self.assertEqual(result, {"state": "open", "number": 7,
                                  "url": "https://example.invalid/pull/7"})
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(runner.commands()[0], [
            "gh", "pr", "list", "--head", "agent/knowledge/alpha-1a2b3c4d",
            "--base", "main", "--state", "open", "--json", "number,url",
        ])

    def test_pr_is_created_when_absent(self):
        def handler(argv):
            if argv[:3] == ["gh", "pr", "list"]:
                return Result(0, "[]")
            return Result(0, "https://example.invalid/pull/12\n")
        runner = FakeRunner(handler)
        result = pr_publish.ensure_pull_request(
            "/repo", "main", "agent/knowledge/alpha-1a2b3c4d", "Title", "Body",
            runner=runner)
        self.assertEqual(result, {"state": "open", "number": 12,
                                  "url": "https://example.invalid/pull/12"})
        self.assertEqual(runner.commands()[1], [
            "gh", "pr", "create", "--base", "main",
            "--head", "agent/knowledge/alpha-1a2b3c4d",
            "--title", "Title", "--body", "Body",
        ])

    def test_missing_gh_is_a_structured_failure(self):
        runner = FakeRunner(lambda argv: (_ for _ in ()).throw(
            FileNotFoundError("gh")))
        result = pr_publish.ensure_pull_request(
            "/repo", "main", "agent/knowledge/alpha-1a2b3c4d", "Title", "Body",
            runner=runner)
        self.assertEqual(result["state"], "failed")
        self.assertIn("gh CLI unavailable", result["detail"])

    def test_non_zero_exit_is_a_structured_failure(self):
        runner = FakeRunner(lambda argv: Result(1, "", "authentication required"))
        result = pr_publish.ensure_pull_request(
            "/repo", "main", "agent/knowledge/alpha-1a2b3c4d", "Title", "Body",
            runner=runner)
        self.assertEqual(result["state"], "failed")
        self.assertIn("authentication required", result["detail"])

    def test_never_uses_shell(self):
        runner = FakeRunner(lambda argv: Result(0, "[]"))
        pr_publish.ensure_pull_request(
            "/repo", "main", "agent/knowledge/alpha-1a2b3c4d", "Title", "Body",
            runner=runner)
        self.assertTrue(all(isinstance(call[0], list) for call in runner.calls))


class AutoMergeTest(unittest.TestCase):
    def test_success_is_explicit_squash_auto_merge(self):
        runner = FakeRunner(lambda argv: Result(0, "auto-merge enabled"))
        result = pr_publish.enable_auto_merge("/repo", 7, runner=runner)
        self.assertEqual(result["state"], "enabled")
        self.assertEqual(runner.commands()[0], [
            "gh", "pr", "merge", "7", "--auto", "--squash", "--delete-branch",
        ])

    def test_disallowed_auto_merge_is_non_fatal(self):
        runner = FakeRunner(lambda argv: Result(
            1, "", "Auto-merge is not allowed for this repository"))
        result = pr_publish.enable_auto_merge("/repo", 7, runner=runner)
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["reason"], "auto_merge_not_allowed")
        self.assertIn("not allowed", result["detail"])


class FakeWriter:
    def __init__(self):
        self.writes = []
        self.reads = []

    def read(self, record_id):
        self.reads.append(record_id)
        return {"record_id": record_id, "path": PATH, "content": CONTENT,
                "version": EVENT_ID, "head": HEAD}

    def write(self, request):
        self.writes.append(request)
        return {"status": "committed", "record_id": RECORD_ID,
                "event_id": EVENT_ID, "operation_id": RECORD_ID,
                "version": EVENT_ID, "head": HEAD, "record_url": PATH,
                "event_url": PATH[:-3] + ".log.md#" + EVENT_ID,
                "diff_url": HEAD, "publication": "pending"}


def call(name, **fields):
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "knowledge_" + name,
                       "arguments": fields}}


def write_fields(**extra):
    return {"expected_head": HEAD,
            "idempotency_key": "1a2b3c4d-0000-4000-8000-000000000000",
            "actor": {"id": "agent", "kind": "agent", "label": "Agent"},
            "summary": "Create alpha note", **extra}


def payload(result):
    return json.loads(result["content"][0]["text"])


class McpPrModeTest(unittest.TestCase):
    publication = {"root": "/repo", "base": "main", "remote": "origin",
                   "auto_merge": False, "capability_file": "/cap.json"}

    def handler(self, merge=None):
        state = {}

        def handle(argv):
            if argv[:2] == ["git", "rev-parse"]:
                return Result(1, "")
            if argv[:2] == ["git", "ls-remote"]:
                return Result(0, "")
            if argv[:2] == ["git", "branch"]:
                return Result(0)
            if argv[:2] == ["git", "push"]:
                state["pushed"] = True
                state["push_calls"] = len(runner.calls)
                return Result(0)
            if argv[:3] == ["gh", "pr", "list"]:
                return Result(0, "[]")
            if argv[:3] == ["gh", "pr", "create"]:
                return Result(0, "https://example.invalid/pull/9\n")
            if argv[:3] == ["gh", "pr", "merge"]:
                return merge or Result(0, "enabled")
            raise AssertionError("unexpected command: " + repr(argv))
        runner = FakeRunner(handle)
        return runner, state

    def test_pr_mode_adds_fields_and_keeps_publication_pending(self):
        runner, state = self.handler()
        writer = FakeWriter()
        created = []

        def factory(head):
            created.append((head, len(runner.calls)))
            return writer

        result = mcp_server._dispatch(
            FakeWriter(), call("create", **write_fields(path=PATH,
                                                        content=CONTENT)),
            self.publication, runner=runner, writer_factory=factory)
        self.assertFalse(result["isError"], payload(result))
        response = payload(result)
        self.assertEqual(response["status"], "committed")
        self.assertEqual(response["publication"], "pending")
        self.assertEqual(response["pull_request"],
                         {"state": "open", "number": 9,
                          "url": "https://example.invalid/pull/9"})
        self.assertIs(response["auto_merge"], False)
        self.assertTrue(state["pushed"])
        self.assertEqual(created[0][0], "agent/knowledge/alpha-1a2b3c4d")
        # The branch was pushed before the writer was constructed.
        self.assertEqual(created[0][1], state["push_calls"])
        self.assertEqual(runner.commands()[created[0][1] - 1][:2],
                         ["git", "push"])
        self.assertFalse(any(cmd[:3] == ["gh", "pr", "merge"]
                             for cmd in runner.commands()))

    def test_auto_merge_failure_keeps_commit_result(self):
        runner, _ = self.handler(
            Result(1, "", "Auto-merge is not allowed for this repository"))
        publication = {**self.publication, "auto_merge": True}
        result = mcp_server._dispatch(
            FakeWriter(), call("create", **write_fields(path=PATH,
                                                        content=CONTENT)),
            publication, runner=runner,
            writer_factory=lambda head: FakeWriter())
        response = payload(result)
        self.assertFalse(result["isError"], response)
        self.assertEqual(response["status"], "committed")
        self.assertEqual(response["publication"], "pending")
        self.assertEqual(response["pull_request"]["state"], "open")
        self.assertEqual(response["auto_merge"]["state"], "failed")
        self.assertEqual(response["auto_merge"]["reason"],
                         "auto_merge_not_allowed")

    def test_auto_merge_success_is_true(self):
        runner, _ = self.handler()
        publication = {**self.publication, "auto_merge": True}
        result = mcp_server._dispatch(
            FakeWriter(), call("create", **write_fields(path=PATH,
                                                        content=CONTENT)),
            publication, runner=runner,
            writer_factory=lambda head: FakeWriter())
        self.assertIs(payload(result)["auto_merge"], True)

    def test_branch_failure_never_calls_writer(self):
        def handle(argv):
            if argv[:2] == ["git", "rev-parse"]:
                return Result(1, "")
            if argv[:2] == ["git", "ls-remote"]:
                return Result(0, "")
            if argv[:3] == ["gh", "pr", "list"]:
                return Result(0, "[]")
            if argv[:2] == ["git", "branch"]:
                return Result(1, "", "cannot create")
            raise AssertionError("unexpected command: " + repr(argv))
        runner = FakeRunner(handle)
        writer = FakeWriter()
        created = []
        result = mcp_server._dispatch(
            writer, call("create", **write_fields(path=PATH, content=CONTENT)),
            self.publication, runner=runner,
            writer_factory=lambda head: created.append(head) or writer)
        response = payload(result)
        self.assertTrue(result["isError"])
        self.assertEqual(response["code"], "WRITE_FAILED")
        self.assertEqual(writer.writes, [])
        self.assertEqual(created, [])
        self.assertNotIn("pull_request", response)

    def test_non_pr_launch_is_unchanged(self):
        def handler(argv):
            raise AssertionError("non-PR launch must not run commands")

        runner = FakeRunner(handler)
        writer = FakeWriter()

        def factory(head):
            raise AssertionError("non-PR launch must not create a branch writer")

        result = mcp_server._dispatch(
            writer, call("create", **write_fields(path=PATH, content=CONTENT)),
            None, runner=runner, writer_factory=factory)
        response = payload(result)
        self.assertFalse(result["isError"], response)
        self.assertEqual(response["status"], "committed")
        self.assertNotIn("pull_request", response)
        self.assertNotIn("auto_merge", response)
        self.assertEqual(len(writer.writes), 1)

    def test_read_tool_never_runs_publication(self):
        def handler(argv):
            raise AssertionError("read must not run commands")

        result = mcp_server._dispatch(
            FakeWriter(), call("read", record_id=RECORD_ID), self.publication,
            runner=FakeRunner(handler),
            writer_factory=lambda head: FakeWriter())
        response = payload(result)
        self.assertEqual(response["record_id"], RECORD_ID)
        self.assertNotIn("pull_request", response)

    def test_flags_default_off_and_auto_merge_requires_pr_base(self):
        parser = mcp_server.build_parser()
        args = parser.parse_args(["--root", "/repo",
                                  "--capability-file", "/cap.json"])
        self.assertIsNone(args.pr_base)
        self.assertFalse(args.auto_merge)
        enabled = parser.parse_args([
            "--root", "/repo", "--capability-file", "/cap.json",
            "--pr-base", "main", "--auto-merge"])
        self.assertEqual(enabled.pr_base, "main")
        self.assertTrue(enabled.auto_merge)


if __name__ == "__main__":
    unittest.main()
