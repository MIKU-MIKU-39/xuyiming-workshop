#!/usr/bin/env python3
"""Xuyiming：组件同步回归，仅使用临时仓库及本地 bare remote。"""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/xym-compoments-publish/skills/xym-compoments-publish/scripts/sync_projects.py"
spec = importlib.util.spec_from_file_location("component_sync", SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class VersionTests(unittest.TestCase):
    def test_platform_suffixes_and_neutral_versions(self):
        result = sync.classify_versions(["104.b1.VO-SC", "105.PLA-CF", "637.VONE", "363", "637.POPPO"])
        self.assertEqual(result["candidates"]["vone"], ["104.b1.VO-SC", "637.VONE"])
        self.assertEqual(result["candidates"]["poppo"], ["105.PLA-CF"])
        self.assertEqual(result["unmapped"], ["363", "637.POPPO"])
        self.assertTrue(result["needs_mapping"])

    def test_single_platform_never_invents_other_platform(self):
        result = sync.classify_versions(["104.b1.VO-SC", "104.b1.VO-SC"])
        self.assertEqual(result["candidates"], {"vone": ["104.b1.VO-SC"], "poppo": []})
        self.assertFalse(result["needs_mapping"])

    def test_conflicting_and_single_neutral_versions_require_mapping(self):
        for versions in (["123.VO-PLA"], ["363"], ["1.VO-C", "2.VO-C"], []):
            self.assertTrue(sync.classify_versions(versions)["needs_mapping"])

    def test_version_input_cannot_contain_commands(self):
        with self.assertRaises(sync.SyncError):
            sync.classify_versions(["1'; system('evil')"])


class PodfileTests(unittest.TestCase):
    def test_preserves_quotes_comments_crlf_and_other_components(self):
        original = (b"# pod 'BTAssets', '0'\r\n"
                    b"target 'App' do\r\n"
                    b"  pod 'BTAssets', '1.VO-C' # assets\r\n"
                    b'  pod("BTAssets/Core", "1.VO-C")\r\n'
                    b"  pod 'BTDebugTool', '10', :configurations => ['Debug']\r\nend\r\n")
        updated, old = sync.rewrite_podfile(original, "BTAssets", "2.VO-C")
        self.assertEqual(old, ["1.VO-C"])
        self.assertEqual(updated, original.replace(b"1.VO-C", b"2.VO-C"))

    def test_configurations_and_unicode_are_preserved(self):
        text = 'pod "BTAssets", "1", :configurations => ["Debug"] # 图片\n'.encode()
        self.assertEqual(sync.rewrite_podfile(text, "BTAssets", "2")[0], text.replace(b'"1"', b'"2"'))

    def test_comments_and_heredoc_text_are_not_calls(self):
        text = b"text = <<~TEXT\npod 'BTAssets', '0'\nTEXT\n# pod 'BTAssets', '0'\npod 'BTAssets', '1'\n"
        updated, _ = sync.rewrite_podfile(text, "BTAssets", "2")
        self.assertEqual(updated.count(b"'0'"), 2)
        self.assertTrue(updated.endswith(b"pod 'BTAssets', '2'\n"))

    def test_unsafe_or_ambiguous_declarations_fail_closed(self):
        cases = [
            "pod 'Other', '1'\n",
            "pod 'BTAssets', version\n",
            "pod 'BTAssets', :path => '../BTAssets'\n",
            "pod 'BTAssets', '1', :git => 'remote'\n",
            "pod 'BTAssets',\n '1'\n",
            "enabled ? pod('BTAssets', '1') : pod('BTAssets', '2')\n",
            "pod 'BTAssets', '1' + suffix\n",
            'pod "BTAssets", "1.#{suffix}"\n',
            "pod 'BTAssets', '1'\npod 'BTAssets/Core', '2'\n",
            "pod 'BTAssets', '1' if enabled\n",
            "pod 'BTAssets', '1'\npod component_name, '2'\n",
            "pod 'BTAssets', '1'\nend\n",
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(sync.SyncError):
                sync.rewrite_podfile(text.encode(), "BTAssets", "3")


class GitSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xym-component-sync-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "app"
        self.repo.mkdir()
        self.remote = self.base / "remote.git"
        self.run_git(self.base, "init", "--bare", str(self.remote))
        self.git("init", "-b", "develop")
        for key, value in (("user.name", "Xuyiming"), ("user.email", "test@example.invalid"),
                           ("core.hooksPath", str(self.base / "disabled-hooks")), ("commit.gpgsign", "false")):
            self.git("config", key, value)
        (self.repo / "Podfile").write_text("pod 'BTAssets', '1'\n")
        self.git("add", "Podfile")
        self.git("commit", "-m", "fixture")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "develop")
        self.head = self.git("rev-parse", "HEAD")

    @staticmethod
    def run_git(path, *args):
        return subprocess.run(["git", "-C", str(path), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def git(self, *args):
        return self.run_git(self.repo, *args)

    def remote_head(self):
        return self.run_git(self.remote, "rev-parse", "refs/heads/develop")

    def execute(self, expected=None):
        return sync.sync_project(self.repo, "BTAssets", "2.VO-C", "修复图片；支持缓存", "origin", expected or self.head)

    def test_plan_is_read_only_even_on_other_branch(self):
        self.git("checkout", "-b", "feature")
        index_before = (self.repo / ".git/index").read_bytes()
        with patch.object(sync, "git", wraps=sync.git) as calls:
            plan = sync.plan_sync(self.repo, "BTAssets", "2.VO-C")
        self.assertEqual(plan["develop_head"], self.head)
        self.assertEqual(plan["old_versions"], ["1"])
        self.assertEqual(self.git("branch", "--show-current"), "feature")
        self.assertEqual(index_before, (self.repo / ".git/index").read_bytes())
        self.assertNotIn("fetch", [arg for call in calls.call_args_list for arg in call.args[1:]])

    def test_sync_commits_only_podfile_and_never_pushes(self):
        self.git("checkout", "-b", "feature")
        result = self.execute()
        self.assertEqual(self.git("branch", "--show-current"), "develop")
        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["base_commit"], self.head)
        self.assertEqual(self.remote_head(), self.head)
        self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"), "Podfile")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "修复图片；支持缓存")
        self.assertEqual(self.git("log", "-1", "--format=%B"), "修复图片；支持缓存")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_multiline_release_note_is_the_complete_commit_message(self):
        # 全局/项目 cleanup 设置不能悄悄丢弃更新日志中的备注行。
        self.git("config", "commit.cleanup", "strip")
        note = '修复图片加载\n\n新增 "勋章" 资源\n# 保留发布备注\n支持缓存；修复回调\n'
        result = sync.sync_project(self.repo, "BTAssets", "2.VO-C", note, "origin", self.head)
        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "修复图片加载")
        self.assertEqual(self.git("log", "-1", "--format=%B"), note.rstrip("\n"))
        self.assertEqual(self.remote_head(), self.head)

    def test_rewritten_commit_message_is_reported_without_amending_or_pushing(self):
        original = sync.git
        def rewrite_commit_message(repo, *args, **kwargs):
            if args and args[0] == "commit":
                # 模拟 hook 改写最终提交说明；仍由真实 Git 创建提交。
                args = (*args[:-1], "hook rewrote the release note")
            return original(repo, *args, **kwargs)
        with patch.object(sync, "git", side_effect=rewrite_commit_message), \
                self.assertRaisesRegex(sync.SyncError, "提交说明.*更新日志"):
            self.execute()
        self.assertEqual(self.git("log", "-1", "--format=%B"), "hook rewrote the release note")
        self.assertEqual(self.git("rev-parse", "HEAD^1"), self.head)
        self.assertEqual(self.remote_head(), self.head)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_fetches_new_remote_commit_before_version_update(self):
        self.git("checkout", "-b", "publisher")
        (self.repo / "remote.txt").write_text("upstream")
        self.git("add", "remote.txt")
        self.git("commit", "-m", "upstream changes")
        upstream = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "HEAD:develop")
        self.git("checkout", "develop")
        result = self.execute()
        self.assertEqual(result["base_commit"], upstream)
        self.assertEqual(self.git("rev-parse", "HEAD^"), upstream)
        self.assertEqual(self.remote_head(), upstream)

    def test_dirty_worktree_stops_without_checkout_or_write(self):
        self.git("checkout", "-b", "feature")
        (self.repo / "user.txt").write_text("keep")
        with self.assertRaises(sync.SyncError):
            self.execute()
        self.assertEqual(self.git("branch", "--show-current"), "feature")
        self.assertEqual((self.repo / "user.txt").read_text(), "keep")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_staged_changes_block(self):
        (self.repo / "Podfile").write_text("pod 'BTAssets', 'user-change'\n")
        self.git("add", "Podfile")
        with self.assertRaises(sync.SyncError):
            self.execute()
        self.assertIn("user-change", self.git("show", ":Podfile"))

    def test_local_ahead_or_diverged_develop_stops(self):
        (self.repo / "local.txt").write_text("unrelated local commit")
        self.git("add", "local.txt")
        self.git("commit", "-m", "local")
        with self.assertRaises(sync.SyncError):
            self.execute(self.git("rev-parse", "HEAD"))
        self.assertEqual(self.remote_head(), self.head)

    def test_changed_approval_snapshot_stops(self):
        with self.assertRaises(sync.SyncError):
            self.execute("0" * 40)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_remote_rewind_stops_even_when_local_develop_was_behind(self):
        self.git("checkout", "-b", "publisher")
        (self.repo / "remote.txt").write_text("upstream")
        self.git("add", "remote.txt")
        self.git("commit", "-m", "remote advance")
        self.git("push", "origin", "HEAD:develop")
        self.git("checkout", "develop")
        # 仅修改临时 bare remote 的 ref，模拟远端在预检后撤回提交。
        self.run_git(self.remote, "update-ref", "refs/heads/develop", self.head)
        with self.assertRaises(sync.SyncError):
            self.execute()
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)
        self.assertEqual((self.repo / "Podfile").read_text(), "pod 'BTAssets', '1'\n")

    def test_diverged_develop_stops_without_merging(self):
        self.git("checkout", "-b", "publisher")
        (self.repo / "remote.txt").write_text("remote")
        self.git("add", "remote.txt")
        self.git("commit", "-m", "remote branch")
        self.git("push", "origin", "HEAD:develop")
        self.git("checkout", "develop")
        (self.repo / "local.txt").write_text("local")
        self.git("add", "local.txt")
        self.git("commit", "-m", "local branch")
        local = self.git("rev-parse", "HEAD")
        with self.assertRaises(sync.SyncError):
            self.execute(local)
        self.assertEqual(self.git("rev-parse", "HEAD"), local)

    def test_fetch_failure_does_not_switch_or_change_podfile(self):
        self.git("checkout", "-b", "feature")
        self.git("remote", "set-url", "origin", str(self.base / "missing.git"))
        with self.assertRaises(sync.SyncError):
            self.execute()
        self.assertEqual(self.git("branch", "--show-current"), "feature")
        self.assertEqual((self.repo / "Podfile").read_text(), "pod 'BTAssets', '1'\n")

    def test_detached_head_and_in_progress_operation_block(self):
        self.git("checkout", "--detach", self.head)
        with self.assertRaises(sync.SyncError):
            self.execute()
        self.git("checkout", "develop")
        (self.repo / ".git/MERGE_HEAD").write_text(self.head + "\n")
        with self.assertRaises(sync.SyncError):
            self.execute()

    def test_missing_note_or_bad_component_never_mutates(self):
        with self.assertRaises(sync.SyncError):
            sync.sync_project(self.repo, "BTAssets", "2", " ", "origin", self.head)
        with self.assertRaises(sync.SyncError):
            sync.plan_sync(self.repo, "BTAssets/../../other", "2")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_noop_produces_no_commit(self):
        result = sync.sync_project(self.repo, "BTAssets", "1", "note", "origin", self.head)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)

    def test_missing_local_develop_can_track_existing_remote(self):
        self.git("checkout", "-b", "feature")
        self.git("branch", "-d", "develop")
        self.assertEqual(self.execute()["status"], "committed")

    def test_symlink_podfile_is_rejected(self):
        actual = self.repo / "ActualPodfile"
        (self.repo / "Podfile").rename(actual)
        (self.repo / "Podfile").symlink_to("ActualPodfile")
        self.git("add", "Podfile", "ActualPodfile")
        self.git("commit", "-m", "symlink")
        self.git("push", "origin", "develop")
        with self.assertRaises(sync.SyncError):
            sync.plan_sync(self.repo, "BTAssets", "2")

    def test_commit_failure_retains_change_and_never_pushes(self):
        original = sync.git
        def fail_commit(repo, *args, **kwargs):
            if args and args[0] == "commit":
                raise sync.SyncError("simulated commit failure")
            return original(repo, *args, **kwargs)
        with patch.object(sync, "git", side_effect=fail_commit), self.assertRaises(sync.SyncError):
            self.execute()
        self.assertIn("2.VO-C", (self.repo / "Podfile").read_text())
        self.assertEqual(self.remote_head(), self.head)


if __name__ == "__main__":
    unittest.main()
