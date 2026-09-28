# 配置与运行

作者：Xuyiming。

个人配置独立于 Skill，升级时保留：`$CODEX_HOME/xym-weekly-okr/config.json`，未设置 CODEX_HOME 时使用 `~/.codex/xym-weekly-okr/config.json`。Python 3.9+（带 zoneinfo 时区数据）、Git 支持 `log --since-as-filter` 即可，不依赖第三方 Python 包。旧 Git 不支持时报告错误，不降级为可能漏掉历史的 `--since`。

```json
{
  "version": 1,
  "timezone": "Asia/Shanghai",
  "search_roots": ["~/Desktop/Work", "~/Documents/Codex", "~/workshop"],
  "author_emails": ["your-email@example.com", "your-work-email@example.com"],
  "blacklist": ["MikuPet", "demo-*", "~/Desktop/Work/private-*"],
  "skip_directory_names": ["node_modules", "Pods", ".build", ".venv", "DerivedData"],
  "okr_items": ["【诺】高质量、按期完成业务需求交付，保障版本稳定上线"]
}
```

上面是示例，不自动将示例黑名单或目标写入用户配置。实际安装时配置的黑名单和 OKR 可以为空数组。

- `search_roots`：绝对路径或 `~/` 路径；可配置 `~` 扫描用户目录。默认安装跳过 Library、缓存和常见依赖；这不是全磁盘扫描。显式列出的根目录可以覆盖目录名跳过规则，但不能覆盖黑名单。
- `author_emails`：按原始 Git author 邮箱（不套用 mailmap）精确匹配，忽略大小写；支持公司邮箱、GitHub noreply 邮箱等别名。不能为空；不因其他邮箱作者姓名相同就自动归入本人。
- `blacklist`：不带 `/` 的条目按目录/仓库名称匹配（大小写敏感）；绝对路径按完整路径匹配。支持 `*`、`?`、`[abc]`，这里的 `*` 也可以匹配路径分隔符。过滤目录连同子仓库一起剪枝；匹配到扫描根目录或其祖先时也排除。符号链接规范化可能影响路径匹配，推荐真实绝对路径。
- `skip_directory_names`：按目录名精确跳过，`.git` 始终不递归。不想排除 Pods 中真正维护的仓库时，将具体组件路径显式加入根目录，或者修改此列表。
- `okr_items`：本期目标原文字符串列表；为空时只生成标注清楚的建议目标。不要把过往周报全文放入该字段。

## 常见调用

在 Skill 目录执行（若环境要求 RTK，在以下命令前加 `rtk proxy`）：

```bash
python3 scripts/collect.py --discover-only --output /tmp/weekly-discovery-new.json
python3 scripts/collect.py --as-of 2026-09-28 --output /tmp/weekly-evidence-new.json
python3 -B -m unittest discover -s scripts -p 'test_*.py'
```

`--as-of 2026-09-28` 产生北京时间 `[2026-09-21 00:00, 2026-09-28 00:00)`。即使周日运行，也仍然选择上一个已结束的周，不包含本周未结束的周日。指定不带时区的日期时间时按配置时区解释。

默认不 fetch，仅采集本地分支、远程跟踪分支、标签和 HEAD 可达提交；同一 SHA 跨仓库只保留一份，同时保存所有来源路径。工作区未提交修改不计入。历史重写或 cherry-pick 会产生新的提交者时间，应在报告里交代此口径，必要时结合作者时间辨认旧工作重放。

## 输出与故障

JSON 包含 `period`、`author_emails`、`search_roots`、`blacklist`、`skip_directory_names`、`okr_items`、`repositories`、`excluded`、`warnings`、`commits`。每条提交带完整 SHA、作者、作者时间、提交者时间、说明、变更文件和来源仓库。合并提交的文件列表可能为空，不能据此判定无变化。

仓库状态：`ok`、`empty`、`no_commits_in_period`、`no_matching_author`、`error`；发现模式为 `discovered`。退出码 0 是完成，2 是部分采集/扫描失败或浅克隆等历史完整性风险，1 是配置或输出错误。每个 Git 子命令最长 60 秒，失败仓库不会丢弃其他仓库结果。输出路径不得已存在，防止覆盖前一份证据。

运行后先看覆盖范围，尤其是 `~/Library`、`~/.codex/worktrees` 等默认跳过目录是否藏有需要统计的仓库；若有，加入具体根目录。没有扫描到的外置盘、其他账户目录、远端未同步提交不在本次范围。不要把“配置内采集完成”写成“所有远端代码完整统计”。
