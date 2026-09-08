---
name: project-terms
description: "需要检查 iOS 源码或 Git 暂存区中的项目禁止术语、标识符命名规则时使用；不内置公司词库，不将匹配结果等同于商店审核结论。"
---

# 项目术语检查

必须取得用户或项目已有规则文件；没有配置时说明未执行，不能偷偷使用公司黑名单。配置 JSON：
```json
{"rules":[{"word":"example","mode":"component"}],"allow":["exampleAllowed"]}
```

word 是示例，不是推荐的禁止词。exact 匹配完整标识符；component 匹配下划线/驼峰拆分后的片段；literal 匹配字面子串。allow 是标识符豁免，literal 不应用它。扫描包含注释和字符串，发现命中仍需人工区分用途。

PLUGIN_ROOT 为本技能目录（包含 SKILL.md）的 ../..：
- 工作区指定文件：python3 "$PLUGIN_ROOT/scripts/term_check.py" --repo "$PROJECT" --config "$RULES" "Sources/File.swift"
- 提交前检查：python3 "$PLUGIN_ROOT/scripts/term_check.py" --repo "$PROJECT" --config "$RULES" --staged

--staged 读取 Git index blob，不读取同名工作区文件；输出实际范围和行号，不暂存或修改内容。退出 1 表示命中，2 表示检查失败；两者都不能当作通过。输出报告要标注 index/worktree，避免把暂存行号当成编辑器当前行号。
只检查 h/m/mm/swift/c/cpp/proto；不扫描产物证明全部消费者安全。自动生成文件应回到 schema/生成器修正，不能只修改下一次生成会覆盖的文件。
