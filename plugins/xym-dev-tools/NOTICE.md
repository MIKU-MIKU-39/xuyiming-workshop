# 来源与改编说明

维护者：Xuyiming。

上游：[BaiTu-iOS/workshop](https://github.com/BaiTu-iOS/workshop)，本地参考提交 `710f119995332658a926919ebdb7c87049020e65`，MIT 许可。

- `scripts/git_context.py` 改编自上游 `plugins/wk/skills/review/scripts/collect.py`：保留只读索引、明确比较基线、未跟踪文件和限制提示；增加 Python 3.9 注解兼容，并单独封装为通用技能。
- `github-review` 和 `scripts/github_review.py` 依据上游 `plugins/wk/skills/gh-pr-review-fix/SKILL.md` 与 `references/review-thread-commands.md` 提炼工作流。API 包装脚本由 Xuyiming 新编写，移除上游环境的固定缓存路径，补齐线程/评论独立分页、JSON 编码、预览、HEAD 校验与错误检查。
- 不包含上游的内部组件选择规则、公司 Git 主机、账号、凭据或自动提交推送策略。引用公开 API 文档用于核实命令，不复制第三方完整文档。

随插件打包保留上游 MIT 版权声明，新增部分同样使用 MIT。本插件不是 BaiTu-iOS 或 GitHub 的官方插件。

新增通用工作流提炼自上游 `plugins/wk/skills/review`、`brainstorm`、`git-commit`、`learn`、`skill-create` 以及 `plugins/wk-simplify`。保留证据驱动的审查/计划/学习逻辑，移除强制子代理、固定阈值、全局规则自动写入和默认推送约定。上游 which 的入口索引职责由本市场 README 技能表承担，不另建空路由技能。
