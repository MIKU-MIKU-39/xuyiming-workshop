# Xym Compoments Publish

由 Xuyiming 维护的本机 CocoaPods 组件发布插件。Codex 和 Claude Code 共用 `skills/xym-compoments-publish/SKILL.md` 及其配套脚本。

## 发布流程

在目标组件的 Git 仓库中使用本技能。先检查仓库状态，再解析三项发布设置；展示组件版本、分支、提交和命令预览，确认后通过 Wukong 发布。

| 设置 | 默认规则 |
| --- | --- |
| 发布信息 | 最后一个可达的 Wukong 发布节点到当前 `HEAD` 的非合并提交；找不到发布节点时回退到最近可达 Git tag |
| 是否混淆 | `BTRouter`、`BTAssets`、`BTIMService` 默认不混淆，其余组件默认混淆；接受 `BTAssests` 别名 |
| 发布环境 | 测试环境，传入 `--beta`；正式环境不传此参数 |

没有可用的发布基线或增量内容时，技能会要求明确发布信息。仓库状态变化、脏工作区、缺少 Wukong 等问题需要处理后再发布。具体执行规则以 `SKILL.md` 为准。

## 入口与资源

- `.codex-plugin/plugin.json`：Codex 插件声明。
- `.claude-plugin/plugin.json`：Claude Code 插件声明。
- `skills/xym-compoments-publish/SKILL.md`：两端共用的技能入口。
- `skills/xym-compoments-publish/scripts/release_context.py`：只读收集组件和发布设置。
- `skills/xym-compoments-publish/agents/openai.yaml`：Codex 技能展示名称、简介和默认提示词。

安装与升级命令见[市场说明](../../README.md)。
