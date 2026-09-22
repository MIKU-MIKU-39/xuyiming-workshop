# 发布后同步 Vone / Poppo

维护：Xuyiming。完成组件发布后，或用户要求同步已经发布的组件版本时，读取本流程。

## 1. 确定本次真实发布结果

保留组件名、本次实际使用的发布信息、环境、发布前后提交，以及发布工具的成功证据。完整版本号必须来自本次 Wukong 输出中的成功记录，必要时交叉核对新建 tag 和对应 Specs；不能用当前 Podspec、旧 tag 或版本自增推算代替。不要把日志中引用的依赖版本当成本次组件版本。不能确定完整成功结果时，报告已知状态并停止同步，不自动重发。

只读分类（命令路径相对于本技能目录；版本参数可重复）：

```bash
python3 scripts/sync_projects.py classify --version '104.b1.VO-SC' --version '104.b1.PLA-SC'
```

| 本次实际版本 | 可建议的工程 |
| --- | --- |
| 后缀包含 VO，包括 `.VO-CF`、`.VO-SC`、`.VONE` | Vone |
| 后缀包含 PLA 标识，例如 `.PLA-CF`、`.PLA-SC` | Poppo |
| 只有一个明确平台版本 | 只同步这个平台，不给另一平台合成版本 |
| 没有平台标识，例如 `363` 或规则未覆盖的 `.POPPO` | 询问 Vone、Poppo，还是两个都同步 |
| 同一版本同时标识两个平台、同平台多个版本、已知与未知版本混合 | 展示完整候选，请用户明确逐工程的版本映射 |

`needs_mapping=false` 只表示候选明确，**不表示用户同意同步**。即使只有一个无标识版本，也必须询问工程。不能为了匹配另一个工程而删除、替换或补齐版本后缀。

## 2. 获取同步批准并预检

已知的本机工程路径：

- Vone：`/Users/vshow/Desktop/Work/vone`
- Poppo：`/Users/vshow/Desktop/Work/poppo`

优先遵从用户在当前任务给出的路径和远端覆盖。路径不存在、仓库身份与目标不符、或不在这台 Mac 时，询问实际路径；不要根据名字搜索后自动选一个，不创建或克隆工程。

展示组件、完整版本、工程路径、远端名、目标分支 `develop`、发布信息，并询问是否执行「拉取 develop → 更新 Podfile → 本地提交」。选项可包含各个可用工程、全部可用工程、不需要同步；无标识版本的选项为 Vone / Poppo / 两个 / 不同步。用户未回答时保持等待，不视为默认同意；不需要同步则结束。

路径和映射确定后，可先做只读预检；双工程必须先分别预检通过。示例：

```bash
python3 scripts/sync_projects.py plan \
  --project-path /Users/vshow/Desktop/Work/vone \
  --component BTRNBridgeModule --version '104.b1.VO-SC' --remote origin
```

核对 Git 根目录及目标远端的仓库身份；展示时不输出 URL 内凭据。plan 输出使用**本地缓存**的远端 develop，不联网，`remote_fresh=false`；它不是远端最新状态证明。记录 `develop_head`、旧版本及 diff。没有远端跟踪分支时，先核实远端身份，用户同意同步后才获取 develop，再重新预检。

阻塞条件：工作区/暂存区不干净、detached HEAD、Git 操作未完成、develop 有未推送提交或分叉、Podfile 不存在/非普通跟踪文件、目标 pod 缺失或版本表达式不受支持。说明具体问题，让用户处理或明确新的方案；禁止自动 stash、reset、rebase、强制切换、覆盖用户修改或顺带推送既有提交。

## 3. 执行同步和本地提交

用户批准具体工程/版本映射后，再执行 `sync`，传入该工程预检的 `develop_head`（以下 `DEVELOP_SHA_FROM_PLAN` 代表实际 SHA，不是字面量参数）：

```bash
python3 scripts/sync_projects.py sync \
  --project-path /Users/vshow/Desktop/Work/vone \
  --component BTRNBridgeModule --version '104.b1.VO-SC' --remote origin \
  --expected-develop DEVELOP_SHA_FROM_PLAN \
  --note '本次实际发布信息'
```

脚本再次检查状态，获取 `origin/develop`，切换 develop 并以 `merge --ff-only` 拉取最新代码。这等价于受控的 fetch + 快进 pull；同步结束后留在 develop。远端在预检后正常前进可以快进；本地提交、分叉、远端历史重写等异常停止。Git 身份缺失、鉴权、签名或 hook 失败也停止，不修改全局 Git 配置、不禁用真实工程 hook。

Podfile 处理规则：

- 使用 Ruby 标准库 Ripper 静态语法分析，**不执行 Podfile**，需要 Python 3.9+、Git 和 Ruby。
- 支持普通单行 `pod 'Name', 'version'`、双引号、可选括号、行尾注释和 `:configurations => [...]`。
- 同组件的重复声明和 subspec 仅在旧版本一致时一起更新，保留引号、注释、编码和换行。
- 动态版本、条件调用、多行声明、`:path`/`:git` 等源引用或不支持的选项停止并询问；不要退回全局文本替换或执行 Ruby 配置。
- 只改目标组件的字面量版本，只暂存/提交 Podfile；不运行 `pod install/update`，不改 Podfile.lock。
- 版本已经一致则报告 `unchanged`，不创建空提交、不询问推送不存在的提交。

主工程的完整提交说明直接使用本次组件更新日志，即发布时实际传给 Wukong `--note` 的内容。不要添加 `chore(deps): update ...`、组件名或版本号等固定标题，也不要只把日志放在正文中；单行日志直接成为提交标题，多行日志保留原有段落及备注。同步已发布版本时，使用该版本真实的更新日志；缺失则先获取或询问用户，不能根据主工程的版本号 diff 编造日志。

脚本使用 `git commit --cleanup=verbatim -m <更新日志>`，提交后核对完整提交说明和 Podfile 差异。若 hook 改写说明则报告并停止，不自动 amend 或推送。报告脚本返回的 `commit`、`base_commit`、完整版本及工程路径；提交失败时保留修改/暂存状态，不重置。

多个工程逐个执行；如果前一个已提交、后一个失败，准确报告部分完成及各工程状态，不回滚成功的本地提交、不盲目重试。失败工程修复后先重新预检。

## 4. 单独询问是否推送

本地提交完成后明确询问：「以下工程的 develop 已生成本地提交，是否推送远端？」，列出每个工程、远端、完整版本和提交 SHA。用户可选择部分、全部或不推送。发布批准和同步批准都不等于推送批准；没有答复就保留本地提交。

对用户同意的工程，推送前再次核对：

1. 工作区干净，当前分支仍为 develop，HEAD 等于刚才获批的 `commit`。
2. 该提交只有 Podfile 的预期版本差异，父提交等于记录的 `base_commit`，完整提交说明与本次组件更新日志一致。
3. 远端身份仍一致，fetch/push URL 指向同一目标；多 push URL、身份变化或无法确定时询问，不猜测。
4. 通过 `git ls-remote --heads <remote> refs/heads/develop` 核实远端仍等于 `base_commit`。若前进、消失或改写，停止说明，不自动合并、重建提交或强推。

核对通过后，使用固定 argv 的 `git push <remote> <approved-commit>:refs/heads/develop`，不带 `--force`。随后读远端 develop SHA 验证结果。网络中断/结果不明时先查远端；不得盲目重复推送或重新提交。用户拒绝推送则保留本地提交并报告 SHA。

## 开发与安装边界

本技能的开发、测试或升级仅操作 marketplace 源仓库和临时测试仓库，不触发以上业务操作。更新 marketplace 的提交/推送和应用工程的提交/推送是两个独立授权范围。不要修改安装缓存或同名独立 skill 来代替用户要求的手动升级。
