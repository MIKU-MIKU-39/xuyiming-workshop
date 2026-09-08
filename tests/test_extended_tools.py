"""Xuyiming：诊断、飞书 XML、格式化保护和本地标注 HTTP 行为测试。"""
import base64
import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from test_ios_tools import RepoCase, load, ROOT


class DiagnosticTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-ios-diagnostics", "symbolicate")
        self.payload = {"usedImages": [{"name": "App", "uuid": "AA-BB", "arch": "arm64", "base": 4096}],
                        "threads": [{"frames": [{"imageIndex": 0, "imageOffset": 16}]}]}
        self.entries = [{"uuid": "aabb", "arch": "arm64", "binary": "/symbols/App"}]

    def test_ips_header_and_payload(self):
        file = self.repo / "report.ips"
        file.write_text(json.dumps({"app_name": "App"}) + "\n" + json.dumps(self.payload))
        self.assertEqual(self.tool.read_ips(file), self.payload)

    def test_uuid_arch_and_ambiguity(self):
        self.assertEqual(self.tool.select(self.payload, self.entries)[0], 0)
        for entries in ([{"uuid": "ccdd", "arch": "arm64"}], [{"uuid": "aabb", "arch": "x86_64"}], self.entries * 2):
            with self.assertRaises(ValueError):
                self.tool.select(self.payload, entries)
        with self.assertRaises(ValueError):
            self.tool.select(self.payload, self.entries, image="Ap")

    def test_unresolved_addresses_are_not_symbols(self):
        with patch.object(self.tool, "run", return_value="0x1010\n"):
            result = self.tool.symbolicate(self.payload, self.tool.select(self.payload, self.entries))
        self.assertFalse(result["frames"][0]["resolved"])
        self.assertEqual(result["frames"][0]["address"], "0x1010")

    def test_atos_alignment_error(self):
        with patch.object(self.tool, "run", return_value=""):
            with self.assertRaises(ValueError):
                self.tool.symbolicate(self.payload, self.tool.select(self.payload, self.entries))

    def test_source_header_and_binary_limitations(self):
        scanner = load("xym-ios-diagnostics", "reference_scan")
        (self.repo / "API.h").write_text("void Example(void);\n")
        (self.repo / "App").write_bytes(b"\xcf\xfa\xed\xfeExample")
        partial = scanner.scan([self.repo], "Example")
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["matches"][0]["kind"], "header")
        with patch.object(scanner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "Example\n", "")):
            full = scanner.scan([self.repo], "Example", binaries=True)
        self.assertTrue(full["complete"])
        binary = [hit for hit in full["matches"] if hit["kind"] == "binary-string"]
        self.assertIsNone(binary[0]["line"])
        self.assertFalse(scanner.scan([self.repo], "Example", limit=1)["complete"])


class FormatSafetyTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-ios-quality", "format_code")
        (self.repo / ".clang-format").write_text("BasedOnStyle: LLVM\n")
        self.file = self.repo / "Example.m"
        self.file.write_text("void Example() { }\n")

    def test_preview_does_not_write(self):
        before = self.file.read_bytes()
        with patch.object(self.tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"void Example() {}\n", b"")):
            result = self.tool.execute(self.tool.plan_format(self.repo, self.file))
        self.assertTrue(result["changed"])
        self.assertEqual(self.file.read_bytes(), before)

    def test_empty_output_rejected(self):
        with patch.object(self.tool.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"", b"")):
            with self.assertRaises(ValueError):
                self.tool.execute(self.tool.plan_format(self.repo, self.file, write=True))

    def test_concurrent_source_edit_rejected(self):
        def fake(*args, **kwargs):
            self.file.write_text("// changed by user\n")
            return subprocess.CompletedProcess([], 0, b"formatted\n", b"")
        with patch.object(self.tool.subprocess, "run", side_effect=fake):
            with self.assertRaises(ValueError):
                self.tool.execute(self.tool.plan_format(self.repo, self.file, write=True))
        self.assertEqual(self.file.read_text(), "// changed by user\n")

    def test_objc_indentation_and_ranges(self):
        tool = load("xym-ios-quality", "objc_indent")
        source = "void Example() {\nvalue();\n}\n"
        self.assertEqual(tool.Reindenter(2).reindent(source), "void Example() {\n  value();\n}\n")
        self.assertEqual(tool.Reindenter(2).reindent(source, [(3, 3)]), source)

    def test_objc_macro_rejected_without_writing(self):
        before = "#define EXAMPLE \\\n   value\n"
        self.file.write_text(before)
        tool = ROOT / "plugins/xym-ios-quality/scripts/objc_indent.py"
        result = subprocess.run([sys.executable, "-B", str(tool), "--repo", str(self.repo), "--width", "2", "--write", str(self.file)], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.file.read_text(), before)


class ProtoTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-ios-build", "proto_generate")
        (self.repo / "schema").mkdir()
        (self.repo / "schema/example.proto").write_text('syntax = "proto3";\n')
        self.git("add", "schema")
        self.git("commit", "-m", "fixture")

    def test_plan_is_local_and_preview_only(self):
        result = self.tool.plan(self.repo, "schema", ["Generated"], ["protoc", "--version"])
        self.assertEqual(result["argv"], ["protoc", "--version"])
        self.assertFalse((self.repo / "Generated").exists())

    def test_dirty_or_broad_output_rejected(self):
        with self.assertRaises(ValueError):
            self.tool.plan(self.repo, "schema", ["."], ["protoc"])
        (self.repo / "local.txt").write_text("user content")
        with self.assertRaises(ValueError):
            self.tool.plan(self.repo, "schema", ["Generated"], ["protoc"])


class LarkXmlTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-lark-tools", "lark_api")
        self.content = self.repo / "report.xml"
        self.content.write_text('<p>Summary</p><okr-progress id="existing"/>')
        self.refs = self.repo / "refs.json"
        self.refs.write_text(json.dumps({"existing": {"token": "original"}}))

    def args(self):
        return ["docs-update", "--doc", "verified-doc", "--doc-format", "xml", "--content-file", str(self.content),
                "--reference-map-file", str(self.refs), "--command", "block_replace", "--block-id", "block", "--revision-id", "7"]

    def test_xml_and_reference_map_are_separate(self):
        result = self.tool.build_plan(self.tool.parse_args(self.args()))
        self.assertEqual(result["stdin"], self.content.read_text())
        argv = result["argv"]
        self.assertEqual(json.loads(argv[argv.index("--reference-map") + 1]), {"existing": {"token": "original"}})
        self.assertEqual(argv[argv.index("--revision-id") + 1], "7")

    def test_invalid_reference_map_rejected(self):
        self.refs.write_text("[]")
        with self.assertRaises(self.tool.LarkError):
            self.tool.build_plan(self.tool.parse_args(self.args()))

    def test_xml_fetch_preserves_full_format(self):
        result = self.tool.build_plan(self.tool.parse_args(["docs-fetch", "--doc", "verified-doc", "--doc-format", "xml"]))
        self.assertIn("xml", result["argv"])
        self.assertIn("full", result["argv"])
        self.assertFalse(result["writes_remote"])


class VisualTests(RepoCase):
    def setUp(self):
        super().setUp()
        self.tool = load("xym-visual-patch", "visual_patch")
        self.image = self.repo / "image.png"
        self.image.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII="))

    def test_coordinate_validation(self):
        valid = {"x": 0, "y": 0, "width": 1, "height": 1, "text": "change"}
        self.assertEqual(self.tool.validate_annotations({"annotations": [valid]}, 1, 1), [valid])
        for changes in ({"x": -1}, {"width": 2}, {"y": float("nan")}, {"x": True}, {"text": ""}, {"path": "../escape"}):
            with self.assertRaises(ValueError):
                self.tool.validate_annotations({"annotations": [{**valid, **changes}]}, 1, 1)

    def test_output_symlink_rejected(self):
        (self.repo / ".visualpatch").symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.tool.make_server(self.repo, self.image)

    def test_http_auth_origin_fixed_paths_and_save(self):
        server = self.tool.make_server(self.repo, self.image)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, method="GET", body=None, headers=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                connection.request(method, path, body=body, headers=headers or {})
                response = connection.getresponse()
                return response.status, response.read()
            finally:
                connection.close()
        auth = {"Authorization": "Bearer " + server.token}
        self.assertEqual(request("/")[0], 200)
        self.assertEqual(request("/image")[0], 401)
        self.assertEqual(request("/meta", headers={**auth, "Origin": "https://external.invalid"})[0], 403)
        self.assertEqual(request("/../../.git/config", headers=auth)[0], 404)
        self.assertEqual(request("/image", headers=auth)[1], self.image.read_bytes())
        payload = json.dumps({"annotations": [{"x": 0, "y": 0, "width": 1, "height": 1, "text": "hello"}]})
        code, body = request("/annotations", "POST", payload, auth)
        self.assertEqual(code, 200)
        saved = Path(json.loads(body)["saved"])
        self.assertEqual(saved.parent, self.repo.resolve() / ".visualpatch/annotations")
        self.assertEqual(json.loads(saved.read_text())["annotations"][0]["text"], "hello")
        code, body2 = request("/annotations", "POST", payload, auth)
        self.assertNotEqual(saved, Path(json.loads(body2)["saved"]))
        self.assertTrue(saved.exists())
        code, _ = request("/annotations", "POST", '{"annotations":[],"path":"/tmp/escape"}', auth)
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
