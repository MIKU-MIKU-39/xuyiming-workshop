# 来源与改编说明

2026-09-08：扩展 `lark-report`，提炼上游 `plugins/wk/skills/okr-report` 的报告和引用保留流程，去掉固定人员/周期/文档映射；新增 XML、reference-map 和块版本参数，不复制租户数据。仍以同一上游 MIT 声明为准。

维护者：Xuyiming。

上游：[BaiTu-iOS/workshop](https://github.com/BaiTu-iOS/workshop)，本地参考提交 `710f119995332658a926919ebdb7c87049020e65`，MIT 许可。

- 文档技能提炼自 `plugins/wk/skills/lark-wiki/references/step-upload.md` 的目标映射、更新/新建区分和失败防重复策略。不携带 iOS API 文档生成器、公司知识库或具体组件配置。
- OKR 技能提炼自 `plugins/wk/skills/okr-sync/references/lark-cli-okr-commands.md` 的身份和周期核实、目标回查、进展与评分区分。
- `scripts/lark_api.py` 为 Xuyiming 新编写的固定操作包装器；根据官方 [larksuite/cli](https://github.com/larksuite/cli) 当前接口，将旧版文档参数改为 doc-format/content/parent-token，将单 KR 创建改为 `okr +create`，采用 simple JSON，不照搬旧 raw create 命令。

随插件保留上游 MIT 声明，新增部分同样使用 MIT。官方 CLI 由使用者独立安装，不随插件分发。本插件不是 BaiTu-iOS、飞书或 Lark 的官方插件。
