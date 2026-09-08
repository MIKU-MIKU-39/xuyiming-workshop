---
name: symbol-references
description: "需要查询 iOS 符号在源码、头文件、Framework/XCFramework 或静态库中的引用，评估改名/删除影响时使用；只读收集多来源证据。"
---

# 符号引用扫描

取得准确符号及搜索根目录，明确 single/batch/related 范围。以真实根目录为界，不扫描用户整个磁盘。
PLUGIN_ROOT 为本技能目录（包含 SKILL.md）的 ../..：
`python3 "$PLUGIN_ROOT/scripts/reference_scan.py" "ExactSymbol" --root "$PROJECT" --root "$FRAMEWORKS" --binaries`

源码/头文件使用字面包含匹配；.plist/.xib/.storyboard/.json 也检查动态注册。已识别 Mach-O 与 .a 可用 strings 提取；Framework/XCFramework 作为目录递归，不使用固定业务前缀。必要时针对已确认二进制补充 nm 导出符号、Swift demangle 和链接配置证据。

结果中 source/header 的 line 是文件行号；binary-string 没有源码行号。strings 命中可能是日志、元数据或定义，不能直接认定为调用。脚本会列出不可读、未扫二进制、超大文本或截断限制；complete=false 时不能给出“无引用”结论。退出 1 表示不完整，2 表示参数/运行错误。
批量逐符号保留命中、范围和限制。反射、KVC/KVO、NSClassFromString、selector 拼接和仓库外消费者需要额外人工检查；扫描本身不授权删除或改名。
