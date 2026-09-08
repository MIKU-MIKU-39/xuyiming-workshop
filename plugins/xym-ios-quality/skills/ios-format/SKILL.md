---
name: ios-format
description: "需要格式化 Objective-C/Swift、按修改行缩进或检查格式差异时使用；优先目标项目配置，默认输出差异，写回必须明确授权。"
---

# iOS 格式化

确认文件范围并读取最近的 .clang-format / .swiftformat。脚本不会提供公司默认风格；缺配置时让用户指定配置或只报告问题。PLUGIN_ROOT 为本技能目录（包含 SKILL.md）的 ../..。

`python3 "$PLUGIN_ROOT/scripts/format_code.py" --repo "$PROJECT" --lines 10:25 "Sources/Example.swift"`

默认实际运行 formatter 产生 diff，但不修改源文件；差异退出 1、无差异 0、错误 2。--write 才写回。配置路径可显式 --config；Swift 一次一个行区间，多个区间按从后向前执行，每次重新读取行号，避免漂移。不因 formatter 缺失而自动全局安装或改用另一套风格。

对只需 ObjC 冒号对齐且项目明确接受词法缩进器的情况，可使用 scripts/objc_indent.py --repo ... --width 项目宽度 --lines 起:止 文件。只支持 .h/.m，默认 diff，--write 写回；不宣称与 Xcode 等价。宏续行/跨行或原始字符串拒绝处理，ObjC++ 使用项目 clang-format。

写回后核对 diff 的实际范围；格式化工具可能扩展到相邻语法结构。保留用户本地改动；文件已变化就重新预览，不能覆盖。敏感源代码不上传第三方格式化服务。
