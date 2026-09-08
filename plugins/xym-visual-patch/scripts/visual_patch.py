#!/usr/bin/env python3
"""Xuyiming：仅回环地址的截图标注服务，令牌鉴权，输出固定项目目录。"""
import argparse
import hmac
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
from pathlib import Path
import secrets
import struct
import sys
from urllib.parse import urlsplit
import webbrowser


def image_info(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        mime = "image/png"
    elif data.startswith(b"\xff\xd8"):
        offset, width, height = 2, 0, 0
        # JPEG SOF 包含像素尺寸；忽略 EXIF 等可选段，不解码图像。
        while offset < len(data):
            if data[offset] != 255:
                raise ValueError("无效 JPEG 段")
            while offset < len(data) and data[offset] == 255:
                offset += 1
            marker = data[offset]
            offset += 1
            if marker in (0xD9, 0xDA):
                break
            if marker in (0x01, *range(0xD0, 0xD8)):
                continue
            size = int.from_bytes(data[offset:offset + 2], "big")
            if size < 2 or offset + size > len(data):
                raise ValueError("JPEG 段长度无效")
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
                break
            offset += size
        mime = "image/jpeg"
    else:
        raise ValueError("仅支持 PNG/JPEG；不加载 SVG、远程图片或剪贴板")
    if not (0 < width <= 30000 and 0 < height <= 30000):
        raise ValueError("图片尺寸无效或过大")
    return width, height, mime


def validate_annotations(payload, width, height):
    if not isinstance(payload, dict) or set(payload) != {"annotations"}:
        raise ValueError("请求只能包含 annotations")
    values = payload["annotations"]
    if not isinstance(values, list) or len(values) > 200:
        raise ValueError("标注必须为数组，最多 200 条")
    clean = []
    for item in values:
        if not isinstance(item, dict) or set(item) != {"x", "y", "width", "height", "text"}:
            raise ValueError("标注字段不完整或含未知字段")
        for key in ("x", "y", "width", "height"):
            if isinstance(item[key], bool) or not isinstance(item[key], (float, int)) or not math.isfinite(item[key]):
                raise ValueError("坐标必须是有限数值")
        if item["x"] < 0 or item["y"] < 0 or item["width"] <= 0 or item["height"] <= 0 or item["x"] + item["width"] > width or item["y"] + item["height"] > height:
            raise ValueError("矩形超出图片范围")
        if not isinstance(item["text"], str) or not item["text"].strip() or len(item["text"]) > 4000:
            raise ValueError("说明不能为空且最多 4000 字符")
        clean.append(dict(item))
    return clean


def output_directory(project):
    project = Path(project).resolve(strict=True)
    if not project.is_dir():
        raise ValueError("project 必须是目录")
    target = project / ".visualpatch" / "annotations"
    for part in (target.parent, target):
        if part.is_symlink() or (part.exists() and not part.is_dir()):
            raise ValueError("标注输出路径不能是链接或普通文件")
    return target


def make_server(project, image, port=0):
    target = output_directory(project)
    path = Path(image).resolve(strict=True)
    if path.stat().st_size > 30 * 1024 * 1024:
        raise ValueError("图片超过 30 MiB")
    data = path.read_bytes()
    width, height, mime = image_info(data)
    token = secrets.token_urlsafe(32)
    html = (Path(__file__).resolve().parents[1] / "assets/index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # 不把路径、令牌或用户标注写入 HTTP 访问日志。

        def respond(self, status, content, content_type="application/json"):
            body = content if isinstance(content, bytes) else json.dumps(content, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self, auth=True):
            expected = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected or self.headers.get("Origin", "http://" + expected) != "http://" + expected:
                self.respond(403, {"error": "origin/host rejected"})
                return False
            if auth and not hmac.compare_digest(self.headers.get("Authorization", "").encode("utf-8"), ("Bearer " + token).encode("utf-8")):
                self.respond(401, {"error": "token required"})
                return False
            return True

        def do_GET(self):
            route = urlsplit(self.path).path
            if not self.allowed(auth=route != "/"):
                return
            if route == "/":
                self.respond(200, html, "text/html; charset=utf-8")
            elif route == "/image":
                self.respond(200, data, mime)
            elif route == "/meta":
                self.respond(200, {"width": width, "height": height, "name": path.name})
            else:
                self.respond(404, {"error": "unknown route"})

        def do_POST(self):
            if not self.allowed():
                return
            if self.path != "/annotations":
                self.respond(404, {"error": "unknown route"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if self.headers.get("Transfer-Encoding") or not 0 < size <= 1024 * 1024:
                    raise ValueError("需要不超过 1 MiB 的 Content-Length")
                self.connection.settimeout(5)
                payload = json.loads(self.rfile.read(size))
                values = validate_annotations(payload, width, height)
                fresh = output_directory(project)
                if fresh != target:
                    raise ValueError("输出位置已变化")
                target.mkdir(parents=True, exist_ok=True)
                file = target / (secrets.token_hex(12) + ".json")
                result = {"schema": 1, "image": str(path), "image_sha256": hashlib.sha256(data).hexdigest(),
                          "width": width, "height": height, "annotations": values}
                with file.open("x", encoding="utf-8") as stream:
                    json.dump(result, stream, ensure_ascii=False, indent=2)
                self.respond(200, {"saved": str(file), "count": len(values)})
            except (OSError, ValueError, TypeError) as error:
                self.respond(400, {"error": str(error)})

    class LocalServer(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(5)  # 包括请求头读取，避免单连接永久占住本地服务。
            return connection, address

    server = LocalServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    server.token = token
    server.url = f"http://127.0.0.1:{server.server_port}/#token={token}"
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    try:
        if not args.execute:
            print(json.dumps({"image": str(args.image.resolve(strict=True)), "output": str(output_directory(args.project)), "bind": "127.0.0.1", "executed": False}))
            return 0
        server = make_server(args.project, args.image, args.port)
        print(json.dumps({"url": server.url, "stop": "Ctrl-C", "output": str(output_directory(args.project))}), flush=True)
        if args.open:
            webbrowser.open(server.url)
        try:
            server.serve_forever()
        finally:
            server.server_close()
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, IndexError, struct.error) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
