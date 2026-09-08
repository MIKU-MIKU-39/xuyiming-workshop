#!/usr/bin/env python3
"""Xuyiming：按项目词表检查源码；staged 模式严格读取索引而非工作区。"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

EXTENSIONS = {".h", ".m", ".mm", ".swift", ".c", ".cpp", ".proto"}
TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
PART = re.compile(r"[A-Z]+(?=[A-Z][a-z]|[0-9_]|$)|[A-Z]?[a-z]+|[0-9]+")


def git(repo, *args):
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args],
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace"))
    return result.stdout


def validate_config(config):
    if not isinstance(config, dict) or not isinstance(config.get("rules"), list) or not config["rules"]:
        raise ValueError("配置需要非空 rules 数组，不内置公司词表")
    allow = config.get("allow", [])
    if not isinstance(allow, list) or any(not isinstance(x, str) for x in allow):
        raise ValueError("allow 必须为字符串数组")
    for rule in config["rules"]:
        if not isinstance(rule, dict) or not isinstance(rule.get("word"), str) or not rule["word"].strip():
            raise ValueError("每条规则需要非空 word")
        if rule.get("mode", "exact") not in ("exact", "component", "literal"):
            raise ValueError("mode 仅支持 exact / component / literal")


def scan(repo, paths, config, staged=False):
    validate_config(config)
    repo = Path(repo).resolve(strict=True)
    before = None
    index_modes = {}
    if staged:
        if paths:
            raise ValueError("staged 与指定文件不能混用")
        before = git(repo, "ls-files", "--stage", "-z")
        for record in before.split(b"\0"):
            if record:
                metadata, filename = record.split(b"\t", 1)
                index_modes[os.fsdecode(filename)] = metadata.split()[0]
        if git(repo, "ls-files", "--unmerged", "-z"):
            raise ValueError("索引存在冲突")
        paths = [os.fsdecode(p) for p in git(repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR").split(b"\0") if p]
    elif not paths:
        raise ValueError("需要指定文件或 --staged")
    allow = {word.casefold() for word in config.get("allow", [])}
    findings, checked = [], []
    for path in paths:
        relative = Path(path)
        if relative.is_absolute():
            relative = relative.relative_to(repo)
        if ".." in relative.parts:
            raise ValueError("文件必须在项目内")
        if relative.suffix not in EXTENSIONS:
            continue
        name = relative.as_posix()
        if staged:
            if index_modes.get(name) not in (b"100644", b"100755"):
                raise ValueError(f"暂存文件不是普通源码 blob：{name}")
            text = git(repo, "show", ":" + name).decode("utf-8", errors="strict")
        else:
            resolved = (repo / relative).resolve(strict=True)
            resolved.relative_to(repo)
            text = resolved.read_text(encoding="utf-8")
        checked.append(name)
        for number, line in enumerate(text.splitlines(), 1):
            for rule in config["rules"]:
                word, mode = rule["word"], rule.get("mode", "exact")
                matches = []
                if mode == "literal":
                    if word.casefold() in line.casefold():
                        matches = [word]
                else:
                    for token in TOKEN.findall(line):
                        if token.casefold() in allow:
                            continue
                        candidates = [token] if mode == "exact" else PART.findall(token)
                        if word.casefold() in {part.casefold() for part in candidates}:
                            matches.append(token)
                for match in dict.fromkeys(matches):
                    findings.append({"file": name, "line": number, "word": word, "match": match, "mode": mode})
    if staged and before != git(repo, "ls-files", "--stage", "-z"):
        raise ValueError("检查期间索引已变化，请重新检查")
    return {"scope": "index" if staged else "worktree", "checked": checked, "findings": findings,
            "limitations": ["词表命中仅代表项目规则；包含注释和字符串，不是编译器或商店审核判定。"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    try:
        result = scan(args.repo, args.paths, json.loads(args.config.read_text()), args.staged)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(bool(result["findings"]))
    except (OSError, ValueError, TypeError) as error:
        print(f"term check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
