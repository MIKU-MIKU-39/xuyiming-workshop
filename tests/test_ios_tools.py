"""Xuyiming：跨项目工具的可观察行为测试，无真实远端写入。"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(plugin, script):
    spec = importlib.util.spec_from_file_location(script, ROOT / "plugins" / plugin / "scripts" / (script + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xym-tools-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Xuyiming")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.hooksPath", str(self.repo / "no-hooks"))
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, check=True).stdout


class BuildTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-ios-build", "ios_build")

    def test_bundler_is_project_local(self):
        (self.repo / "Gemfile").write_text("source 'https://rubygems.org'")
        result = self.tool.plan(self.repo, ["pod", "install"])
        self.assertEqual(result["argv"], ["bundle", "exec", "pod", "install"])

    def test_no_mac_fallback_for_test(self):
        with self.assertRaises(ValueError):
            self.tool.plan(self.repo, ["xcodebuild", "test", "-scheme", "My App"])
        result = self.tool.plan(self.repo, ["xcodebuild", "test", "-scheme", "My App"], "platform=iOS Simulator,id=ABC")
        self.assertIn("platform=iOS Simulator,id=ABC", result["argv"])

    def test_existing_destination_preserved(self):
        command = ["xcodebuild", "build", "-destination", "generic/platform=iOS"]
        self.assertEqual(self.tool.plan(self.repo, command)["argv"], command)

    def test_queries_need_no_destination(self):
        self.assertEqual(self.tool.plan(self.repo, ["xcodebuild", "-list", "-json"])["tool"], "xcodebuild")

    def test_exit_code_and_log_preserved(self):
        plan = self.tool.plan(self.repo, ["swift", "test"])
        def fake_run(argv, **kwargs):
            kwargs["stdout"].write("file.swift:4: error: example\n")
            return subprocess.CompletedProcess(argv, 65)
        with patch.object(self.tool.subprocess, "run", side_effect=fake_run):
            result = self.tool.run_plan(plan, self.repo / "logs")
        self.assertEqual(result["exit_code"], 65)
        self.assertIn("example", Path(result["raw_log"]).read_text())
        self.assertTrue(result["summary"]["errors"])


class TermsTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-ios-quality", "term_check")
        self.config = {"rules": [{"word": "pay", "mode": "component"}], "allow": ["repay"]}

    def test_staged_reads_index_not_worktree(self):
        path = self.repo / "中文 name.swift"
        path.write_text("let payAmount = 1\n")
        self.git("add", path.name)
        path.write_text("let amount = 1\n")
        before = self.git("diff", "--cached")
        result = self.tool.scan(self.repo, [], self.config, staged=True)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(before, self.git("diff", "--cached"))
        self.assertEqual(self.tool.scan(self.repo, [path.name], self.config)["findings"], [])

    def test_component_boundaries_and_allow(self):
        (self.repo / "model.swift").write_text("let payload = 1\nlet display = 2\nlet repay = 3\nlet wx_pay = 4\n")
        hits = self.tool.scan(self.repo, ["model.swift"], self.config)["findings"]
        self.assertEqual([h["line"] for h in hits], [4])

    def test_missing_input_and_invalid_rules_fail(self):
        with self.assertRaises((OSError, ValueError)):
            self.tool.scan(self.repo, ["missing.swift"], self.config)
        with self.assertRaises(ValueError):
            self.tool.scan(self.repo, [], {"rules": [{"word": "a", "mode": "regex"}]})

    def test_staged_symlink_is_not_treated_as_source(self):
        (self.repo / "link.swift").symlink_to("outside.swift")
        self.git("add", "link.swift")
        with self.assertRaises(ValueError):
            self.tool.scan(self.repo, [], self.config, staged=True)


class FormatAndDocsTests(RepoCase):
    def test_invalid_doc_baseline_fails(self):
        tool = load("xym-ios-quality", "api_index")
        for previous in ([], {"files": []}, {"files": {"Example.swift": []}}):
            with self.assertRaises(ValueError):
                tool.inventory(self.repo, ["."], previous)

    def test_format_uses_nearest_project_config(self):
        tool = load("xym-ios-quality", "format_code")
        (self.repo / ".clang-format").write_text("BasedOnStyle: LLVM\n")
        source = self.repo / "file.m"
        source.write_text("int main() {return 0;}\n")
        plan = tool.plan_format(self.repo, source)
        self.assertIn(str(self.repo / ".clang-format"), " ".join(plan["argv"]))
        self.assertFalse(plan["write"])

    def test_no_silent_format_defaults(self):
        tool = load("xym-ios-quality", "format_code")
        source = self.repo / "file.swift"
        source.write_text("let value = 1\n")
        with self.assertRaises(ValueError):
            tool.plan_format(self.repo, source)

    def test_docs_add_modify_delete_and_unchanged(self):
        tool = load("xym-ios-quality", "api_index")
        source = self.repo / "Sources"
        source.mkdir()
        file = source / "Example.swift"
        file.write_text("public struct Example {}\n")
        first = tool.inventory(self.repo, ["Sources"])
        self.assertEqual(first["changes"]["added"], ["Sources/Example.swift"])
        same = tool.inventory(self.repo, ["Sources"], first)
        self.assertFalse(any(same["changes"].values()))
        file.write_text("public struct Renamed {}\n")
        changed = tool.inventory(self.repo, ["Sources"], first)
        self.assertEqual(changed["changes"]["modified"], ["Sources/Example.swift"])
        file.unlink()
        deleted = tool.inventory(self.repo, ["Sources"], first)
        self.assertEqual(deleted["changes"]["deleted"], ["Sources/Example.swift"])


class TemporaryTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-tmp-guard", "tmp_guard")
        self.root = self.repo / "xym-tmp"

    def test_preview_has_no_side_effects(self):
        self.tool.create_slot(self.root, "session", "slot")
        self.assertFalse(self.root.exists())

    def test_active_and_keep_block_cleanup(self):
        self.tool.create_slot(self.root, "session", "slot", execute=True)
        with self.assertRaises(ValueError):
            self.tool.clean_slot(self.root, "session", "slot", execute=True)
        self.tool.set_state(self.root, "session", "slot", "complete")
        target = self.root / "session/slot"
        (target / ".keep").touch()
        with self.assertRaises(ValueError):
            self.tool.clean_slot(self.root, "session", "slot", execute=True)
        (target / ".keep").unlink()
        self.tool.clean_slot(self.root, "session", "slot")
        self.assertTrue(target.exists())
        self.tool.clean_slot(self.root, "session", "slot", execute=True)
        self.assertFalse(target.exists())

    def test_invalid_paths_and_unknown_ownership(self):
        for slot in ("../escape", "/", "a/b"):
            with self.assertRaises(ValueError):
                self.tool.create_slot(self.root, "session", slot, execute=True)
        target = self.root / "session/slot"
        target.mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.tool.clean_slot(self.root, "session", "slot", execute=True)

    def test_symlink_slot_is_rejected(self):
        (self.root / "session").mkdir(parents=True)
        (self.root / "session/slot").symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.tool.clean_slot(self.root, "session", "slot", execute=True)


if __name__ == "__main__":
    unittest.main()
