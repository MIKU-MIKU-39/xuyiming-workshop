#!/usr/bin/env python3
"""Xuyiming：显式拥有、显式结束的临时任务槽；不安装全局清理钩子。"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

MARKER = ".xym-owner.json"


def target_path(root, session, slot):
    root = Path(root).absolute()
    if ".." in root.parts or root.is_symlink():
        raise ValueError("根目录不能含 .. 或自身是符号链接")
    # macOS 的 /var、/tmp 是系统链接；先固定父级真实位置，再校验任务内部路径。
    root = root.parent.resolve() / root.name
    if root.name != "xym-tmp" or len(root.parts) < 4:
        raise ValueError("根目录必须是明确的专用 xym-tmp 子目录，不能是工作区或系统根目录")
    for name in (session, slot):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name):
            raise ValueError("session/slot 只允许简单名称，不能含路径分隔符")
    target = root / session / slot
    # 检查每个父级，禁止借助链接把清理范围转移到其他位置。
    for path in (target, *target.parents):
        if path.is_symlink():
            raise ValueError("临时目录及父级不能是符号链接")
    return root, target


def owner(root, session, slot):
    root, target = target_path(root, session, slot)
    marker = target / MARKER
    if not target.is_dir() or marker.is_symlink() or not marker.is_file():
        raise ValueError("目标不是本工具拥有的任务槽")
    data = json.loads(marker.read_text(encoding="utf-8"))
    expected = {"schema": 1, "root": str(root), "session": session, "slot": slot}
    if not isinstance(data, dict) or any(data.get(k) != v for k, v in expected.items()):
        raise ValueError("任务槽所有权不匹配")
    if data.get("state") not in ("active", "complete"):
        raise ValueError("任务槽状态无效")
    return target, data


def create_slot(root, session, slot, execute=False):
    root, target = target_path(root, session, slot)
    if target.exists():
        raise ValueError("任务槽已存在；不会接管或覆盖已有目录")
    data = {"schema": 1, "root": str(root), "session": session, "slot": slot, "state": "active"}
    if execute:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()  # 独占创建，重复名称不能接管其他任务。
        with (target / MARKER).open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
    return {"action": "create", "path": str(target), "executed": execute, "owner": data}


def set_state(root, session, slot, state):
    if state not in ("active", "complete"):
        raise ValueError("state 必须为 active 或 complete")
    target, data = owner(root, session, slot)
    data["state"] = state
    (target / MARKER).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"path": str(target), "state": state}


def clean_slot(root, session, slot, execute=False):
    target, data = owner(root, session, slot)
    if data["state"] != "complete":
        raise ValueError("活动任务不能清理；mtime 不能证明任务已结束")
    if (target / ".keep").exists() or (target / ".keep").is_symlink():
        raise ValueError(".keep 保护任务槽，禁止清理")
    if execute:
        # 使用 fd 安全实现，目录内的链接只删除链接本身，不跟随目标。
        if not shutil.rmtree.avoids_symlink_attacks:
            raise ValueError("当前 Python 缺少安全 rmtree 实现，拒绝递归删除")
        owner(root, session, slot)
        shutil.rmtree(target)
    return {"action": "clean", "path": str(target), "executed": execute, "recoverable": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "complete", "active", "clean"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--session", required=True)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action in ("create", "clean"):
            func = create_slot if args.action == "create" else clean_slot
            result = func(args.root, args.session, args.slot, args.execute)
        elif args.execute:
            result = set_state(args.root, args.session, args.slot, args.action)
        else:
            target, data = owner(args.root, args.session, args.slot)
            result = {"path": str(target), "from": data["state"], "to": args.action, "executed": False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
