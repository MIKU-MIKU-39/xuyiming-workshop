#!/usr/bin/env python3
"""Xuyiming：生成可检查的飞书 CLI 请求计划，显式执行后检查业务响应。"""

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


class LarkError(Exception):
    pass


def positive_id(value):
    if not re.fullmatch(r"[1-9][0-9]*", value) or int(value) > 2**63 - 1:
        raise argparse.ArgumentTypeError("ID 必须是正 int64，不能使用名称或用户 open_id")
    return value


def percent(value):
    try:
        number = Decimal(value)
        if not number.is_finite() or abs(number) > Decimal("99999999999"):
            raise ValueError
        if number != number.quantize(Decimal("0.01")):
            raise ValueError
    except (InvalidOperation, ValueError):
        raise argparse.ArgumentTypeError("进度值必须是范围内、最多两位小数的有限数值")
    # 不截断到 0–100：飞书支持超额完成、负增长以及非百分比指标的当前值。
    return format(number, "f")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--execute", action="store_true", help="运行 CLI；默认仅输出本地计划，不需要安装或登录")
    common.add_argument("--timeout", type=int, default=45)
    actions = parser.add_subparsers(dest="action", required=True)

    fetch = actions.add_parser("docs-fetch", parents=[common])
    fetch.add_argument("--doc", required=True, help="已经确认的文档 ID 或 URL")
    fetch.add_argument("--doc-format", choices=("markdown", "xml"), default="markdown")

    create = actions.add_parser("docs-create", parents=[common])
    create.add_argument("--title", required=True)
    create.add_argument("--parent-token", required=True, help="已经确认的文件夹或知识库父节点 token")
    create.add_argument("--markdown-file", "--content-file", dest="content_file", type=Path, required=True)
    create.add_argument("--doc-format", choices=("markdown", "xml"), default="markdown")

    update = actions.add_parser("docs-update", parents=[common])
    update.add_argument("--doc", required=True)
    update.add_argument("--markdown-file", "--content-file", dest="content_file", type=Path, required=True)
    update.add_argument("--doc-format", choices=("markdown", "xml"), default="markdown")
    update.add_argument("--reference-map-file", type=Path, help="XML 中引用对象的原始 JSON 映射；与内容分别传递")
    update.add_argument("--command", choices=("append", "overwrite", "block_replace", "block_insert_after"), default="append")
    update.add_argument("--block-id")
    update.add_argument("--revision-id", type=int, help="使用读取到的文档版本做写入前置条件")

    kr = actions.add_parser("okr-create-kr", parents=[common])
    kr.add_argument("--objective-id", required=True, type=positive_id)
    kr.add_argument("--text-file", required=True, type=Path)

    progress = actions.add_parser("okr-progress", parents=[common])
    progress.add_argument("--target-id", required=True, type=positive_id)
    progress.add_argument("--target-type", choices=("objective", "key_result"), required=True)
    progress.add_argument("--text-file", required=True, type=Path)
    progress.add_argument("--percent", type=percent)
    progress.add_argument("--status", choices=("normal", "overdue", "done"))
    args = parser.parse_args(argv)
    if args.timeout < 1:
        parser.error("--timeout 必须为正整数")
    if args.action == "okr-progress" and args.status and args.percent is None:
        parser.error("--status 需要 --percent，否则飞书不会应用该状态")
    if args.action == "docs-update":
        needs_block = args.command.startswith("block_")
        if needs_block != bool(args.block_id):
            parser.error("block_* 操作必须提供 --block-id；append/overwrite 不接受 --block-id")
        if args.revision_id is not None and args.revision_id <= 0:
            # 当前 CLI 对 0 不发送 revision_id，不能声称提供了版本保护。
            parser.error("显式 --revision-id 必须为正整数；0 不会被当前 CLI 发送")
    for field in ("doc", "title", "parent_token", "block_id"):
        value = getattr(args, field, None)
        if value is not None and (not value.strip() or value.startswith("-") or "\0" in value):
            parser.error(f"--{field.replace('_', '-')} 不能为空或以 - 开头")
    return args


def build_plan(args):
    content_path = getattr(args, "content_file", None) or getattr(args, "text_file", None)
    content = content_path.read_text(encoding="utf-8") if content_path else None
    if content is not None and (not content.strip() or "\0" in content):
        raise LarkError("内容必须是非空 UTF-8 文本且不包含 NUL")
    command = ["lark-cli"]
    stdin = None
    if args.action == "docs-fetch":
        command += ["docs", "+fetch", "--doc", args.doc, "--doc-format", args.doc_format, "--detail", "full"]
    elif args.action == "docs-create":
        command += ["docs", "+create", "--title", args.title, "--parent-token", args.parent_token,
                    "--doc-format", args.doc_format, "--content", "-"]
        stdin = content
    elif args.action == "docs-update":
        command += ["docs", "+update", "--doc", args.doc, "--command", args.command,
                    "--doc-format", args.doc_format, "--content", "-"]
        stdin = content
        if args.block_id:
            command += ["--block-id", args.block_id]
        if args.revision_id is not None:
            command += ["--revision-id", str(args.revision_id)]
        if args.reference_map_file:
            if args.doc_format != "xml":
                raise LarkError("reference-map 仅用于 XML 更新")
            references = json.loads(args.reference_map_file.read_text(encoding="utf-8"))
            if not isinstance(references, dict):
                raise LarkError("reference-map 必须是 JSON 对象")
            # stdin 已承载文档；映射作为一个 argv 值，避免两个输入争用 stdin。
            command += ["--reference-map", json.dumps(references, ensure_ascii=False)]
    else:
        # 当前官方 shortcut 使用 simple JSON；不沿用旧版的 raw create 接口。
        payload = json.dumps({"text": content}, ensure_ascii=False)
        if args.action == "okr-create-kr":
            command += ["okr", "+create", "--level", "key-result", "--objective-id", args.objective_id]
        else:
            command += ["okr", "+progress-create", "--target-id", args.target_id, "--target-type", args.target_type]
            if args.percent is not None:
                command += ["--progress-percent", args.percent]
            if args.status:
                command += ["--progress-status", args.status]
        command += ["--style", "simple", "--content", payload]
    command += ["--as", "user", "--format", "json"]
    return {
        "action": args.action, "writes_remote": args.action != "docs-fetch",
        "argv": command, "stdin": stdin,
        "content_sha256": hashlib.sha256(content.encode()).hexdigest() if content is not None else None,
    }


def check_response(payload, action):
    if not isinstance(payload, dict):
        raise LarkError("CLI 返回的 JSON 不是对象，无法确认结果")
    if payload.get("ok") is False or payload.get("code", 0) not in (0, "0") or payload.get("error"):
        raise LarkError("CLI 返回业务错误：" + json.dumps(payload, ensure_ascii=False))
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise LarkError("CLI 返回 data 格式异常，无法确认结果")
    if data.get("result") not in (None, "success"):
        # partial_success 可能已经写入部分内容，不能自动重试追加或创建。
        raise LarkError("操作并非完整成功，请先回查远端：" + json.dumps(payload, ensure_ascii=False))
    if action == "docs-create" and not (data.get("document") or {}).get("document_id"):
        raise LarkError("缺少新文档 ID，不能确认创建结果")
    if action == "docs-update" and data.get("result") != "success":
        raise LarkError("缺少文档更新成功标记，请回查远端")
    if action == "okr-create-kr" and not data.get("key_result_id"):
        raise LarkError("缺少新 KR ID，不能确认创建结果")
    if action == "okr-progress" and not (data.get("progress") or {}).get("progress_id"):
        raise LarkError("缺少新进展 ID，不能确认创建结果")
    return payload  # 保留 warnings、文档引用映射和返回 ID，供技能回查而非静默丢弃。


def run_plan(plan, timeout):
    result = subprocess.run(plan["argv"], input=plan["stdin"] or "", text=True,
                            capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise LarkError(result.stderr.strip() or result.stdout.strip() or "lark-cli 执行失败")
    return check_response(json.loads(result.stdout), plan["action"])


def main(argv=None):
    args = parse_args(argv)
    attempted_write = False
    try:
        plan = build_plan(args)
        if args.execute:
            attempted_write = plan["writes_remote"]
            result = run_plan(plan, args.timeout)
            output = {"status": "executed", "action": args.action, "result": result}
        else:
            output = {"status": "preview", "plan": plan}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, AttributeError, LarkError, subprocess.TimeoutExpired) as error:
        print(f"Lark API error: {error}", file=sys.stderr)
        if attempted_write:
            print("写入可能已发生。先回查目标，勿自动重试，勿因失败改为新建。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
