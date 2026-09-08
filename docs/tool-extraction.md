# 公共工具提炼记录

维护者：Xuyiming。来源为本地 `baitu-workshop` 对应的 [BaiTu-iOS/workshop](https://github.com/BaiTu-iOS/workshop)，参考提交 `710f119995332658a926919ebdb7c87049020e65`。

## 来源 → 可安装插件

| 上游能力 | 个人插件 / 技能 | 提炼后的公共部分 |
| --- | --- | --- |
| `wk/review/scripts/collect.py` | `xym-dev-tools` / `git-context` | Git 基线、变更范围、补丁、未跟踪文件、只读索引检查 |
| `wk/gh-pr-review-fix` | `xym-dev-tools` / `github-review` | 评审线程查询、根评论回复、解决线程、用户授权边界 |
| `wk/lark-wiki` 的上传步骤 | `xym-lark-tools` / `lark-docs` | Markdown 文档新建/更新、目标核实、失败防重复 |
| `wk/okr-sync` 的 CLI 命令参考 | `xym-lark-tools` / `lark-okr` | 身份与周期查询、KR 创建、进展记录、指标回查 |

目录采用同一个插件容纳相关技能、脚本在插件内共享的方式。Codex 和 Claude Code 各有自己的清单，读取同一份 SKILL.md 和脚本；没有创建新的 Agent 常驻进程或 MCP 服务。

## 重写和兼容调整

- Git 采集器沿用上游只读实现，增加 Python 3.9 注解兼容；通过真实临时 Git 仓库验证范围与索引不变。
- GitHub 不再依赖另一台机器的绝对缓存路径；改为包内独立脚本，线程和评论分别分页，检查 GraphQL 部分失败和重复游标。写入前确认线程归属和已检查的 HEAD，正文通过 JSON stdin 传递。
- 飞书旧版文档参数替换为当前 `docs +create/+update`，单 KR 创建使用 `okr +create`。使用 `simple` JSON 正文，避免把富文本 ContentBlock 误按新版 simple 输入处理。
- 飞书不默认覆盖全文；不把读取失败转成新建；不把进展文本等同于指标值、评分或权重。脚本对写入部分成功、缺失返回 ID、超时做明确失败处理，不自动重试。
- 依赖由用户在本机配置；插件不保存密码、token、默认员工、租户、知识库或组件映射。

## 本次未迁移

- iOS 组件 API 文档生成、飞书批量组件同步：依赖公司组件仓库/业务映射。
- 公司发布、dSYM 下载和内部事故平台调用：依赖内部主机、发布权限和业务约定；已有组件发布插件继续独立维护。
- 强制提交格式、自动推送脚本、重复的构建封装：不与现有发布和 `wk-xcodebuild` 工具叠加。
- hooks、agents、MCP 服务：本次固定 CLI 能力不需要这些运行结构，避免无用途的空壳配置。

## 验证与分发边界

执行市场结构校验、公共工具行为测试以及宿主清单/技能校验。测试不访问真实 GitHub 评审或飞书租户写接口。当前机器没有 `lark-cli`，飞书仅核验官方契约、请求生成和错误处理，真实鉴权、租户权限和资源渲染仍需使用者联调。

本次新增两个插件均为 `0.1.0`，原 `xym-compoments-publish` 保持 `0.1.1`。本地修改提交并推送后，远端安装者才能通过 marketplace upgrade/update 获取新增条目；修改源仓库本身不等于已安装到客户端缓存。
