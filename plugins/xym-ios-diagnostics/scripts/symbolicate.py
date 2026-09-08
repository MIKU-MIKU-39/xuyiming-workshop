#!/usr/bin/env python3
"""Xuyiming：Apple IPS 的本地 dSYM 符号化；匹配不明确时拒绝猜测。"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def number(value):
    result = value if isinstance(value, int) else int(str(value), 0)
    if isinstance(value, bool) or result < 0:
        raise ValueError("地址、偏移必须为非负整数")
    return result


def uuid(value):
    return str(value).lower().replace("-", "")


def read_ips(path):
    text = Path(path).read_text(encoding="utf-8")
    objects, decoder = [], json.JSONDecoder()
    while text.strip():
        obj, end = decoder.raw_decode(text.lstrip())
        objects.append(obj)
        text = text.lstrip()[end:]
    matches = [obj for obj in objects if isinstance(obj, dict) and "usedImages" in obj]
    if len(matches) != 1:
        raise ValueError("需要包含一个 usedImages payload 的 JSON IPS；旧文本 crash 不支持")
    return matches[0]


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "命令执行失败：" + argv[1])
    return result.stdout


def entries(dsym):
    text = run(["xcrun", "dwarfdump", "--uuid", str(Path(dsym).resolve(strict=True))])
    result = []
    for line in text.splitlines():
        match = re.match(r"UUID:\s*([0-9A-Fa-f-]+)\s+\(([^)]+)\)\s+(.+)$", line.strip())
        if match:
            ident, arch, binary = match.groups()
            result.append({"uuid": uuid(ident), "arch": arch, "binary": binary})
    if not result:
        raise ValueError("dSYM 没有可用 UUID")
    return result


def select(payload, symbols, image=None, arch=None):
    candidates = []
    for index, item in enumerate(payload["usedImages"]):
        if image and image not in (item.get("name"), item.get("path"), item.get("uuid")) and uuid(image) != uuid(item.get("uuid")):
            continue
        if arch and item.get("arch") and item["arch"] != arch:
            continue
        for entry in symbols:
            if uuid(item.get("uuid")) == uuid(entry["uuid"]) and entry["arch"] == (arch or item.get("arch")):
                candidates.append((index, item, entry))
    if len(candidates) != 1:
        raise ValueError("必须唯一匹配镜像 UUID 和架构；请确认 dSYM，或指定精确 --image/--arch")
    return candidates[0]


def symbolicate(payload, selected):
    index, item, entry = selected
    base = number(item["base"])
    frames = []
    groups = [("lastExceptionBacktrace", payload.get("lastExceptionBacktrace", []))]
    groups += [(f"thread:{i}", thread.get("frames", [])) for i, thread in enumerate(payload.get("threads", []))]
    for group, values in groups:
        for position, frame in enumerate(values):
            if frame.get("imageIndex") == index:
                frames.append({"group": group, "frame": position, "address": base + number(frame["imageOffset"])})
    addresses = list(dict.fromkeys(frame["address"] for frame in frames))
    mapped = {}
    # 分批避免超长 argv；每批必须一地址一结果，否则不能对齐报告。
    for start in range(0, len(addresses), 200):
        batch = addresses[start:start + 200]
        output = run(["xcrun", "atos", "-o", entry["binary"], "-arch", entry["arch"], "-l", hex(base), *map(hex, batch)]).splitlines()
        if len(output) != len(batch):
            raise ValueError("atos 输出数量与地址不一致，不能可靠映射")
        mapped.update(zip(batch, output))
    for frame in frames:
        value = mapped[frame["address"]].strip()
        frame.update(symbol=value, resolved=bool(value) and not bool(re.fullmatch(r"0x[0-9a-fA-F]+", value)))
        frame["address"] = hex(frame["address"])
    return {"image": item, "dsym": entry, "frames": frames,
            "exception": payload.get("exception"), "exceptionReason": payload.get("exceptionReason"),
            "faultingThread": payload.get("faultingThread"),
            "limitations": ["仅符号化匹配镜像；未解析地址不是源码证据", "符号化不等于根因分析"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ips", required=True, type=Path)
    parser.add_argument("--dsym", required=True, type=Path)
    parser.add_argument("--image")
    parser.add_argument("--arch")
    parser.add_argument("--list-images", action="store_true")
    args = parser.parse_args()
    try:
        payload, symbols = read_ips(args.ips), entries(args.dsym)
        result = {"images": payload["usedImages"], "dsym": symbols} if args.list_images else symbolicate(payload, select(payload, symbols, args.image, args.arch))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
