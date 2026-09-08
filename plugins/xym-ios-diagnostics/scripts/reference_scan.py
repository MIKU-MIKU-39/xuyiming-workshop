#!/usr/bin/env python3
"""Xuyiming：源码、头文件和二进制字符串的只读引用证据扫描。"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

TEXT = {".h", ".m", ".mm", ".swift", ".c", ".cpp", ".hpp", ".plist", ".xib", ".storyboard", ".json"}
MAGIC = {b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"!<ar"}


def walk_files(root):
    if root.is_file():
        yield root
        return
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {".git", ".tmp", ".build", "DerivedData"}
                   and not (Path(parent) / d).is_symlink()]
        for name in files:
            yield Path(parent) / name


def scan(roots, symbol, binaries=False, limit=1000, timeout=20):
    if not symbol or "\0" in symbol or "\n" in symbol or limit < 1:
        raise ValueError("symbol 需要单行非空文本，limit 必须为正整数")
    results, limitations, seen = [], [], set()
    checked = {"text": 0, "binary": 0}
    for raw in roots:
        root = Path(raw).resolve(strict=True)
        for path in walk_files(root):
            if path.is_symlink() or path in seen:
                continue
            seen.add(path)
            try:
                kind = "header" if path.suffix in {".h", ".hpp"} else "source"
                if path.suffix in TEXT:
                    if path.stat().st_size > 10 * 1024 * 1024:
                        limitations.append(f"文本过大未读：{path}")
                        continue
                    text = path.read_text(encoding="utf-8")
                    checked["text"] += 1
                else:
                    with path.open("rb") as stream:
                        magic = stream.read(4)
                    if magic not in MAGIC:
                        continue
                    if not binaries:
                        limitations.append(f"未启用二进制扫描：{path}")
                        continue
                    result = subprocess.run(["strings", str(path)], text=True, errors="replace", capture_output=True, timeout=timeout, check=False)
                    if result.returncode:
                        raise ValueError(result.stderr.strip() or "strings 失败")
                    text, kind = result.stdout, "binary-string"
                    checked["binary"] += 1
                for number, line in enumerate(text.splitlines(), 1):
                    if symbol in line:
                        results.append({"file": str(path), "line": number if kind != "binary-string" else None, "kind": kind, "text": line[:1000]})
                        if len(results) >= limit:
                            return {"matches": results, "checked": checked, "complete": False, "limitations": limitations + ["达到结果上限；不能据此判定无引用"]}
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                limitations.append(f"未完成 {path}: {error}")
    return {"matches": results, "checked": checked, "complete": not limitations,
            "limitations": limitations + ["字符串/文本命中不证明调用；未命中也不能排除反射、运行时拼接或外部消费者"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--binaries", action="store_true")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    try:
        result = scan(args.root, args.symbol, args.binaries, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["complete"] else 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
