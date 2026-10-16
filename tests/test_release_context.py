"""Xuyiming：发布摘要输入回归；不执行 Wukong 或真实工程写入。"""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/xym-compoments-publish/skills/xym-compoments-publish/scripts/release_context.py"
spec = importlib.util.spec_from_file_location("release_context", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseContextTests(unittest.TestCase):
    def context(self, commits):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Example.podspec").write_text("s.name = 'Example'\ns.version = '1.0'\n")
            def git(_repo, *args, **kwargs):
                return {("rev-parse", "--show-toplevel"): str(root),
                        ("branch", "--show-current"): "main",
                        ("rev-parse", "HEAD"): "current",
                        ("status", "--porcelain"): ""}[args]
            with patch.object(release, "run_git", side_effect=git), \
                 patch.object(release, "find_wukong_release_commit", return_value=("base", "[Update] (1.0)")), \
                 patch.object(release, "collect_increment_commits", return_value=commits), \
                 patch.object(release.shutil, "which", return_value="/bin/wukong"):
                return release.build_context(root)

    def test_full_increment_is_evidence_not_joined_or_truncated_note(self):
        commits = [{"sha": str(i), "subject": "fix: 修复第%d项问题" % i} for i in range(6)]
        result = self.context(commits)
        self.assertEqual(result["increment_commits"], commits)
        self.assertEqual(result["increment_commit_count"], 6)
        self.assertIsNone(result["defaults"]["note"])
        self.assertTrue(result["defaults"]["note_requires_summary"])

    def test_empty_increment_does_not_invent_note(self):
        result = self.context([])
        self.assertIsNone(result["defaults"]["note"])
        self.assertFalse(result["defaults"]["note_requires_summary"])
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
