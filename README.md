# xuyiming-workshop

Xuyiming 的个人插件市场，同时提供 Codex 和 Claude Code 的市场清单。两端安装同一个插件目录，共用技能说明与执行脚本。

## 仓库结构

```text
xuyiming-workshop/
├── .agents/plugins/marketplace.json       # Codex 市场清单
├── .claude-plugin/marketplace.json        # Claude Code 市场清单
├── plugins/
│   └── xym-compoments-publish/            # 插件：独立安装、独立版本
│       ├── .codex-plugin/plugin.json     # Codex 插件声明
│       ├── .claude-plugin/plugin.json    # Claude Code 插件声明
│       ├── README.md
│       └── skills/
│           └── xym-compoments-publish/   # 技能：具体发布流程
│               ├── SKILL.md
│               ├── scripts/release_context.py
│               └── agents/openai.yaml   # Codex 展示信息
└── scripts/validate_marketplace.py       # 双端结构与一致性校验
```

市场清单中的插件路径相对于仓库根目录；插件声明中的 `./skills/` 相对于插件根目录。每个技能使用独立目录和 `SKILL.md`，插件可包含多个技能。插件名与技能名可以相同，当前保留已发布的 `xym-compoments-publish` 标识。

`scripts/release_context.py` 随技能一起打包，不依赖市场仓库外部的共享文件。`agents/openai.yaml` 提供 Codex 的展示信息，不会创建独立 Agent。

## 安装前提

这是私有 GitHub 仓库，安装者需要仓库访问权限和有效的 Git HTTPS 凭据。组件发布在本机执行，还需要 Git、Python 3、Wukong 和组件自身的构建环境。

以下命令使用客户端原生命令；已使用 RTK 的环境可以添加 `rtk proxy` 前缀。

## Codex

首次安装：

```bash
codex plugin marketplace add https://github.com/MIKU-MIKU-39/xuyiming-workshop.git
codex plugin add xym-compoments-publish@xuyiming-workshop
```

升级或重新安装：

```bash
codex plugin marketplace upgrade xuyiming-workshop
codex plugin add xym-compoments-publish@xuyiming-workshop
```

安装完成后新建 Codex 任务，可通过技能选择器选择发布技能，或直接提出“使用 xym-compoments-publish 发布当前组件”。

## Claude Code

首次安装：

```bash
claude plugin marketplace add https://github.com/MIKU-MIKU-39/xuyiming-workshop.git
claude plugin install xym-compoments-publish@xuyiming-workshop --scope user
```

升级已安装插件：

```bash
claude plugin marketplace update xuyiming-workshop
claude plugin update xym-compoments-publish@xuyiming-workshop --scope user
```

安装或更新后，在 Claude Code 会话中执行 `/reload-plugins`，再显式调用：

```text
/xym-compoments-publish:xym-compoments-publish
```

两端都会按技能说明检查发布信息、混淆策略和发布环境；实际发布前需要确认本次解析出的发布设置。

## 插件

- [xym-compoments-publish](plugins/xym-compoments-publish/README.md)：检查当前组件的增量发布信息、混淆策略与发布环境，确认后通过 Wukong 发布。

## 维护与校验

在本仓库修改源文件，并在仓库根目录执行：

```bash
python3 scripts/validate_marketplace.py
```

校验器仅依赖 Python 3 标准库，检查两份市场清单的名称、插件集合和路径，以及两端插件声明的一致性、技能入口和资源文件。它不执行 Wukong，也不发布组件。

安装了 Claude Code 时，还可以使用其原生清单校验：

```bash
claude plugin validate .
claude plugin validate ./plugins/xym-compoments-publish
```

新增插件时放入 `plugins/<plugin-name>/`，再分别登记到两份市场清单中；新增技能时放入所属插件的 `skills/<skill-name>/`。发布插件更新时同步修改两端 `plugin.json` 的版本，市场清单只维护插件路径，避免重复维护版本。

GitHub 来源的升级命令读取远端仓库。源文件的本地修改完成并提交、推送后，其他用户才能通过升级命令获取新版本。
