# xuyiming-workshop

Xuyiming 的个人插件市场，同时提供 Codex 和 Claude Code 的市场清单。两端安装同一个插件目录，共用技能说明与执行脚本。

## 仓库结构

```text
xuyiming-workshop/
├── .agents/plugins/marketplace.json       # Codex 市场清单
├── .claude-plugin/marketplace.json        # Claude Code 市场清单
├── plugins/
│   ├── xym-iphone-duo-adapt/              # 最小侵入适配 + 每批独立双机型回归
│   ├── xym-compoments-publish/            # 插件：独立安装、独立版本
│   │   ├── .codex-plugin/plugin.json     # Codex 插件声明
│   │   ├── .claude-plugin/plugin.json    # Claude Code 插件声明
│   │   ├── README.md
│   │   └── skills/
│   │       └── xym-compoments-publish/   # 技能：具体发布流程
│   │           ├── SKILL.md
│   │           ├── scripts/release_context.py
│   │           ├── scripts/sync_projects.py
│   │           ├── references/project-sync.md
│   │           └── agents/openai.yaml   # Codex 展示信息
│   ├── xym-dev-tools/
│   │   ├── .codex-plugin/plugin.json
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/<skill-name>/SKILL.md  # 7 个开发技能
│   │   ├── scripts/{git_context,github_review}.py
│   │   └── LICENSE + NOTICE.md
│   ├── xym-lark-tools/
│   │   ├── .codex-plugin/plugin.json
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/<skill-name>/SKILL.md  # 3 个飞书技能
│   │   ├── scripts/lark_api.py
│   │   └── LICENSE + NOTICE.md
│   ├── xym-ios-build/                    # 构建、结果/覆盖率、Proto
│   ├── xym-ios-quality/                  # 项目规则、格式、术语、TDD、文档
│   ├── xym-ios-diagnostics/              # dSYM、复现、引用、清理审计
│   ├── xym-tmp-guard/                    # 可选：显式临时任务槽
│   ├── xym-visual-patch/                 # 可选：本地标注网页 + JSON
│   └── xym-weekly-okr/                   # 本人跨仓库提交 → 四段式 OKR 周报
├── scripts/validate_marketplace.py       # 双端结构与一致性校验
├── tests/test_*.py                       # Git/API/原生工具包装/本地 HTTP 测试
└── docs/cross-project-delivery.md        # 完整映射、能力与验证边界
```

市场清单中的插件路径相对于仓库根目录；插件声明中的 `./skills/` 相对于插件根目录。每个技能使用独立目录和 `SKILL.md`，插件可包含多个技能。插件名与技能名可以相同，当前保留已发布的 `xym-compoments-publish` 标识。

发布插件的 `scripts/release_context.py` 随技能一起打包；公共工具脚本放在各自插件的 `scripts/`，由同一插件内的技能共享，不依赖市场仓库外部的文件。`agents/openai.yaml` 提供 Codex 的展示信息，不会创建独立 Agent。

## 安装前提

这是私有 GitHub 仓库，安装者需要仓库访问权限和有效的 Git HTTPS 凭据。插件均在本机执行，按需安装，不强制安装所有工具：组件发布需要 Git、Python 3、Wukong 和构建环境；公共开发工具需要 Python 3.9+、Git，GitHub 功能另需已登录的 `gh`；飞书真实调用需要官方 `lark-cli` 和用户授权，预览只需 Python。

组件发布后的工程同步另需 Ruby 标准库 Ripper，用于静态检查 Podfile，不会加载或执行 Podfile。

以下命令使用客户端原生命令；已使用 RTK 的环境可以添加 `rtk proxy` 前缀。

## Codex

首次安装：

```bash
codex plugin marketplace add https://github.com/MIKU-MIKU-39/xuyiming-workshop.git
codex plugin add xym-compoments-publish@xuyiming-workshop
```

选择安装公共工具插件：

```bash
codex plugin add xym-dev-tools@xuyiming-workshop
codex plugin add xym-lark-tools@xuyiming-workshop
codex plugin add xym-ios-build@xuyiming-workshop
codex plugin add xym-ios-quality@xuyiming-workshop
codex plugin add xym-ios-diagnostics@xuyiming-workshop
codex plugin add xym-iphone-duo-adapt@xuyiming-workshop
# 可选，不会自动启用全局 hook
codex plugin add xym-tmp-guard@xuyiming-workshop
codex plugin add xym-visual-patch@xuyiming-workshop
codex plugin add xym-weekly-okr@xuyiming-workshop
```

升级或重新安装：

```bash
codex plugin marketplace upgrade xuyiming-workshop
codex plugin add xym-compoments-publish@xuyiming-workshop
```

安装完成后新建 Codex 任务，可通过技能选择器选择发布技能，或直接提出“使用 xym-compoments-publish 发布当前组件”。

如果还存在 `~/.codex/skills/xym-compoments-publish` 的同名独立 skill，插件升级不会覆盖它。请在新任务中从插件选择器选择新版，或显式调用 `$xym-compoments-publish:xym-compoments-publish`，避免继续使用独立旧副本。仓库开发与推送本身不会修改已安装的 skill 或插件缓存，需用户执行升级命令才安装新版。

## Claude Code

首次安装：

```bash
claude plugin marketplace add https://github.com/MIKU-MIKU-39/xuyiming-workshop.git
claude plugin install xym-compoments-publish@xuyiming-workshop --scope user
```

公共工具可分别安装：`claude plugin install xym-dev-tools@xuyiming-workshop --scope user`、`claude plugin install xym-lark-tools@xuyiming-workshop --scope user`。升级时把下方插件名替换为对应名称即可。

升级已安装插件：

```bash
claude plugin marketplace update xuyiming-workshop
claude plugin update xym-compoments-publish@xuyiming-workshop --scope user
```

安装或更新后，在 Claude Code 会话中执行 `/reload-plugins`，再显式调用：

```text
/xym-compoments-publish:xym-compoments-publish
```

两端都会按技能说明检查发布信息、混淆策略和发布环境；明确要求发布时，展示参数摘要后直接执行，无需二次确认。仅检查参数或编辑技能时不会触发发布。

从发布插件 0.2.4 起，发布成功后弹框选择「同步提交并推送」「仅提交」「不提交也不推送」。VO / PLA / DRL 分别对应 Vone / Poppo / DoraLive，无标识则先明确工程。只提交目标组件版本更新，保留主工程其他本地改动；选择第一项后不重复询问推送，未回答不写入主工程。

## 插件

- [xym-iphone-duo-adapt](plugins/xym-iphone-duo-adapt/README.md)：最小侵入适配 iPhone Duo，保持原 UI，每 1–3 页由独立子 Agent 代码审核及双机型模拟器回归。
- [xym-compoments-publish](plugins/xym-compoments-publish/README.md)：检查发布信息、混淆策略与环境，发布后三选一同步 Vone/Poppo/DoraLive，只提交组件更新，保留其他改动。
- [xym-dev-tools](plugins/xym-dev-tools/README.md)：Git 上下文、GitHub 评审线程、代码审查、简化、设计计划、安全提交、经验提炼（7 个技能）。
- [xym-lark-tools](plugins/xym-lark-tools/README.md)：文档、OKR、周报（3 个技能），支持 Markdown/XML、引用映射与块版本保护。
- [xym-ios-build](plugins/xym-ios-build/README.md)：构建/测试/Pods/xcresult/覆盖率包装，Proto 生成（2 个技能）。
- [xym-ios-quality](plugins/xym-ios-quality/README.md)：工程规则、格式化、术语、TDD、组件复用、API 文档（6 个技能）。
- [xym-ios-diagnostics](plugins/xym-ios-diagnostics/README.md)：符号化、崩溃复现、符号引用、无用代码审计（4 个技能）。
- [xym-tmp-guard](plugins/xym-tmp-guard/README.md)：可选的临时目录生命周期与清理（1 个技能），无自动清理 hook。
- [xym-visual-patch](plugins/xym-visual-patch/README.md)：可选的本地截图标注（1 个技能），纯 Python + HTML。
- [xym-weekly-okr](plugins/xym-weekly-okr/README.md)：本人上周跨仓库提交采集与四段式 OKR 周报（1 个技能），支持黑名单和证据追溯，个人配置独立保存。

共 10 个插件、27 个技能。公共工具来自本地 `baitu-workshop` 的通用部分，已移除环境专属路径与业务依赖，保留 MIT 来源声明；详见 [完整映射与交付边界](docs/cross-project-delivery.md) 和 [前期审计](docs/baitu-reuse-audit.md)。它们是 Skill 或 Skill + CLI 脚本插件，不额外启动 MCP 服务。插件可独立安装；iOS 工具优先目标项目配置，不强制公司技术栈。

## 维护与校验

在本仓库修改源文件，并在仓库根目录执行：

```bash
python3 scripts/validate_marketplace.py
python3 -B -m unittest discover -s tests -v
```

校验器仅依赖 Python 3 标准库，检查两份市场清单的名称、插件集合和路径，以及两端插件声明的一致性、技能入口和资源文件。测试使用临时 Git 仓库、API/CLI 替身和临时回环 HTTP 服务，需要允许绑定 127.0.0.1；不执行 Wukong、不发布组件、不发送真实评审评论或飞书写请求。

安装了 Claude Code 时，还可以使用其原生清单校验：

```bash
claude plugin validate .
claude plugin validate ./plugins/xym-compoments-publish
```

新增插件时放入 `plugins/<plugin-name>/`，再分别登记到两份市场清单中；新增技能时放入所属插件的 `skills/<skill-name>/`。发布插件更新时同步修改两端 `plugin.json` 的版本，市场清单只维护插件路径，避免重复维护版本。

GitHub 来源的升级命令读取远端仓库。源文件的本地修改完成并提交、推送后，其他用户才能通过升级命令获取新版本。
