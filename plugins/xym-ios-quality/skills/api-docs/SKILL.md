---
name: api-docs
description: "需要为 CocoaPods/SwiftPM/iOS 组件生成或更新本地 API 文档，或批量按源码变更检查文档时使用；先建立可核验索引，不依赖公司文档服务。"
---

# 组件 API 文档

确认组件目录、公开源文件集合、语言和本地输出路径。先读取 podspec 的 public_header_files/source_files 或 Package.swift 的 target 产品设置，不把整个仓库每个符号都视为公开 API。

从本技能目录（包含 SKILL.md）的 ../..得到 PLUGIN_ROOT，运行 scripts/api_index.py --repo "$PROJECT" --source "Sources"；多个 --source 可重复。可用 --previous 已审查的索引JSON 对比 added/modified/deleted。脚本只输出结果，不自动覆盖缓存或写文档。schema/来源变化的 requires_full_review 必须触发全量复查；哈希不变也不能掩盖文档模板或导出配置变化。

逐个阅读 candidates 对应源码与实际调用，生成：职责、安装/导入、公开类型和方法、线程/生命周期、错误、可运行示例、限制和来源。正则候选不是 AST，尤其多行签名、扩展、宏和 ObjC 实现中的声明可能误收或漏收；必须人工核实。不要输出未验证 API 或泄露私有密钥。

本地文档经核验后才更新索引基线；发生解析失败、源缺失或删除时不得把旧缓存当成功。批量操作逐组件报告成功/失败，默认不切分支、不 pull、不暂存。
上传是独立授权动作：先确认目标文档/知识库与内容，可选使用 xym-lark-tools 的预览和版本保护；未安装或无权限时交付本地文档，不替换成未知远端目标。
