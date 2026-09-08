#!/usr/bin/env python3
"""Xuyiming：检查显式 proto 输入和输出范围，再调用项目自己的生成器。"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def git(repo, *args):
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return result.stdout.strip()


def plan(repo, source, outputs, command):
    repo = Path(repo).resolve(strict=True)
    source = (repo / source).resolve(strict=True)
    source.relative_to(repo)
    if not source.is_dir() or not command or not outputs:
        raise ValueError("必须提供 proto 目录、输出范围和生成器 argv")
    resolved = []
    for raw in outputs:
        path = (repo / raw).resolve()
        relative = path.relative_to(repo)
        if not relative.parts or relative.parts[0] == ".git":
            raise ValueError("输出不能是整个仓库或 Git 元数据")
        resolved.append(str(relative))
    head = git(repo, "rev-parse", "HEAD")
    # 生成器可能清空输出目录，因此有本地变更时不代替用户决定覆盖范围。
    dirty = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise ValueError("仓库有本地变更；先由用户处理，工具不会 stash/reset")
    source_commit = git(source, "rev-parse", "HEAD")
    if git(source, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("proto 输入仓库有本地变更")
    return {"repo": str(repo), "source": str(source), "source_commit": source_commit,
            "head": head, "outputs": resolved, "argv": command,
            "warning": "输出范围是审核契约，不是操作系统沙箱；仅执行已检查、可信的项目生成器。不会 fetch/pull/checkout。"}


def execute(resolved, timeout=300):
    fresh = plan(resolved["repo"], resolved["source"], resolved["outputs"], resolved["argv"])
    if fresh != resolved:
        raise ValueError("生成前输入发生变化，请重新预览")
    result = subprocess.run(resolved["argv"], cwd=resolved["repo"], timeout=timeout, check=False)
    return {"exit_code": result.returncode, "changes": git(resolved["repo"], "status", "--porcelain=v1", "--untracked-files=all"),
            "next": "核对变更是否全部位于约定 outputs；越界不自动回滚。执行项目检查后再请求提交。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", action="append", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        resolved = plan(args.repo, args.source, args.output, command)
        result = execute(resolved, args.timeout) if args.execute else resolved
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result.get("exit_code", 0)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
