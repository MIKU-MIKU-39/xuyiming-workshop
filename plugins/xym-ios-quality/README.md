# Xym iOS Quality

项目优先的 iOS 规则、格式化、术语检查、TDD、组件复用与 API 文档。

## 技能

- [ios-guidelines](skills/ios-guidelines/SKILL.md)
- [ios-format](skills/ios-format/SKILL.md)
- [project-terms](skills/project-terms/SKILL.md)
- [ios-tdd](skills/ios-tdd/SKILL.md)
- [component-reuse](skills/component-reuse/SKILL.md)
- [api-docs](skills/api-docs/SKILL.md)

## 使用条件

Python 3.9+，脚本先运行 `--help`。iOS 原生工具按动作需要 Xcode；格式化按动作需要 clang-format/SwiftFormat。未安装的依赖只报告，不自动全局安装。执行目录、输入文件和配置使用目标项目真实路径。

默认不修改全局配置、不自动提交/推送/发版、不创建远端资源。各工作流的写入开关、输出位置及验证限制见对应 SKILL.md。

可独立安装；不依赖公司 marketplace 或其他 xym 插件。来源与改编见 [NOTICE.md](NOTICE.md)，版权见 [LICENSE](LICENSE)。
