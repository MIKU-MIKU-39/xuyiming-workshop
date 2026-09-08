#!/usr/bin/env python3
"""Xuyiming：优先项目格式配置，默认仅输出 diff；--write 才写回指定文件。"""
import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys


def plan_format(repo, file, write=False, config=None, lines=None):
    repo = Path(repo).resolve(strict=True)
    raw_file = Path(file)
    if not raw_file.is_absolute():
        raw_file = repo / raw_file
    if raw_file.is_symlink():
        raise ValueError("不通过符号链接格式化文件")
    file = raw_file.resolve(strict=True)
    file.relative_to(repo)
    if file.suffix not in (".h", ".m", ".mm", ".swift"):
        raise ValueError("仅支持 ObjC/Swift 源码")
    swift = file.suffix == ".swift"
    config_name = ".swiftformat" if swift else ".clang-format"
    if config is None:
        current = file.parent
        while True:
            candidate = current / config_name
            if candidate.is_file():
                config = candidate
                break
            if current == repo:
                raise ValueError(f"项目中没有 {config_name}；请先确定项目风格或显式 --config")
            current = current.parent
    config = Path(config).resolve(strict=True)
    if swift:
        # swiftformat 的 stdin + stdout 模式不触碰原文件，方便比较和并发编辑检测。
        argv = ["swiftformat", "stdin", "--config", str(config), "--stdin-path", str(file), "--cache", "ignore"]
        if lines:
            if len(lines) != 1:
                raise ValueError("Swift 每次仅接受一个区间；多区间由后向前逐次检查")
            argv += ["--line-range", lines[0].replace(":", ",")]
    else:
        argv = ["clang-format", "-style=file:" + str(config), "--assume-filename=" + str(file)]
        for span in lines or []:
            argv.append("-lines=" + span)
    for span in lines or []:
        start, end = map(int, span.split(":"))
        if start < 1 or end < start:
            raise ValueError("行区间应为正数 start:end")
    return {"file": str(file), "repo": str(repo), "argv": argv, "write": write}


def execute(plan):
    file = Path(plan["file"])
    original = file.read_bytes()
    result = subprocess.run(plan["argv"], input=original, capture_output=True, cwd=plan["repo"], timeout=60)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace"))
    if original and not result.stdout:
        raise ValueError("格式化工具返回空内容，拒绝覆盖")
    before = original.decode("utf-8")
    after = result.stdout.decode("utf-8")
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile=plan["file"], tofile=plan["file"]))
    if plan["write"] and diff:
        if file.is_symlink() or file.read_bytes() != original:
            raise ValueError("格式化期间文件发生变化，拒绝覆盖")
        file.write_bytes(result.stdout)
    return {"changed": bool(diff), "written": bool(diff and plan["write"]), "diff": diff}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path)
    parser.add_argument("--lines", action="append")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        result = execute(plan_format(args.repo, args.file, args.write, args.config, args.lines))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result["changed"] and not args.write)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"format error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
