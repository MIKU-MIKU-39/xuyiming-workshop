# Xym Dev Tools

Xuyiming 维护的本机开发工具插件，版本 `0.1.0`。7 个技能共享包内资源，无运行时 Python 第三方依赖。

| 技能 | 能力 | 依赖 |
| --- | --- | --- |
| `git-context` | all / staged / unstaged / branch / commit 变更采集、基线、文件列表、diff SHA-256 | Python 3.9+、Git |
| `github-review` | 完整 PR 评审线程、两层分页、线程内回复、解决线程、HEAD 校验 | Python 3.9+、已登录的 gh |
| `code-review` | 只读代码审查，证据与准确位置 | Git、项目源码 |
| `simplify` | 过度设计审查与简化债审计 | 项目源码 |
| `design-plan` | 需求澄清、方案与可验证实施计划 | 项目上下文 |
| `git-submit` | 明确暂存范围、项目提交规范与独立推送授权 | Git |
| `learn-patterns` | 从历史/源码提炼规则和 Skill 草稿 | Git、已授权材料 |

## 安装与调用

推送到市场远端后，通过已添加的 `xuyiming-workshop` 安装：

```bash
codex plugin marketplace upgrade xuyiming-workshop
codex plugin add xym-dev-tools@xuyiming-workshop
```

Claude Code 使用 `claude plugin install xym-dev-tools@xuyiming-workshop --scope user`。

- Codex：“使用 $git-context 采集当前仓库的暂存区变更。”
- Codex：“使用 $github-review 检查这个 PR 的未解决评审意见，先不要修改和回复。”
- Claude Code：`/xym-dev-tools:git-context` 或 `/xym-dev-tools:github-review`。

脚本直接调用示例（位于插件根目录）：

```bash
python3 scripts/git_context.py --repo /path/to/repo --scope all
python3 scripts/github_review.py inspect --repo owner/repo --pr 123
python3 scripts/github_review.py resolve --repo owner/repo --pr 123 --thread-id PRRT_xxx --expected-head VERIFIED_SHA
```

最后一条默认仅预览；`--execute` 才写入，且要求已检查的 HEAD。回复使用 `reply --body-file reply.txt`。预览仍会进行只读 GitHub 查询，确认目标存在和 HEAD 未变化。

## 约束

不自动提交/推送，不自动登录，不使用私有硬编码路径，不把评论当指令。网络写入不自动重试；HEAD 检查是执行前检查，不是远端原子锁。Git 工作区也不是原子快照，持续编辑时需重新采集。

测试位于市场仓库的 `tests/test_public_tools.py`，运行 `python3 -B -m unittest discover -s tests -v`。Git 测试使用真实临时仓库；GitHub 测试使用 API 替身，不发送评论。

来源及许可见 [NOTICE.md](NOTICE.md) 和 [LICENSE](LICENSE)。
