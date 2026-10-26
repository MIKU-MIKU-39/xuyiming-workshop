#!/usr/bin/env python3
"""Xuyiming：隔离同步 develop 的组件版本；仅显式 --push 才推送本次提交。"""

import argparse
import difflib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


class SyncError(RuntimeError):
    """需要用户处理的同步阻塞；不自动回滚或重试。"""


def validate_version(version):
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+-]*", version):
        raise SyncError("版本必须是实际发布的完整字面量版本号。")


def classify_versions(versions):
    candidates = {"vone": [], "poppo": [], "doralive": []}
    unmapped, conflicting = [], []
    for version in dict.fromkeys(versions):
        validate_version(version)
        suffix = version.partition(".")[2].upper()
        vone = "VO" in suffix
        poppo = bool(re.search(r"(?:^|[.-])PLA(?:[.-]|$)", suffix))
        # DRL 必须是独立后缀标识，保留完整版本；多平台标识不能静默选一个。
        doralive = bool(re.search(r"(?:^|[.-])DRL(?:[.-]|$)", suffix))
        platforms = [name for name, matched in (("vone", vone), ("poppo", poppo),
                                               ("doralive", doralive)) if matched]
        if len(platforms) > 1:
            conflicting.append(version)
        elif platforms:
            candidates[platforms[0]].append(version)
        else:
            unmapped.append(version)
    return {"candidates": candidates, "unmapped": unmapped, "conflicting": conflicting,
            "needs_mapping": bool(not versions or unmapped or conflicting or
                                  any(len(items) > 1 for items in candidates.values()))}


# Ripper 仅解析 Ruby 语法，不 require/eval Podfile，避免把配置文件当脚本执行。
RUBY_LEX = """require 'ripper'; require 'json'
source = STDIN.read
abort 'Podfile Ruby syntax is invalid' unless Ripper.sexp(source)
puts JSON.generate(Ripper.lex(source))
"""


def lex_podfile(contents):
    try:
        contents.decode("utf-8")
        result = subprocess.run(["ruby", "-e", RUBY_LEX], input=contents, capture_output=True)
    except (OSError, UnicodeError) as exc:
        raise SyncError("需要 Ruby 标准库 Ripper 和 UTF-8 Podfile。") from exc
    if result.returncode:
        raise SyncError("Podfile Ruby 语法无效；未执行 Podfile。")
    return json.loads(result.stdout)


def rewrite_podfile(contents, component, version, declarations=None):
    validate_version(version)
    if not re.fullmatch(r"[A-Za-z0-9_+-]+", component):
        raise SyncError("组件名必须是根 Pod 名称，不接受路径或 shell 文本。")
    tokens = [t for t in lex_podfile(contents) if t[1] not in ("on_sp", "on_ignored_sp")]
    lines = contents.splitlines(keepends=True)
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line)

    def literal(index):
        # 只接受未插值、未转义、未跨行的普通引号字符串。
        parts = tokens[index:index + 3]
        if (len(parts) != 3 or parts[0][1] != "on_tstring_beg" or
                parts[0][2] not in ("'", '"') or parts[1][1] != "on_tstring_content" or
                parts[2][1] != "on_tstring_end" or "\\" in parts[1][2] or
                parts[0][0][0] != parts[2][0][0]):
            raise SyncError("Podfile 含动态或非单行字面量 pod 声明，请先确认如何修改。")
        return parts[1][2], parts[1], parts[2]

    replacements, old_versions = [], set()
    for index, token in enumerate(tokens):
        if token[1:3] != ["on_ident", "pod"]:
            continue
        start = index + 1
        if start < len(tokens) and tokens[start][1] == "on_lparen":
            start += 1
        name, _, _ = literal(start)
        if name != component and not name.startswith(component + "/"):
            continue
        line_number, column = token[0]
        line = lines[line_number - 1]
        if line[:column].strip():
            raise SyncError("目标组件使用条件或嵌套 pod 调用，需人工确认。")
        if start + 3 >= len(tokens) or tokens[start + 3][1] != "on_comma":
            raise SyncError("目标组件缺少固定版本参数。")
        old, value_token, end_token = literal(start + 4)
        validate_version(old)
        if value_token[0][0] != line_number:
            raise SyncError("目标组件版本跨行，需人工确认。")
        end_column = end_token[0][1] + len(end_token[2].encode())
        tail = line[end_column:].decode("utf-8").rstrip("\r\n")
        # 支持常见 Debug 配置；其余 Ruby 选项/条件/源引用不静默改写。
        if not re.fullmatch(r"\s*(?:,\s*:configurations\s*=>\s*\[[^\]\r\n]*\])?\s*\)?\s*(?:#.*)?", tail):
            raise SyncError("目标 pod 的选项或表达式不受自动同步支持，请确认固定版本声明。")
        position = offsets[line_number - 1] + value_token[0][1]
        replacements.append((position, len(old.encode()), version.encode()))
        old_versions.add(old)
        if declarations is not None:
            declarations.append(line)
    if not replacements:
        raise SyncError(f"Podfile 中未找到 {component} 的可同步声明。")
    if len(old_versions) != 1:
        raise SyncError("同组件/子规格存在多个旧版本，需用户确认后再同步。")
    updated = contents
    for position, length, replacement in reversed(replacements):
        updated = updated[:position] + replacement + updated[position + length:]
    lex_podfile(updated)
    return updated, sorted(old_versions)


def git(repo, *args, check=True, raw=False, index=None, input_data=None):
    # 预检不刷新 index，不触发只读命令的可选写锁。
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    result = subprocess.run(["git", "-C", str(repo), *args], input=input_data,
                            capture_output=True, env=env)
    if check and result.returncode:
        raise SyncError(f"git {args[0]} 失败：" + result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout if raw else result.stdout.decode("utf-8").rstrip("\n")


def check_repository(project):
    if os.environ.get("GIT_INDEX_FILE"):
        raise SyncError("检测到外部 GIT_INDEX_FILE；请从普通工程环境执行同步。")
    repo = Path(project).expanduser().resolve()
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo:
        raise SyncError("请传入工程 Git 根目录，不能是其子目录。")
    if not git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False):
        raise SyncError("工程处于 detached HEAD，需先处理。")
    if git(repo, "ls-files", "--unmerged"):
        raise SyncError("工程存在未解决的 index 冲突，请先处理。")
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "BISECT_LOG"):
        location = Path(git(repo, "rev-parse", "--git-path", marker))
        if not location.is_absolute():
            location = repo / location
        if location.exists():
            raise SyncError("工程存在进行中的 Git 操作，请先处理。")
    return repo


def has_local_changes(repo):
    return bool(git(repo, "status", "--porcelain=v1", "--untracked-files=all"))


def check_dirty_baseline(repo, develop, upstream):
    dirty = has_local_changes(repo)
    if dirty and (git(repo, "branch", "--show-current") != "develop" or develop != upstream):
        raise SyncError("已有本地改动时，必须在与远端一致的 develop；不会切分支、快进或搬移用户改动。")
    return dirty


def index_snapshot(repo):
    # 同时核对内容和特殊标志，不把用户的暂存改动或并发 git add 静默覆盖。
    return (git(repo, "ls-files", "--stage", "-z", raw=True),
            git(repo, "ls-files", "-v", "-z", raw=True))


def podfile_snapshot(repo, original, component, version):
    podfile = repo / "Podfile"
    entry = git(repo, "ls-files", "--stage", "--", "Podfile")
    match = re.fullmatch(r"(100644|100755) [0-9a-f]+ 0\tPodfile", entry)
    if (not match or git(repo, "ls-files", "-v", "--", "Podfile") != "H Podfile" or
            podfile.is_symlink() or not podfile.is_file()):
        raise SyncError("Podfile 必须是普通跟踪文件，不能删除、冲突或带特殊 index 标志。")
    staged = git(repo, "show", ":Podfile", raw=True)
    working = podfile.read_bytes()
    baseline_declarations = []
    rewrite_podfile(original, component, version, baseline_declarations)
    updates = []
    for contents in (staged, working):
        declarations = []
        updated, _ = rewrite_podfile(contents, component, version, declarations)
        if declarations != baseline_declarations:
            raise SyncError("目标组件声明已有本地改动；不会覆盖或一并提交，请先处理冲突。")
        updates.append(updated)
    return {"index": index_snapshot(repo), "mode": match[1], "working": working,
            "staged_updated": updates[0], "working_updated": updates[1]}


def verify_release_commit(repo, commit, base, updated, note):
    if (git(repo, "branch", "--show-current") != "develop" or
            git(repo, "rev-parse", "HEAD") != commit or
            git(repo, "rev-list", "--parents", "-n", "1", commit) != f"{commit} {base}" or
            git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", commit) != "Podfile\0" or
            read_podfile(repo, commit) != updated or
            git(repo, "ls-tree", commit, "--", "Podfile").split()[0] !=
            git(repo, "ls-tree", base, "--", "Podfile").split()[0]):
        raise SyncError("提交结果与计划不符（可能受 hook 影响）；禁止推送，请检查本地提交。")
    if git(repo, "log", "-1", "--format=%B", commit) != note.rstrip("\n"):
        raise SyncError("提交说明与组件更新日志不一致（可能被 hook 改写）；保留本地提交，禁止推送。")


def remote_identity(repo, remote):
    fetch_urls = git(repo, "remote", "get-url", "--all", remote).splitlines()
    push_urls = git(repo, "remote", "get-url", "--push", "--all", remote).splitlines()
    if len(fetch_urls) != 1 or fetch_urls != push_urls:
        raise SyncError("远端 fetch/push URL 必须唯一且一致；请先确认推送目标。")
    return fetch_urls[0]


def remote_develop(repo, remote):
    lines = git(repo, "ls-remote", "--heads", remote, "refs/heads/develop").splitlines()
    if len(lines) != 1 or not re.fullmatch(r"[0-9a-f]+\trefs/heads/develop", lines[0]):
        raise SyncError("无法确认远端 develop，停止推送。")
    return lines[0].split("\t")[0]


def branch_state(repo, remote):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote):
        raise SyncError("远端名无效。")
    git(repo, "remote", "get-url", remote)
    remote_ref = f"refs/remotes/{remote}/develop"
    upstream = git(repo, "rev-parse", "--verify", remote_ref, check=False)
    local = git(repo, "rev-parse", "--verify", "refs/heads/develop", check=False)
    if not upstream:
        raise SyncError(f"缺少 {remote}/develop；先确认远端并授权获取该分支，再重新预检。")
    if local and git(repo, "merge-base", local, upstream, check=False) != local:
        raise SyncError("develop 存在未推送提交或已分叉；不会合并、重置或推送已有提交。")
    return local or upstream, upstream, bool(local)


def read_podfile(repo, revision):
    entry = git(repo, "ls-tree", revision, "--", "Podfile")
    if not entry.startswith(("100644 blob ", "100755 blob ")):
        raise SyncError("develop 必须跟踪根目录下的普通 Podfile，不能是符号链接。")
    return git(repo, "show", f"{revision}:Podfile", raw=True)


def plan_sync(project, component, version, remote="origin"):
    repo = check_repository(project)
    develop, upstream, _ = branch_state(repo, remote)
    dirty = check_dirty_baseline(repo, develop, upstream)
    contents = read_podfile(repo, upstream)
    updated, old = rewrite_podfile(contents, component, version)
    if dirty:
        podfile_snapshot(repo, contents, component, version)
    return {"project_path": str(repo), "component": component, "version": version,
            "remote": remote, "branch": "develop", "develop_head": develop,
            "cached_remote_head": upstream, "old_versions": old,
            "changed": contents != updated, "remote_fresh": False, "local_changes": dirty,
            "diff": "".join(difflib.unified_diff(contents.decode().splitlines(True),
                                                 updated.decode().splitlines(True),
                                                 fromfile="a/Podfile", tofile="b/Podfile"))}


def sync_project(project, component, version, note, remote, expected_develop, push=False):
    if not note.strip() or "\0" in note:
        raise SyncError("提交说明需要本次组件的实际更新日志。")
    plan = plan_sync(project, component, version, remote)
    if plan["develop_head"] != expected_develop:
        raise SyncError("develop 与预检快照不一致，请重新预检并确认。")
    repo = Path(plan["project_path"])
    identity = remote_identity(repo, remote) if push else None
    # 显式同步后才获取远端；无强制 refspec，远端改写历史时停止。
    git(repo, "fetch", "--no-tags", remote, f"refs/heads/develop:refs/remotes/{remote}/develop")
    check_repository(repo)
    develop, upstream, exists = branch_state(repo, remote)
    if exists and develop != expected_develop:
        raise SyncError("获取远端期间本地 develop 发生变化，请重新预检。")
    original = read_podfile(repo, upstream)
    updated, old = rewrite_podfile(original, component, version)
    dirty = check_dirty_baseline(repo, develop, upstream)
    if not dirty:
        if exists:
            git(repo, "switch", "develop")
        else:
            git(repo, "switch", "--create", "develop", "--track", f"{remote}/develop")
        git(repo, "merge", "--ff-only", upstream)
    check_repository(repo)
    if git(repo, "rev-parse", "HEAD") != upstream:
        raise SyncError("develop 快进后的 HEAD 不符合远端基线，停止同步。")
    podfile = repo / "Podfile"
    snapshot = podfile_snapshot(repo, original, component, version)
    result = {"project_path": str(repo), "component": component, "version": version,
              "old_versions": old, "remote": remote, "branch": "develop", "base_commit": upstream,
              "status": "unchanged", "commit": None, "pushed": False,
              "local_changes_preserved": dirty}
    if updated == original:
        return result
    # 独立 index 从基线开始，仅包含组件版本更新，正常运行真实工程的 hook/签名。
    with tempfile.TemporaryDirectory(prefix="xym-release-index-") as directory:
        isolated_index = Path(directory) / "index"
        git(repo, "read-tree", upstream, index=isolated_index)
        mode = git(repo, "ls-tree", upstream, "--", "Podfile").split()[0]
        blob = git(repo, "hash-object", "-w", "--stdin", input_data=updated)
        git(repo, "update-index", "--cacheinfo", mode, blob, "Podfile", index=isolated_index)
        expected_tree = git(repo, "write-tree", index=isolated_index)
        if (index_snapshot(repo) != snapshot["index"] or podfile.is_symlink() or
                podfile.read_bytes() != snapshot["working"] or
                git(repo, "rev-parse", "HEAD") != upstream or
                git(repo, "branch", "--show-current") != "develop"):
            raise SyncError("暂存内容、Podfile 或分支在同步期间变化；停止并保留现场。")
        podfile.write_bytes(snapshot["working_updated"])
        git(repo, "commit", "--cleanup=verbatim", "-m", note, index=isolated_index)
    commit = git(repo, "rev-parse", "HEAD")
    # 先验证树，再更新真实 index 的目标版本；不以整个工作文件覆盖已暂存版本。
    if (git(repo, "branch", "--show-current") != "develop" or
            git(repo, "rev-parse", f"{commit}^{{tree}}") != expected_tree or
            git(repo, "rev-list", "--parents", "-n", "1", commit) != f"{commit} {upstream}" or
            git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", commit) != "Podfile\0" or
            read_podfile(repo, commit) != updated or index_snapshot(repo) != snapshot["index"] or
            podfile.is_symlink() or podfile.read_bytes() != snapshot["working_updated"]):
        raise SyncError("提交或本地改动被并发操作/hook 改变；保留现场，禁止推送。")
    staged_blob = git(repo, "hash-object", "-w", "--stdin", input_data=snapshot["staged_updated"])
    git(repo, "update-index", "--cacheinfo", snapshot["mode"], staged_blob, "Podfile")
    verify_release_commit(repo, commit, upstream, updated, note)
    check_repository(repo)
    result.update(status="committed", commit=commit)
    if push:
        if remote_identity(repo, remote) != identity or remote_develop(repo, remote) != upstream:
            raise SyncError("远端身份或 develop 已变化；保留本次本地提交，不推送、不自动合并。")
        verify_release_commit(repo, commit, upstream, updated, note)
        # 精确 SHA 的普通推送，不包含其他分支/本地既有提交，不使用 force。
        try:
            git(repo, "-c", "push.followTags=false", "push", remote, f"{commit}:refs/heads/develop")
        except SyncError as exc:
            # 网络中断可能发生在服务端已接收之后；只查询结果，不再次推送。
            if remote_develop(repo, remote) != commit:
                raise SyncError("推送失败或结果不明；保留本地提交，核实远端后再决定，不自动重试。") from exc
        if remote_develop(repo, remote) != commit:
            raise SyncError("未验证到远端目标提交；请核实远端，不自动重复推送。")
        result["pushed"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    classify = commands.add_parser("classify", help="只读分类本次实际成功发布的版本")
    classify.add_argument("--version", action="append", default=[])
    for name in ("plan", "sync"):
        child = commands.add_parser(name, help="只读预检" if name == "plan" else "隔离同步并提交，仅显式 --push 才推送")
        child.add_argument("--project-path", type=Path, required=True)
        child.add_argument("--component", required=True)
        child.add_argument("--version", required=True)
        child.add_argument("--remote", default="origin")
        if name == "sync":
            child.add_argument("--note", required=True)
            child.add_argument("--expected-develop", required=True, help="plan 返回的 develop_head")
            child.add_argument("--push", action="store_true", help="仅选择“同步提交并推送”时传入")
    args = parser.parse_args()
    try:
        if args.command == "classify":
            result = classify_versions(args.version)
        elif args.command == "plan":
            result = plan_sync(args.project_path, args.component, args.version, args.remote)
        else:
            result = sync_project(args.project_path, args.component, args.version, args.note,
                                  args.remote, args.expected_develop, push=args.push)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SyncError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "pushed": None,
                          "recovery": "检查当前分支、状态和最近提交；保留已有修改，不自动回滚/重试。"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
