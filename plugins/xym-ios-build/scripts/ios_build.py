#!/usr/bin/env python3
"""Xuyiming：可预览的 Apple/Swift/CocoaPods 命令包装，保存日志和原始退出状态。"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def plan(repo, command, destination=None):
    repo = Path(repo).resolve(strict=True)
    if not repo.is_dir() or not command:
        raise ValueError("需要有效项目目录和命令")
    tool, *args = command
    if tool not in ("xcodebuild", "swift", "pod", "result", "coverage"):
        raise ValueError("仅支持 xcodebuild / swift / pod / result / coverage")
    argv = list(command)
    if tool in ("result", "coverage"):
        if len(args) != 1 or not (repo / args[0]).resolve().is_dir():
            raise ValueError("result/coverage 需要一个现有 xcresult 路径")
        bundle = str((repo / args[0]).resolve())
        argv = (["xcrun", "xcresulttool", "get", "test-results", "summary", "--path", bundle]
                if tool == "result" else ["xcrun", "xccov", "view", "--report", "--json", bundle])
    elif tool == "pod" and (repo / "Gemfile").is_file():
        argv = ["bundle", "exec", *command]
    if tool == "xcodebuild":
        has_dest = any(a == "-destination" or a.startswith("-destination=") for a in args)
        actions = {"build", "test", "archive", "analyze", "install", "build-for-testing", "test-without-building"}
        query = any(a in args for a in ("-list", "-showdestinations", "-showBuildSettings", "-version", "-showsdks"))
        if destination and not has_dest:
            argv += ["-destination", destination]
            has_dest = True
        # 不猜 Mac，也不让连接的设备覆盖用户的 simulator/archive 目标。
        if not query and (actions.intersection(args) or not any(a == "clean" for a in args)) and not has_dest:
            raise ValueError("构建类操作需要明确 -destination；先查询该 scheme 的 -showdestinations")
    elif destination:
        raise ValueError("--destination 仅适用于 xcodebuild")
    return {"repo": str(repo), "tool": tool, "argv": argv}


def summarize(text, tool):
    if tool in ("result", "coverage"):
        payload = json.loads(text)
        if tool == "result":
            if not isinstance(payload, dict):
                raise ValueError("xcresult 摘要格式不支持，请读取原始日志")
            keys = ("title", "result", "totalTestCount", "passedTests", "failedTests", "skippedTests",
                    "testFailures", "finishTime", "startTime")
            return {key: payload[key] for key in keys if key in payload}
        return {"lineCoverage": payload.get("lineCoverage"), "coveredLines": payload.get("coveredLines"),
                "executableLines": payload.get("executableLines"),
                "targets": [{k: t.get(k) for k in ("name", "lineCoverage", "coveredLines", "executableLines")}
                            for t in payload.get("targets", [])]}
    buckets = {"errors": [], "warnings": [], "changes": [], "results": []}
    seen = set()
    counts = {k: 0 for k in buckets}
    for line in text.splitlines():
        if re.search(r"error:|fatal error|Undefined symbols|FAILED|\[!\]|^\s*ERROR", line, re.I):
            key = "errors"
        elif re.search(r"warning:|^\s*WARN", line, re.I):
            key = "warnings"
        elif re.match(r"\s*(Installing|Updating|Removing)\s", line):
            key = "changes"
        elif re.search(r"SUCCEEDED|Test Suite|executed|tests? passed|Pod installation complete", line, re.I):
            key = "results"
        else:
            continue
        counts[key] += 1
        if (key, line) not in seen and len(buckets[key]) < 40:
            buckets[key].append(line)
            seen.add((key, line))
    return dict(buckets, counts=counts, tail=text.splitlines()[-12:])


def run_plan(resolved, log_dir, timeout=1200):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    # 每次运行独立目录，失败/并行不会覆盖旧证据。
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=log_dir))
    raw = run_dir / "output.log"
    with raw.open("w", encoding="utf-8") as stream:
        try:
            result = subprocess.run(resolved["argv"], cwd=resolved["repo"], stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            stream.write("\nerror: command timeout; inspect outputs before retrying\n")
            code = 124
    text = raw.read_text(encoding="utf-8", errors="replace")
    try:
        summary = summarize(text, resolved["tool"])
    except (ValueError, TypeError, AttributeError) as error:
        summary = {"parse_error": str(error), "tail": text.splitlines()[-12:]}
        code = code or 2
    return {"exit_code": code, "raw_log": str(raw.resolve()), "summary": summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--destination")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if args.timeout <= 0:
            raise ValueError("timeout 必须为正数")
        resolved = plan(args.repo, command, args.destination)
        output = run_plan(resolved, args.log_dir or args.repo / ".tmp/xym-ios-build", args.timeout) if args.execute else {"status": "preview", "plan": resolved}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return output.get("exit_code", 0)
    except (OSError, ValueError) as error:
        print(f"build error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
