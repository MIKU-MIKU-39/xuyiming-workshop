# Xym Compoments Publish

由 Xuyiming 维护的本机 CocoaPods 组件发布插件。Codex 和 Claude Code 共用 `skills/xym-compoments-publish/SKILL.md` 及其配套脚本。

## 发布流程

在目标组件的 Git 仓库中明确要求发布时，技能先检查仓库状态，再解析三项发布设置；展示组件版本、分支、提交和命令预览后直接通过 Wukong 发布，无需二次确认。仅检查参数、预览命令或编辑技能时不会触发发布；如果用户要求先确认，则按用户要求执行。

| 设置 | 默认规则 |
| --- | --- |
| 发布信息 | 从最后一个可达的 Wukong 发布节点到当前 `HEAD` 的全部非合并提交中提炼 1–4 个要点，合成不超过 25 个字符的一句中文，可用“，”分隔；找不到发布节点时回退到最近可达 Git tag |
| 是否混淆 | `BTRouter`、`BTAssets`、`BTIMService` 默认不混淆，其余组件默认混淆；接受 `BTAssests` 别名 |
| 发布环境 | 测试环境，传入 `--beta`；正式环境不传此参数 |

没有可用的发布基线或增量内容时，技能会要求明确发布信息。仓库状态变化、脏工作区、缺少 Wukong 等问题需要处理后再发布。具体执行规则以 `SKILL.md` 为准。

## 发布后同步工程（0.2.0）

发布成功后，技能会询问是否把本次实际版本同步到项目：后缀含 VO 对应 Vone，PLA 对应 Poppo，DRL 对应 DoraLive（0.2.2 起支持）；只有单个平台版本只建议同步对应工程。无平台标识时询问 Vone、Poppo、DoraLive 中需要同步哪些工程；版本有歧义时先明确映射，不合成版本号。DoraLive 的实际仓库路径须在同步前确认。

同意同步后，在选定工程的干净 develop 上拉取最新代码（只允许快进），更新 Podfile 的目标组件版本，以发布信息创建本地提交。**本地提交完成后再次询问是否推送**。不自动运行 pod install，不更改 Podfile.lock；工作区不干净、分支有未推送提交/分叉或 Podfile 使用动态版本时停止。

从 0.2.3 起，默认发布信息由技能总结全部增量提交，不再拼接原始标题；1–4 指总结后的要点数，25 字上限包含标点、空格、英文和数字。脚本保留原始提交证据，默认 note 返回 null，需先生成摘要再发布；不会机械截断或虚构改动。用户明确指定的发布信息仍优先，不静默改写。

主工程的完整提交说明直接复用发布时实际传给 `--note` 的摘要，不添加固定标题，也不展开原始提交列表。用户明确提供或历史版本已有的多行日志原样保留；提交后校验内容，发现 hook 改写则停止，不自动修订或推送已有提交。

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
