#!/usr/bin/env python3
"""Xuyiming：增量公开 API 候选索引；源码证据不等于完整 AST 导出。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

EXCLUDE = {".git", "Pods", "Carthage", "DerivedData", "build", ".build", ".tmp"}
DECL = re.compile(r"^\s*(?:@interface\b|@protocol\b|@property\b|[-+]\s*\(|(?:public|open)\s|(?:FOUNDATION_EXPORT|NS_EXPORT|typedef)\b)")


def inventory(repo, sources, previous=None):
    repo = Path(repo).resolve(strict=True)
    if not sources:
        raise ValueError("需要明确源码根，不能默认扫描所有依赖")
    if previous is not None:
        if not isinstance(previous, dict) or not isinstance(previous.get("files"), dict):
            raise ValueError("previous 必须是包含 files 对象的有效索引")
        if any(not isinstance(item, dict) or not isinstance(item.get("sha256"), str) for item in previous["files"].values()):
            raise ValueError("previous 的文件条目缺少 sha256")
    files = {}
    for source in sources:
        root = (repo / source).resolve(strict=True)
        root.relative_to(repo)
        if not root.is_file() and not root.is_dir():
            raise ValueError("source 必须是普通文件或目录")
        candidates = [root] if root.is_file() else []
        if root.is_dir():
            for current, dirs, names in os.walk(root, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d not in EXCLUDE and not (Path(current) / d).is_symlink())
                candidates.extend(Path(current) / name for name in sorted(names))
        for file in candidates:
            if file.is_symlink() or file.suffix not in (".h", ".m", ".mm", ".swift"):
                continue
            content = file.read_bytes()
            name = file.relative_to(repo).as_posix()
            declarations = [{"line": i, "text": line.strip()} for i, line in enumerate(content.decode("utf-8").splitlines(), 1) if DECL.match(line)]
            files[name] = {"sha256": hashlib.sha256(content).hexdigest(), "candidates": declarations}
    old = (previous or {}).get("files", {})
    changes = {"added": sorted(set(files) - set(old)), "deleted": sorted(set(old) - set(files)),
               "modified": sorted(p for p in files.keys() & old.keys() if files[p]["sha256"] != old[p].get("sha256"))}
    return {"schema": 1, "sources": list(sources), "files": files, "changes": changes,
            "requires_full_review": bool(previous and (previous.get("schema") != 1 or previous.get("sources") != list(sources))),
            "limitations": ["正则仅列候选，可能包含注释/私有声明并漏掉多行声明；必须核实公开头文件、target、访问级别和实现。",
                            "索引不自动更新文档缓存；只有文档生成和核对成功后才采用此快照。"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        prior = json.loads(args.previous.read_text()) if args.previous else None
        print(json.dumps(inventory(args.repo, args.source, prior), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"API index error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
