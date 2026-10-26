# 发布后同步 Vone / Poppo / DoraLive

维护：Xuyiming。完成组件发布后，或用户要求同步已经发布的组件版本时，读取本流程。

## 1. 确定本次真实发布结果

保留组件名、本次实际使用的发布信息、环境、发布前后提交，以及发布工具的成功证据。完整版本号必须来自本次 Wukong 输出中的成功记录，必要时交叉核对新建 tag 和对应 Specs；不能用当前 Podspec、旧 tag 或版本自增推算代替。不要把日志中引用的依赖版本当成本次组件版本。不能确定完整成功结果时，报告已知状态并停止同步，不自动重发。

只读分类（命令路径相对于本技能目录；版本参数可重复）：

```bash
python3 scripts/sync_projects.py classify --version '104.b1.VO-SC' --version '104.b1.PLA-SC' --version '104.b1.DRL-SC'
```

| 本次实际版本 | 可建议的工程 |
| --- | --- |
| 后缀包含 VO，包括 `.VO-CF`、`.VO-SC`、`.VONE` | Vone |
| 后缀包含 PLA 标识，例如 `.PLA-CF`、`.PLA-SC` | Poppo |
| 后缀包含 DRL 标识，例如 `.DRL-CF`、`.DRL-SC`、`.DRL-SC.swift-6.3.3` | DoraLive |
| 只有一个明确平台版本 | 只同步这个平台，不给另一平台合成版本 |
| 没有平台标识，例如 `363` 或规则未覆盖的 `.POPPO` | 询问 Vone、Poppo、DoraLive 中需要同步哪些工程 |
| 同一版本同时标识多个平台、同平台多个版本、已知与未知版本混合 | 展示完整候选，请用户明确逐工程的版本映射 |

`needs_mapping=false` 只表示候选明确，**不表示用户同意同步**。即使只有一个无标识版本，也必须询问工程。不能为了匹配另一个工程而删除、替换或补齐版本后缀。

## 2. 发布成功后弹出三选一选择框

已知的本机工程路径：

- Vone：`/Users/vshow/Desktop/Work/vone`
- Poppo：`/Users/vshow/Desktop/Work/poppo`
- DoraLive：同步前向用户确认实际 Git 根目录；不根据项目名推断路径。

优先遵从用户在当前任务给出的路径和远端覆盖。路径不存在、仓库身份与目标不符、或不在这台 Mac 时，询问实际路径；不要根据名字搜索后自动选一个，不创建或克隆工程。

先明确工程/版本映射及实际路径。展示组件、完整版本、工程路径、远端名、目标分支 `develop` 和发布信息，然后用宿主选择工具提供以下三个选项，名称和顺序保持一致：

| 选项 | 授权范围 |
| --- | --- |
| 同步提交并推送 | 同步所展示工程的组件版本，仅提交该组件更新，校验后推送本次提交；不再二次询问推送 |
| 仅提交 | 同步并仅创建本次组件更新的本地提交，不推送 |
| 不提交也不推送 | 不同步主工程，不修改 Podfile，也不暂存、提交或推送 |

优先调用 `request_user_input_async`，问题中包含本次目标和操作，options 为上述三个名称。异步调用返回的 accepted 不是用户答复，不能立即执行同步。若只有 `request_user_input`，须确认当前模式允许；其他宿主用对应的选择工具。工具不可用才改为文本三选一。关闭、取消、没有回答或仅预选都不授权，主工程保持不变；用户选择才决定后续动作。多个明确工程可以在同一问题列出，但不能扩大到未展示的工程；无标识或有歧义的版本先询问映射。DRL 只建议 DoraLive。

路径和映射确定后，可先做只读预检；多个工程必须先分别预检通过。示例：

```bash
python3 scripts/sync_projects.py plan \
  --project-path /Users/vshow/Desktop/Work/vone \
  --component BTRNBridgeModule --version '104.b1.VO-SC' --remote origin
```

核对 Git 根目录及目标远端的仓库身份；展示时不输出 URL 内凭据。plan 输出使用**本地缓存**的远端 develop，不联网，`remote_fresh=false`；它不是远端最新状态证明。记录 `develop_head`、旧版本及 diff。没有远端跟踪分支时，先核实远端身份，用户同意同步后才获取 develop，再重新预检。

允许不相关的已暂存、未暂存、未跟踪改动，也允许同一 Podfile 的其他修改；这些内容必须保持本地及原有暂存状态。有改动时，当前分支必须已是与远端一致的 develop，不能通过切分支或快进搬移用户修改。目标组件声明（包括版本、subspec、注释等）在 HEAD、index、工作文件中不一致时停止，不能替用户决定覆盖。

其他阻塞条件：detached HEAD、Git 操作/冲突未完成、develop 有未推送提交或分叉、Podfile 不存在/不是普通跟踪文件/带特殊 index 标志、动态或不支持的声明。说明具体原因；禁止自动 stash、reset、rebase、强制切换或顺带推送既有提交。

## 3. 执行同步和本地提交

用户选择第一或第二项后，执行 `sync`，传入该工程预检的 `develop_head`（以下 `DEVELOP_SHA_FROM_PLAN` 代表实际 SHA，不是字面量参数）。第二项使用：

```bash
python3 scripts/sync_projects.py sync \
  --project-path /Users/vshow/Desktop/Work/vone \
  --component BTRNBridgeModule --version '104.b1.VO-SC' --remote origin \
  --expected-develop DEVELOP_SHA_FROM_PLAN \
  --note '本次实际发布信息'
```

第一项使用同一命令并添加 `--push`；第三项不调用 sync。脚本默认不推送，不能因用户批准发布而自行添加 `--push`。

脚本再次检查状态并获取 `origin/develop`。干净工程可切换 develop 并 `merge --ff-only`；已有改动的工程必须处于同一基线，fetch 发现远端前进时停止，不更改用户代码。未推送提交、分叉、远端历史重写、身份/鉴权/签名/hook 失败均停止，不修改全局 Git 配置、不禁用真实工程 hook。

Podfile 处理规则：

- 使用 Ruby 标准库 Ripper 静态语法分析，**不执行 Podfile**，需要 Python 3.9+、Git 和 Ruby。
- 支持普通单行 `pod 'Name', 'version'`、双引号、可选括号、行尾注释和 `:configurations => [...]`。
- 同组件的重复声明和 subspec 仅在旧版本一致时一起更新，保留引号、注释、编码和换行。
- 动态版本、条件调用、多行声明、`:path`/`:git` 等源引用或不支持的选项停止并询问；不要退回全局文本替换或执行 Ruby 配置。
- 只改目标组件的字面量版本；从远端基线创建临时 `GIT_INDEX_FILE`，提交树只包含此次版本变化，不包含用户已暂存的其他文件或 Podfile 改动。分别更新工作文件和真实 index 的组件版本，保留其余内容及 staged/unstaged 区分；不能使用 `git add -A`、`git add .` 或整份用户 Podfile 提交。
- 不运行 `pod install/update`，不改 Podfile.lock。
- 版本已经一致则报告 `unchanged`，不创建空提交、不询问推送不存在的提交。

主工程的完整提交说明直接使用本次组件更新日志，即发布时实际传给 Wukong `--note` 的内容。不要添加 `chore(deps): update ...`、组件名或版本号等固定标题，也不要只把日志放在正文中；单行日志直接成为提交标题，多行日志保留原有段落及备注。同步已发布版本时，使用该版本真实的更新日志；缺失则先获取或询问用户，不能根据主工程的版本号 diff 编造日志。

默认发布信息按 SKILL.md 提炼为 1–4 个要点的一句话，总计不超过 25 个字符；主工程原样复用实际发布的这句摘要，不重新总结或展开原始 Git 提交。上述多行保留规则仅用于用户明确覆盖或历史版本已有的真实日志。

脚本使用独立 index 执行 `git commit --cleanup=verbatim -m <更新日志>`，正常运行 hook 和签名。提交后核对唯一父节点、完整提交说明、只有 Podfile 的预期版本差异及原有 index 未被并发改变。hook 若混入其他内容/改写说明，保留现场并停止，不 amend、回滚或推送。提交失败时原有暂存不被覆盖，本次工作文件更新可能留下，报告实际状态，不盲目重试。成功后报告 `commit`、`base_commit`、`pushed`、完整版本和工程路径。

多个工程逐个执行；如果前一个已提交、后一个失败，准确报告部分完成及各工程状态，不回滚成功的本地提交、不盲目重试。失败工程修复后先重新预检。

## 4. 按选择验证并推送

第一项已经授权所展示目标的本次提交与推送，校验通过后连续完成，不再询问。第二项完成本地提交即结束并报告 SHA；后续用户另行明确要求推送时，先按以下条件核验保留的那一条提交，不重新执行 sync 或创建新提交。

推送前核对：

1. 当前分支仍为 develop，HEAD 等于获批的 `commit`；无正在进行的 Git 操作。不相关工作区/暂存内容不构成推送阻塞，也不能加入提交。
2. 该提交只有 Podfile 的预期版本差异，父提交等于记录的 `base_commit`，完整提交说明与本次组件更新日志一致。
3. 远端身份仍一致，fetch/push URL 指向同一目标；多 push URL、身份变化或无法确定时询问，不猜测。
4. 通过 `git ls-remote --heads <remote> refs/heads/develop` 核实远端仍等于 `base_commit`。若前进、消失或改写，停止说明，不自动合并、重建提交或强推。

核对通过后，使用固定 argv 的 `git -c push.followTags=false push <remote> <approved-commit>:refs/heads/develop`，不带 `--force`，不附带其他分支或 tag。随后读远端 develop SHA 验证结果。网络中断/结果不明时只查远端，不重复推送或重新提交。CLI 错误输出中的 `pushed=null` 表示未给出成功结论，须核实实际 HEAD/远端，不可声称一定未上传。

## 开发与安装边界

本技能的开发、测试或升级仅操作 marketplace 源仓库和临时测试仓库，不触发以上业务操作。更新 marketplace 的提交/推送和应用工程的提交/推送是两个独立授权范围。不要修改安装缓存或同名独立 skill 来代替用户要求的手动升级。
