---
name: ios-build
description: "在 iOS/macOS 项目编译、测试、归档，安装或更新 CocoaPods，执行 SwiftPM，读取 xcresult/覆盖率时使用；精简日志并保留真实退出码。"
---

# iOS 构建与测试

先确认项目根目录、用户要求的动作和项目约束。读取 AGENTS.md、README、Gemfile、Podfile、Package.swift；不替用户升级工具链或依赖。所有脚本路径相对于本插件根目录（本技能目录（包含 SKILL.md）的 ../..）；下例 PLUGIN_ROOT、PROJECT 都必须解析为实际绝对路径。

1. 用脚本预览命令。查询 scheme 可运行：
   `python3 "$PLUGIN_ROOT/scripts/ios_build.py" --repo "$PROJECT" --execute -- xcodebuild -list -json`
2. 多个 workspace/scheme/device 时列出候选并确认；用已选 scheme 的 -showdestinations 验证设备。不得因没有 USB 设备就把 iOS 目标改成 macOS。
3. 执行例子：
   `python3 "$PLUGIN_ROOT/scripts/ios_build.py" --repo "$PROJECT" --destination "platform=iOS Simulator,id=已确认的设备ID" --execute -- xcodebuild test -workspace "App.xcworkspace" -scheme "App"`
   test 时显式传 -resultBundlePath 到新的任务路径，避免覆盖既有 xcresult。workspace/scheme 名称必须来自工程，不能使用示例占位符。
4. SwiftPM 使用 -- swift test 或 -- swift build；CocoaPods 使用 -- pod install 等，根目录有 Gemfile 时脚本自动使用 bundle exec。install/update/lint 会改变项目或访问网络，只在用户请求范围内执行；失败后先分析，不自动删除锁文件。
5. result 和 coverage 子命令各接一个已有 xcresult 目录；输出来自 xcresulttool/xccov，不通过日志中的测试字样猜数量。
6. 回报命令、目的地、退出码、错误摘要和 raw_log 路径。默认仅预览；--execute 才调用工具。超时为 124；空摘要不代表测试通过。必要时定向读取完整日志，不把凭据或全量日志粘贴给用户。

依赖 Python 3.9+；各动作另需本机 Xcode/Swift/CocoaPods。脚本不安装依赖、不变更签名、不自动发版。
