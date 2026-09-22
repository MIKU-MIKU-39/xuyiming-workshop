# Xym Compoments Publish

由 Xuyiming 维护的本机 CocoaPods 组件发布插件。Codex 和 Claude Code 共用 `skills/xym-compoments-publish/SKILL.md` 及其配套脚本。

## 发布流程

在目标组件的 Git 仓库中明确要求发布时，技能先检查仓库状态，再解析三项发布设置；展示组件版本、分支、提交和命令预览后直接通过 Wukong 发布，无需二次确认。仅检查参数、预览命令或编辑技能时不会触发发布；如果用户要求先确认，则按用户要求执行。

| 设置 | 默认规则 |
| --- | --- |
| 发布信息 | 最后一个可达的 Wukong 发布节点到当前 `HEAD` 的非合并提交；找不到发布节点时回退到最近可达 Git tag |
| 是否混淆 | `BTRouter`、`BTAssets`、`BTIMService` 默认不混淆，其余组件默认混淆；接受 `BTAssests` 别名 |
| 发布环境 | 测试环境，传入 `--beta`；正式环境不传此参数 |

没有可用的发布基线或增量内容时，技能会要求明确发布信息。仓库状态变化、脏工作区、缺少 Wukong 等问题需要处理后再发布。具体执行规则以 `SKILL.md` 为准。

## 发布后同步工程（0.2.0）

发布成功后，技能会询问是否把本次实际版本同步到项目：后缀含 VO 对应 Vone，PLA 对应 Poppo；只有单个平台版本只建议同步对应工程。无平台标识时询问 Vone、Poppo 或两个工程；版本有歧义时先明确映射，不合成版本号。

同意同步后，在选定工程的干净 develop 上拉取最新代码（只允许快进），更新 Podfile 的目标组件版本，以发布信息创建本地提交。**本地提交完成后再次询问是否推送**。不自动运行 pod install，不更改 Podfile.lock；工作区不干净、分支有未推送提交/分叉或 Podfile 使用动态版本时停止。

默认本机路径是 `/Users/vshow/Desktop/Work/vone` 和 `/Users/vshow/Desktop/Work/poppo`，用户可明确覆盖。同步辅助脚本需要 Python 3.9+、Git 和 Ruby；Ripper 仅做静态语法检查，不执行 Podfile。

## 入口与资源

- `.codex-plugin/plugin.json`：Codex 插件声明。
- `.claude-plugin/plugin.json`：Claude Code 插件声明。
- `skills/xym-compoments-publish/SKILL.md`：两端共用的技能入口。
- `skills/xym-compoments-publish/scripts/release_context.py`：只读收集组件和发布设置。
- `skills/xym-compoments-publish/scripts/sync_projects.py`：只读版本分类/预检，以及显式授权后的工程同步与本地提交；没有自动推送入口。
- `skills/xym-compoments-publish/references/project-sync.md`：版本映射、工程同步及独立推送审批的完整流程。
- `skills/xym-compoments-publish/agents/openai.yaml`：Codex 技能展示名称、简介和默认提示词。

安装与升级命令见[市场说明](../../README.md)。
