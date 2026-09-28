# Xym Weekly OKR

作者：Xuyiming。版本：0.1.0。

从多个本地 Git 仓库提炼本人上一完整自然周的工作，生成中文 OKR 周报。正文固定包含：本周进展、发现的问题、风险同步与资源支持、下周进度计划，并附提交依据与采集范围说明。不负责上传或定时发送周报。

## 安装

已添加 `xuyiming-workshop` 市场时：

```bash
codex plugin marketplace upgrade xuyiming-workshop
codex plugin add xym-weekly-okr@xuyiming-workshop
```

Claude Code：

```bash
claude plugin marketplace update xuyiming-workshop
claude plugin install xym-weekly-okr@xuyiming-workshop --scope user
```

未添加市场时，先执行对应客户端的 `plugin marketplace add https://github.com/MIKU-MIKU-39/xuyiming-workshop.git`。私有仓库需要访问权限和 Git 凭据。不会安装额外 MCP 服务或全局 hook。

## 使用

在新任务中调用插件提供的 `$xym-weekly-okr:xym-weekly-okr`，例如“根据我上一完整自然周的提交写 OKR 周报”。如果有同名独立 Skill，插件安装不会覆盖它，请明确选择插件来源。

首次使用会确认扫描根目录与本人 Git 作者邮箱，并按 [配置说明](skills/xym-weekly-okr/references/config.md) 创建个人配置。两端默认共用 `$CODEX_HOME/xym-weekly-okr/config.json`，未设置 CODEX_HOME 时为 `~/.codex/xym-weekly-okr/config.json`；Claude Code 无需安装 Codex CLI，也可通过 `--config` 使用其他路径。已有配置不覆盖。

个人邮箱、扫描路径、黑名单和实际周报不随插件发布；包内只有通用说明与合成测试。用户可以说“将某仓库加入周报黑名单”，也可以编辑配置的 `blacklist`。当前 OKR 可写入 `okr_items`；未提供时输出标明“建议”的草稿，不照搬历史范例。

## 范围与限制

- 默认北京时间上一完整周，按提交者时间筛选、按作者邮箱精确匹配，支持邮箱别名。
- 支持嵌套仓库、submodule 和 worktree；同一 SHA 跨分支或 checkout 只保留一份。
- 仅采集配置范围内的本地 refs，不自动 fetch、切换分支、构建、发布或修改业务代码。扫描跳过项和错误会在报告中披露。
- 提交消息是未核实资料，不能直接证明测试通过、部署上线、缺陷数或百分比指标。
- 脚本需要 Python 3.9+（包含时区数据）及支持 `git log --since-as-filter` 的 Git；部分克隆还需 Git 支持 `GIT_NO_LAZY_FETCH`，缺失对象时报告失败，不自动联网补齐。

## 验证

在仓库根目录执行：

```bash
python3 scripts/validate_marketplace.py
python3 -B -m unittest discover -s plugins/xym-weekly-okr/skills/xym-weekly-okr/scripts -p 'test_*.py' -v
```

16 项测试使用临时 Git 仓库，覆盖日期边界、作者、分支、远程跟踪 refs、detached HEAD、stash 排除、去重、黑名单、嵌套仓库、异常处理及只读行为，不访问真实业务提交。
