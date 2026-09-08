#!/usr/bin/env python3
"""Xuyiming：公共工具行为回归；临时 Git 仓库隔离，远端写入全部使用 mock。"""

import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_script(plugin, name):
    path = ROOT / "plugins" / plugin / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


git_context = load_script("xym-dev-tools", "git_context")
github = load_script("xym-dev-tools", "github_review")
lark = load_script("xym-lark-tools", "lark_api")


class GitContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xym-git-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Xuyiming")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.hooksPath", str(self.repo / "disabled-hooks"))
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True).stdout

    def commit(self, text="base\n"):
        (self.repo / "tracked.txt").write_text(text)
        self.git("add", "tracked.txt")
        self.git("commit", "-m", "test fixture")

    def test_unborn_repository_and_unusual_filename(self):
        name = "空 格\nfile.txt"
        (self.repo / name).write_text("new file\n")
        context, diff = git_context.collect(self.repo, "all")
        self.assertIsNone(context["head"])
        self.assertEqual(context["files"], [{"status": "?", "path": name}])
        self.assertIn(b"+new file", diff)

    def test_scopes_preserve_index_bytes_and_untracked_files(self):
        self.commit()
        (self.repo / "tracked.txt").write_text("staged\n")
        self.git("add", "tracked.txt")
        (self.repo / "tracked.txt").write_text("working\n")
        (self.repo / "extra.txt").write_text("untracked\n")
        before = (self.repo / ".git/index").read_bytes()
        staged, staged_diff = git_context.collect(self.repo, "staged")
        unstaged, unstaged_diff = git_context.collect(self.repo, "unstaged")
        all_context, all_diff = git_context.collect(self.repo, "all")
        self.assertEqual(before, (self.repo / ".git/index").read_bytes())
        self.assertEqual(len(staged["files"]), 1)
        self.assertIn(b"+staged", staged_diff)
        self.assertNotIn(b"working", staged_diff)
        self.assertIn(b"-staged", unstaged_diff)
        self.assertIn(b"+working", unstaged_diff)
        self.assertEqual(len(unstaged["files"]), 2)
        self.assertEqual(len(all_context["files"]), 2)
        self.assertIn(b"-base", all_diff)

    def test_branch_excludes_uncommitted_changes_and_commit_scope(self):
        self.commit()
        self.git("checkout", "-b", "feature")
        self.commit("feature\n")
        (self.repo / "tracked.txt").write_text("not committed\n")
        context, diff = git_context.collect(self.repo, "branch", "main")
        self.assertEqual(context["target"], self.git("rev-parse", "HEAD").decode().strip())
        self.assertIn(b"+feature", diff)
        self.assertNotIn(b"not committed", diff)
        self.assertEqual(diff, git_context.collect(self.repo, "commit:HEAD")[1])

    def test_merge_requires_explicit_base(self):
        self.commit()
        self.git("checkout", "-b", "feature")
        self.commit("feature\n")
        self.git("checkout", "main")
        self.git("merge", "--no-ff", "feature", "-m", "test merge")
        with self.assertRaisesRegex(git_context.ReviewError, "Merge commit"):
            git_context.collect(self.repo, "commit:HEAD")
        self.assertIn(b"+feature", git_context.collect(self.repo, "commit:HEAD", "HEAD^1")[1])

    def test_binary_and_symlink_are_reported(self):
        (self.repo / "binary").write_bytes(b"\0\xff")
        (self.repo / "link").symlink_to("unavailable-target")
        context, diff = git_context.collect(self.repo, "all")
        self.assertTrue(any("Binary" in item for item in context["limitations"]))
        self.assertIn(b"+unavailable-target", diff)

    def test_existing_output_directory_not_overwritten(self):
        result = subprocess.run([sys.executable, git_context.__file__, "--repo", str(self.repo),
                                 "--out", str(self.repo)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.repo / "context.json").exists())

    def test_mutable_scope_does_not_accept_base(self):
        with self.assertRaisesRegex(git_context.ReviewError, "--base applies"):
            git_context.collect(self.repo, "all", "main")


def page(nodes, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor}}


def thread(identifier="T1", resolved=False, comment_cursor=None):
    return {"id": identifier, "isResolved": resolved, "isOutdated": False, "path": "file.py",
            "line": 1, "originalLine": 1,
            "comments": page([{"id": "C1", "databaseId": 42, "body": "feedback"}], comment_cursor)}


def pr_response(threads, cursor=None, head="abc123"):
    return {"repository": {"pullRequest": {"number": 1, "title": "test", "url": "https://example.invalid/pr/1",
            "state": "OPEN", "headRefOid": head, "reviewDecision": "CHANGES_REQUESTED",
            "reviewThreads": page(threads, cursor)}}}


class FakeGitHub:
    hostname = "github.com"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def graphql(self, query, variables):
        self.calls.append((query, variables))
        return next(self.responses)


class GitHubTests(unittest.TestCase):
    def snapshot(self, resolved=False):
        return github.inspect_review(FakeGitHub([pr_response([thread(resolved=resolved)])]), "owner/repo", 1)

    def test_both_pagination_levels(self):
        client = FakeGitHub([
            pr_response([thread(comment_cursor="comments2")], "threads2"),
            {"node": {"comments": page([{"id": "C2", "databaseId": 43, "body": "reply"}])}},
            pr_response([thread("T2", resolved=True)]),
        ])
        result = github.inspect_review(client, "owner/repo", 1)
        self.assertEqual(len(result["threads"]), 2)
        self.assertEqual(len(result["threads"][0]["comments"]), 2)
        self.assertEqual(result["unresolved_count"], 1)
        self.assertEqual(client.calls[1][1]["cursor"], "comments2")
        self.assertEqual(client.calls[2][1]["cursor"], "threads2")

    def test_repeated_cursor_fails(self):
        with self.assertRaises(github.ReviewError):
            github.next_cursor(page([], "same"), {"same"})

    def test_head_changed_during_pagination(self):
        client = FakeGitHub([pr_response([], "next"), pr_response([], head="new-head")])
        with self.assertRaisesRegex(github.ReviewError, "HEAD"):
            github.inspect_review(client, "owner/repo", 1)

    def test_wrong_head_and_foreign_thread_block_writes(self):
        for thread_id, head in (("T1", "old-head"), ("foreign", "abc123")):
            with self.subTest(thread=thread_id):
                with self.assertRaises(github.ReviewError):
                    github.mutation_plan(self.snapshot(), "resolve", thread_id, expected_head=head)

    def test_reply_targets_root_comment_and_keeps_exact_body(self):
        body = '引号 "\n$(touch /not-executed)'
        plan = github.mutation_plan(self.snapshot(), "reply", "T1", body)
        self.assertEqual(plan["endpoint"], "repos/owner/repo/pulls/1/comments/42/replies")
        self.assertEqual(plan["payload"]["body"], body)

    def test_already_resolved_is_noop(self):
        plan = github.mutation_plan(self.snapshot(True), "resolve", "T1")
        self.assertEqual(plan["status"], "already_resolved")
        self.assertNotIn("endpoint", plan)

    def test_graphql_errors_are_not_silently_partial(self):
        response = subprocess.CompletedProcess([], 0, '{"data": {}, "errors": [{"message":"denied"}]}', "")
        with patch.object(github.subprocess, "run", return_value=response) as run:
            with self.assertRaises(github.ReviewError):
                github.GitHub().graphql("query", {})
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertEqual(json.loads(run.call_args.kwargs["input"])["query"], "query")

    def test_preview_never_sends_mutation(self):
        snapshot = self.snapshot()
        with patch.object(github, "inspect_review", return_value=snapshot), \
             patch.object(github.GitHub, "request") as request, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(github.main(["resolve", "--repo", "owner/repo", "--pr", "1", "--thread-id", "T1"]), 0)
            request.assert_not_called()

    def test_execute_resolves_once_and_validates_response(self):
        snapshot = self.snapshot()
        response = {"data": {"resolveReviewThread": {"thread": {"id": "T1", "isResolved": True}}}}
        with patch.object(github, "inspect_review", return_value=snapshot), \
             patch.object(github.GitHub, "request", return_value=response) as request, \
             contextlib.redirect_stdout(io.StringIO()):
            result = github.main(["resolve", "--repo", "owner/repo", "--pr", "1", "--thread-id", "T1",
                                  "--expected-head", "abc123", "--execute"])
            self.assertEqual(result, 0)
            request.assert_called_once()

    def test_execute_requires_previously_verified_head(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            github.parse_args(["resolve", "--repo", "owner/repo", "--pr", "1", "--thread-id", "T1", "--execute"])

    def test_write_timeout_never_retries(self):
        snapshot = self.snapshot()
        with patch.object(github, "inspect_review", return_value=snapshot), \
             patch.object(github.GitHub, "request", side_effect=subprocess.TimeoutExpired("gh", 1)) as request, \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            result = github.main(["resolve", "--repo", "owner/repo", "--pr", "1", "--thread-id", "T1",
                                  "--expected-head", "abc123", "--execute"])
            self.assertEqual(result, 2)
            request.assert_called_once()
            self.assertIn("回查", errors.getvalue())

    def test_reply_does_not_report_empty_success(self):
        snapshot = self.snapshot()
        with tempfile.TemporaryDirectory(prefix="xym-reply-test-") as directory:
            body = Path(directory) / "reply.txt"
            body.write_text("verified reply")
            with patch.object(github, "inspect_review", return_value=snapshot), \
                 patch.object(github.GitHub, "request", return_value={}) as request, \
                 contextlib.redirect_stderr(io.StringIO()):
                result = github.main(["reply", "--repo", "owner/repo", "--pr", "1", "--thread-id", "T1",
                                      "--body-file", str(body), "--expected-head", "abc123", "--execute"])
                self.assertEqual(result, 2)
                request.assert_called_once()


class LarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xym-lark-test-")
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "正文.md"
        self.content = '# 标题\n引号 " 与 $(echo should-not-run)\n第二行\n'
        self.file.write_text(self.content)

    def args(self, action, *extras):
        option = "--markdown-file" if action.startswith("docs-") else "--text-file"
        return lark.parse_args([action, option, str(self.file), *extras])

    def test_doc_update_defaults_to_append_and_stdin(self):
        plan = lark.build_plan(self.args("docs-update", "--doc", "doc-test", "--revision-id", "5"))
        self.assertIn("append", plan["argv"])
        self.assertNotIn("overwrite", plan["argv"])
        self.assertEqual(plan["stdin"], self.content)
        self.assertEqual(plan["argv"][plan["argv"].index("--content") + 1], "-")
        self.assertIn("--revision-id", plan["argv"])

    def test_doc_create_requires_explicit_parent(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.args("docs-create", "--title", "title")
        plan = lark.build_plan(self.args("docs-create", "--title", "title", "--parent-token", "parent"))
        self.assertEqual(plan["argv"][1:3], ["docs", "+create"])
        self.assertNotIn("--wiki-node", plan["argv"])

    def test_block_update_requires_exact_target(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.args("docs-update", "--doc", "doc-test", "--command", "block_replace")

    def test_zero_revision_is_not_false_concurrency_protection(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.args("docs-update", "--doc", "doc-test", "--revision-id", "0")

    def test_empty_content_rejected_before_cli(self):
        self.file.write_text("  \n")
        with patch.object(lark.subprocess, "run") as run, contextlib.redirect_stderr(io.StringIO()):
            result = lark.main(["docs-update", "--doc", "doc-test", "--markdown-file", str(self.file), "--execute"])
            self.assertEqual(result, 2)
            run.assert_not_called()

    def test_okr_creation_uses_current_shortcut_and_safe_json(self):
        plan = lark.build_plan(self.args("okr-create-kr", "--objective-id", "123"))
        self.assertEqual(plan["argv"][1:5], ["okr", "+create", "--level", "key-result"])
        encoded = plan["argv"][plan["argv"].index("--content") + 1]
        self.assertEqual(json.loads(encoded), {"text": self.content})
        self.assertIn("simple", plan["argv"])

    def test_progress_does_not_implicitly_change_indicator(self):
        plan = lark.build_plan(self.args("okr-progress", "--target-id", "123", "--target-type", "key_result"))
        self.assertNotIn("--progress-percent", plan["argv"])
        self.assertNotIn("--progress-status", plan["argv"])

    def test_percentage_and_positive_int64_validation(self):
        for value in ("-10.5", "125", "0", "75.25"):
            self.assertEqual(lark.percent(value), value)
        for value in ("NaN", "Infinity", "1.234", "100000000000"):
            with self.assertRaises(argparse.ArgumentTypeError):
                lark.percent(value)
        for value in ("0", "-1", "ou_abc", str(2**63)):
            with self.assertRaises(argparse.ArgumentTypeError):
                lark.positive_id(value)

    def test_status_requires_explicit_indicator_value(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.args("okr-progress", "--target-id", "123", "--target-type", "key_result", "--status", "done")

    def test_preview_needs_no_cli_or_network(self):
        with patch.object(lark.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as output:
            result = lark.main(["docs-update", "--doc", "doc-test", "--markdown-file", str(self.file)])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "preview")
            run.assert_not_called()

    def test_business_error_partial_success_and_missing_ids_fail(self):
        for response, action in [({"code": 999}, "docs-fetch"),
                                 ({"ok": False}, "docs-fetch"),
                                 ({"data": {"result": "partial_success"}}, "docs-update"),
                                 ({"ok": True, "data": {}}, "okr-create-kr")]:
            with self.subTest(response=response), self.assertRaises(lark.LarkError):
                lark.check_response(response, action)

    def test_success_preserves_warnings(self):
        response = {"ok": True, "data": {"result": "success", "warnings": ["format degraded"]}}
        self.assertEqual(lark.check_response(response, "docs-update"), response)

    def test_timeout_is_not_retried(self):
        with patch.object(lark.subprocess, "run", side_effect=subprocess.TimeoutExpired("lark-cli", 1)) as run, \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            result = lark.main(["docs-update", "--doc", "doc-test", "--markdown-file", str(self.file), "--execute"])
            self.assertEqual(result, 2)
            run.assert_called_once()
            self.assertIn("先回查", errors.getvalue())

    def test_mock_execution_uses_argv_without_shell(self):
        response = subprocess.CompletedProcess([], 0, '{"data":{"key_result_id":"456"}}', "")
        plan = lark.build_plan(self.args("okr-create-kr", "--objective-id", "123"))
        with patch.object(lark.subprocess, "run", return_value=response) as run:
            lark.run_plan(plan, 30)
            self.assertIsInstance(run.call_args.args[0], list)
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertEqual(run.call_args.kwargs["input"], "")


if __name__ == "__main__":
    unittest.main()
