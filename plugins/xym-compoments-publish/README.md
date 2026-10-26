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

## 发布后同步工程（0.2.4）

发布成功后，技能会询问是否把本次实际版本同步到项目：后缀含 VO 对应 Vone，PLA 对应 Poppo，DRL 对应 DoraLive（0.2.2 起支持）；只有单个平台版本只建议同步对应工程。无平台标识时询问 Vone、Poppo、DoraLive 中需要同步哪些工程；版本有歧义时先明确映射，不合成版本号。DoraLive 的实际仓库路径须在同步前确认。

上传成功后弹出选择框，未回答不执行主工程写入：

1. **同步提交并推送**：更新组件版本、只提交本次变更并推送，不重复询问。
2. **仅提交**：更新组件版本、只创建本地提交，不推送。
3. **不提交也不推送**：不修改主工程。

使用独立暂存区生成组件更新提交，保留其他已暂存、未暂存、未跟踪内容，包括同一 Podfile 的不相关修改。已有改动的工程必须处于与远端一致的 develop；需要切分支/快进、目标组件声明被修改、分支有未推送提交/分叉或动态版本时停止，不 stash/reset。干净工程可切 develop 并快进。不运行 pod install，不更改 Podfile.lock。推送前校验仅包含本次组件更新、父节点和远端基线一致；真实 hook/签名失败或改写提交时停止并保留现场。

从 0.2.3 起，默认发布信息由技能总结全部增量提交，不再拼接原始标题；1–4 指总结后的要点数，25 字上限包含标点、空格、英文和数字。脚本保留原始提交证据，默认 note 返回 null，需先生成摘要再发布；不会机械截断或虚构改动。用户明确指定的发布信息仍优先，不静默改写。

主工程的完整提交说明直接复用发布时实际传给 `--note` 的摘要，不添加固定标题，也不展开原始提交列表。用户明确提供或历史版本已有的多行日志原样保留；提交后校验内容，发现 hook 改写则停止，不自动修订或推送已有提交。

默认本机路径是 `/Users/vshow/Desktop/Work/vone` 和 `/Users/vshow/Desktop/Work/poppo`，用户可明确覆盖。同步辅助脚本需要 Python 3.9+、Git 和 Ruby；Ripper 仅做静态语法检查，不执行 Podfile。

## 入口与资源

- `.codex-plugin/plugin.json`：Codex 插件声明。
- `.claude-plugin/plugin.json`：Claude Code 插件声明。
- `skills/xym-compoments-publish/SKILL.md`：两端共用的技能入口。
- `skills/xym-compoments-publish/scripts/release_context.py`：只读收集组件和发布设置。
- `skills/xym-compoments-publish/scripts/sync_projects.py`：只读版本分类/预检、隔离同步与提交；只有明确选择第一项才传 `--push`。
- `skills/xym-compoments-publish/references/project-sync.md`：版本映射、三选一授权、隔离提交及安全推送流程。
- `skills/xym-compoments-publish/agents/openai.yaml`：Codex 技能展示名称、简介和默认提示词。

安装与升级命令见[市场说明](../../README.md)。
