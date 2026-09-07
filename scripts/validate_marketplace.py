#!/usr/bin/env python3
"""Xuyiming：校验个人市场的双端目录、插件元信息与技能资源。"""

import argparse
import json
import re
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_object(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(payload, dict), f"{path}: 必须是 JSON 对象")
    return payload


def plugin_entries(manifest):
    entries = manifest["plugins"]
    require(isinstance(entries, list) and entries, "市场必须包含插件列表")
    names = [entry["name"] for entry in entries]
    require(len(names) == len(set(names)), "市场包含重复插件名称")
    return {entry["name"]: entry for entry in entries}


def validate(root):
    codex = read_object(root / ".agents/plugins/marketplace.json")
    claude = read_object(root / ".claude-plugin/marketplace.json")
    require(codex["name"] == claude["name"], "两端市场名称不一致")
    require(re.fullmatch(r"[A-Za-z0-9_-]+", codex["name"]), "市场名称不合法")
    require(claude["owner"]["name"].strip(), "Claude 市场缺少维护者名称")
    codex_entries = plugin_entries(codex)
    claude_entries = plugin_entries(claude)
    require(codex_entries.keys() == claude_entries.keys(), "两端市场的插件集合不一致")

    for name, entry in codex_entries.items():
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), f"插件名称不合法：{name}")
        expected_source = f"./plugins/{name}"
        require(entry["source"] == {"source": "local", "path": expected_source},
                f"{name}: Codex 插件路径应为 {expected_source}")
        require(claude_entries[name]["source"] == expected_source,
                f"{name}: Claude 插件路径应为 {expected_source}")
        require(entry["policy"]["installation"] in
                {"NOT_AVAILABLE", "AVAILABLE", "INSTALLED_BY_DEFAULT"},
                f"{name}: installation 无效")
        require(entry["policy"]["authentication"] in {"ON_INSTALL", "ON_USE"},
                f"{name}: authentication 无效")
        require(entry["category"].strip(), f"{name}: 缺少 category")

        plugin = root / "plugins" / name
        codex_plugin = read_object(plugin / ".codex-plugin/plugin.json")
        claude_plugin = read_object(plugin / ".claude-plugin/plugin.json")
        # 两端保留各自的声明格式，共用身份、版本和工作流入口。
        for key in ("name", "version", "description", "author", "repository", "keywords", "skills"):
            require(codex_plugin[key] == claude_plugin[key], f"{name}: 两端 {key} 不一致")
        require(codex_plugin["name"] == name, f"{name}: 插件名称与目录不一致")
        require(codex_plugin["skills"] == "./skills/", f"{name}: skills 入口应为 ./skills/")
        require(re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", codex_plugin["version"]),
                f"{name}: 版本格式不合法")

        skills = sorted((plugin / "skills").glob("*/SKILL.md"))
        require(skills, f"{name}: 没有 skills/<skill-name>/SKILL.md")
        for skill in skills:
            text = skill.read_text(encoding="utf-8")
            lines = text.splitlines()
            require(lines and lines[0] == "---", f"{skill}: 缺少 YAML 元信息")
            end = lines.index("---", 1)
            header = lines[1:end]
            # 这里只检查目录契约；完整 YAML/宿主专属字段由宿主校验器检查。
            fields = {line.split(":", 1)[0]: line.split(":", 1)[1].strip().strip("\"'")
                      for line in header if line and not line[0].isspace() and ":" in line}
            require(fields.get("name") == skill.parent.name, f"{skill}: name 与技能目录不一致")
            require(fields.get("description"), f"{skill}: 缺少 description")
            print(f"OK skill: {name}:{skill.parent.name}")

        # 插件安装时会单独打包，因此资源不能依赖仓库外的软链接。
        for resource in plugin.rglob("*"):
            if resource.is_symlink():
                resolved = resource.resolve()
                require(resolved.exists() and plugin.resolve() in resolved.parents,
                        f"{resource}: 链接资源不在插件包内")
        print(f"OK plugin: {name}@{codex_plugin['version']}")

    print(f"Marketplace validation passed: {codex['name']} ({len(codex_entries)} plugins)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        validate(args.root.resolve())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Marketplace validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
