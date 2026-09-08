# Xym Tmp Guard

基于所有权和任务状态的临时目录管理，默认预览，不启用全局清理钩子。

## 技能

- [tmp-guard](skills/tmp-guard/SKILL.md)

## 使用条件

Python 3.9+，脚本先运行 `--help`。iOS 原生工具按动作需要 Xcode；格式化按动作需要 clang-format/SwiftFormat。未安装的依赖只报告，不自动全局安装。执行目录、输入文件和配置使用目标项目真实路径。

默认不修改全局配置、不自动提交/推送/发版、不创建远端资源。各工作流的写入开关、输出位置及验证限制见对应 SKILL.md。

可独立安装；不依赖公司 marketplace 或其他 xym 插件。来源与改编见 [NOTICE.md](NOTICE.md)，版权见 [LICENSE](LICENSE)。
