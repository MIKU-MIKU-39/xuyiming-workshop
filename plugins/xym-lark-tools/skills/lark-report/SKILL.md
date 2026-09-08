---
name: lark-report
description: "用户要求根据工作记录生成、更新或回填飞书周报/OKR 报告时使用；保留原始进度和引用结构，写入前预览并校验目标与文档版本。"
---

# 飞书周报与 OKR 报告

先分清“生成本地草稿”和“更新飞书”。仅读取用户授权的工作记录；确认周次、人员、目标文档。事实进展、风险、下一步、需协作事项分开；缺少下周计划时留待确认，不代用户承诺。

含 OKR 关联块时使用 scripts/lark_api.py docs-fetch --doc 已确认目标 --doc-format xml --execute，保存完整返回的结构、reference_map、block_id 和 revision。普通文档可 Markdown。不要把 XML 简化成纯文本再覆盖，否则可能丢失嵌套 okr-progress、图片、表格或引用。
从本技能目录（包含 SKILL.md）的 ../..得到 PLUGIN_ROOT。更新示例：
`python3 "$PLUGIN_ROOT/scripts/lark_api.py" docs-update --doc "$DOC" --doc-format xml --content-file "$CONTENT" --reference-map-file "$REFERENCES" --command block_replace --block-id "$BLOCK" --revision-id "$REVISION"`
默认仅预览 argv/内容，不写入。映射必须使用读取到的 JSON 对象，不能自行猜 token。优先最小 block_replace；保留未改动子节点原样，无法确定结构时停止并交付草稿。
用户确认目标和具体内容后才加 --execute。版本冲突时重新读远端并合并，不去掉版本保护重试。部分成功/超时可能已写入，先回查，不重复追加。
百分比与指标值使用真实记录；不得自动把超 100 或负增长截断，也不替用户标记 done。报告更新和 OKR 进展写入是两次独立动作，分别授权和核对。CLI 依赖和常规文档行为见插件 references/cli.md。
