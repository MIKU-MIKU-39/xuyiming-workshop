---
name: git-submit
description: "用户明确要求整理 Git 提交、commit 或推送时使用；检查已有暂存内容与授权范围，沿用项目提交格式，不默认 add 全部或 push。"
---

# 安全提交

先运行 git status --short、git diff、git diff --cached，记录分支和 HEAD。区分用户已有 staged 与本任务修改。缺少范围时先给拟提交文件清单；包含无关改动必须确认，不能擅自 unstage。

- staging 用明确路径；一个文件混有其他修改时使用可审查的局部补丁或请用户确定，不盲目 git add -A。
- 读取项目提交规范/最近日志，生成符合项目风格的说明。不强制中文、emoji、ticket 或作者身份；不改 git config。
- 检查密钥、产物、意外删除和项目必需测试/术语规则。检查失败不跳过 hook，不用 --no-verify。检查 staged 内容而非仅工作区。
- 用户只要求写 commit message 就只输出文案；要求 commit 才实际提交。默认不 amend、不 rebase、不覆盖作者。
- commit 后核对 HEAD 和状态。push 是独立远端写入，仅用户明确要求时确认 remote/branch 并正常推送；不默认 force。
- 输出提交 hash、摘要、保留的本地变更和是否推送。提交被 hook 或签名阻止时保留现场、报告原因。
