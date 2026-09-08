# BaiTu Workshop 跨项目复用盘点

维护者：Xuyiming。日期：2026-09-07。

## 范围与结论

参考本地 `baitu-workshop`，对应上游 [BaiTu-iOS/workshop](https://github.com/BaiTu-iOS/workshop) 提交 `710f119995332658a926919ebdb7c87049020e65`。本轮检查市场清单中全部 **8 个正式插件**、`wk` 内全部 **18 个 Skill**，以及市场外的 **1 个 legacy hook 目录**。

这是静态资产盘点，不是这些插件在其他项目中的实测认证。下文的新插件名和改造方向均为建议，尚未创建或安装。本轮没有执行构建、格式化、临时目录清理 hook、Git 提交推送或飞书写入。

“通用”分为三层：

- **可保留的核心逻辑**：不依赖特定业务，例如 diff 采集、日志摘要、dSYM UUID 比对。
- **需要项目配置的策略**：设备、业务目录、词表、格式化风格、生成器路径、框架版本等。
- **不随通用版迁移的绑定**：公司私有服务地址、账号、固定组件名单和外部仓库实现；可提供适配入口，但不能假装已具备对应能力。

## 逐插件结论

下表中的源码位置均相对于上游仓库根目录，不是个人市场已经存在的实现路径。

| 上游插件 | 可跨项目复用的逻辑 / 入口 | 需要调整的部分 | 建议去向 |
| --- | --- | --- | --- |
| `wk` `1.4.0` | 18 个工作流中的设计、TDD、审查、崩溃符号化、复现、引用扫描、代码清理、Proto 同步、文档增量和经验提取 | 取消固定 BT 工程、业务前缀、宿主路径和公司 MCP 硬依赖；按能力拆分，详见下表 | 开发工具、iOS 构建、iOS 质量、iOS 诊断和已有飞书工具 |
| `wk-xcodebuild` `1.5.4` | `xcb-run.sh` 保留执行状态与日志；两个 AWK 摘要器；`xcb-devices.sh` 设备发现；`xcb-result.sh` 测试/覆盖率摘要；依赖预检与统计 | 自动目的地需匹配 scheme/动作，不能无设备就无条件选 Mac；支持项目 Bundler 环境；公司依赖修复建议移除；避免覆盖已安装的 `xcb` | 新增 `xym-ios-build` |
| `ios-dev-rules` `1.14.2` | 按 ObjC/Swift/Ruby 路由规则；diff hunk 行区间提取；格式化后重新计算区间；Swift 倒序处理区间；注释/公开接口说明检查 | 项目配置优先；不强制 Masonry/SnapKit、固定 Swift 版本、公司大括号风格或函数行数；移除缓存路径和 Wukong 安装假设；不自动升级公司规则 | 新增 `xym-ios-quality` |
| `ios-blocked-words-check` `1.1.1` | token/单词边界/驼峰与下划线匹配；白名单；文件/目录/diff 输入；JSON 汇总；生成代码到 proto 的来源追踪 | 提炼“项目词表检查器”，词表与白名单外置；不能把公司禁词直接当所有项目的审核规则；staged 必须读索引内容；读失败不得当通过 | `xym-ios-quality` 的可配置词表检查 |
| `wk-xcindent` `1.0.2` | `scripts/xcindent.py` 的词法扫描、作用域缩进、ObjC keyword 对齐、限定行区间；已有 golden / 幂等测试 | 不依赖公司缓存；默认检查/预览，明确要求才写回；按项目宽度；不能把“只动行首空白”宣传为适用于所有字符串/宏场景的安全证明 | `xym-ios-quality` 的 ObjC 缩进能力 |
| `wk-simplify` `1.1.1` | review/audit/debt 模式；重复实现识别；SIMPLIFY 标记；文件/函数长度提示 `check_thresholds.py` | 400/40 等阈值改为可配置；将近似解析的误差写明；检索项目已有依赖，不必连公司 MCP；“无简化项”不等于可发布 | 扩展 `xym-dev-tools`，iOS 专项规则按需加载 |
| `wk-tmp-guard` `1.0.1` | `tmp_guard.py` 托管根、会话/slot 隔离、路径边界检查、保留标记、dry-run、过期盘点 | 默认只列计划，清理仅限自己创建且有归属证据的目录；不以 mtime 单独证明无人使用；默认不接管全局 hook；与构建日志/xcresult 的保留期协调 | 新增独立 `xym-tmp-guard` |
| `wk-visual-patch` `1.0.5` | 本地截图标注 UI、编号/坐标/意图/验收条件 JSON、按标注修改的闭环；CLI、Web、Node runtime 可跨 iOS/Web/RN 项目使用 | 独立版本和运行时；移除 wk 名称/路径绑定；保留 localhost/token 边界；校验项目和输出路径；用户请求标注才启动，不自动读剪贴板 | 新增独立 `xym-visual-patch` |
| `ios-blocked-words-hook` `1.0.1`（legacy，未登记） | 从 Edit/Write/apply_patch 结果提取变更文件，按扩展名触发检查 | 上游 README 明确是 legacy/local fallback；脚本依赖 `baitu-workshop` 缓存路径；不再单独发布一个旧 hook 插件 | 可选并入 `xym-ios-quality`，不自动改宿主设置 |

## `wk` 内 18 个 Skill 逐项盘点

| Skill | 可提炼的通用逻辑 | 适配要点 / 边界 | 建议归属 |
| --- | --- | --- | --- |
| `which` | 按用户意图定位已安装工具 | 不照搬过期的 wk 命令表；从个人市场清单维护索引；已有宿主选择器能满足时无需另造路由层 | 个人市场文档/索引，必要时才独立 Skill |
| `brainstorm` | 对实质取舍比较方案、明确验收和未知项 | 保留项目规范和用户范围，不引入与任务无关的强制审批/模型选择 | `xym-dev-tools` |
| `tdd` | 针对一个行为 RED→GREEN→REFACTOR；区分编译失败和行为失败 | 读取项目既有 XCTest / Swift Testing / OCMock；不强制引入新测试框架或统一覆盖率数值 | `xym-ios-quality` |
| `review` | 准确 scope、契约/调用链/并发/生命周期证据、结论去重 | 上轮只提炼了采集器，本轮应补完整审查工作流；iOS 重点按需加载；不强制额外模型或并发 agent | `xym-dev-tools` + 包内 iOS 参考 |
| `gh-pr-review-fix` | 线程归属、检查反馈、修复验证、授权回复/解决 | 上轮已包含完整分页/API 操作；保留代码修改、提交、推送各自授权边界 | 已有 `xym-dev-tools:github-review` |
| `dsym-crash` | `.ips` JSON、imageIndex/imageOffset、UUID/arch、dwarfdump/atos、关键业务帧 | 脚本本身即可在其他 App 使用，不要求公司服务；文本 `.crash` 需要对应解析或明确的地址模式；歧义 image/arch 不默认猜 | `xym-ios-diagnostics` |
| `crash-repro-fix` | 根因假设→可重复复现→最小修复→回归；竞态采样、超时和线程语义 | 去掉 `BTNetwork-Example`、特定测试类/宏；由目标项目选择测试入口；只诊断的请求不自动修复；DEBUG 注入不能进入发布构建 | `xym-ios-diagnostics` |
| `scan-clean-code` | 字段/方法/文件盘点、引用证据、动态调用保守分类 | 覆盖 KVC/KVO/selector/CodingKeys/IB/公开 API/跨模块调用；搜索不到只能是候选，不能自动删除 | `xym-ios-diagnostics` |
| `symbol-reference-scan` | 源码、Headers、framework/xcframework、静态库多来源检索、来源标注与去重 | 删除 `BT/PLA/Pop` 业务判定；采用用户目录/依赖归属；二进制先识别类型；命中字符串不等于运行时调用；macOS 不依赖未安装的 GNU timeout | `xym-ios-diagnostics` |
| `ios-component-reuse` | 需求拆解、查已有能力、核实 API、调用示例、迁移差异和回归 | 本地源码、Podfile.lock、Package.resolved、公开头文件先可用；组件 MCP 仅为可选提供者；没有 MCP 仍可完成有范围说明的检索 | `xym-ios-quality` |
| `sync-pb` | submodule 版本记录、生成器执行、生成 diff、校验和失败停止 | 当前明确绑定 BTProtobufMessages；submodule 路径、版本/分支、protoc/生成脚本、输出目录全部参数化；本地生成不必自动更新远端 | `xym-ios-build` |
| `lark-wiki` | 公开 API 盘点、源码验证文档、源文件/文档 hash、原始稿与润色稿分离 | `generate_api_docs.py` 来自市场外项目，不是此插件自带；需实现可独立工作的本地适配；生成文档不应自动上传或 stage，不强制 main/master | 本地 API 文档部分归 iOS 质量；上传用已有飞书插件 |
| `lark-wiki-batch` | 按组件增量跳过、失败隔离、生成成功后更新缓存、文档映射防重复 | 去掉 `mcp_app.bootstrap` 硬依赖、固定 Haiku、自动 pull/stage；缓存标识需含生成器/规则变化；是否上传与是否重生成分开判断 | 本地批量逻辑归 iOS 质量；上传复用飞书插件 |
| `okr-sync` | 从真实交付映射 KR、草稿、进展/指标回查 | 上轮已覆盖基本能力；旧版 API 命令和一律 0–100 的假设不沿用；无证据不自动给百分比 | 已有 `xym-lark-tools:lark-okr` |
| `okr-report` | 真实证据→周复盘，保持未修改字段、block/revision 回查 | 不把飞书 OKR 嵌套块降级为普通 Markdown 覆盖；需要补 XML/引用保留能力；下周计划不擅自编成承诺 | 扩展 `xym-lark-tools`，不能只靠现有 Markdown 包装器 |
| `git-commit` | 显式暂存范围、敏感信息检查、hook 结果核查、提交与推送分离 | 中文/emoji/Lore 按项目规则选择，不设为通用硬门禁；必须检查既有 staged 内容，避免带上无关变更；不自动 amend/force push | `xym-dev-tools` |
| `learn` | 从实际证据抽取项目经验、记录适用条件/反例/来源、去重 | 存储路径和 project/global 作用域由目标决定；不自动读取其他项目会话、不因一次案例提升全局规则、不凭分数自动删除 | `xym-dev-tools`，与宿主已有记忆区分 |
| `skill-create` | 从 Git 历史/经验归纳可复用流程 | 保留“历史模式提炼”这一差异能力；去掉默认写入 wk 套件及固定宿主目录；生成部分复用已有 skill-creator，不重复维护通用创建器 | `xym-dev-tools` 的经验提炼流程 |

## 不能只改名字：已定位的关键默认值

以下为静态代码/规则证据，不声称已运行复现或完成修复。

1. **staged 输入与工作区输入混用**：`plugins/ios-blocked-words-check/skills/ios-blocked-words-check/scripts/check_blocked_words.py` 的 `get_staged_files()` 在约第 379 行只取暂存文件名；`main()` 约第 675 行调用 `check_file()`，而该函数约第 310 行打开的是磁盘文件。部分暂存时两份内容可能不同。通用版应读取索引 blob 或 cached diff，并分别报告检查失败和词表命中。
2. **无设备即 Mac**：`plugins/wk-xcodebuild/scripts/xcb-run.sh` 约第 156–169 行回退 `platform=macOS`；不一定属于所选 iOS scheme 的有效目的地。通用版应区分 build/test/archive 和 scheme 支持的平台，保留用户显式 destination。
3. **插件格式优先于工程格式**：`plugins/ios-dev-rules/scripts/codex-post-tool-use.sh` 的 `find_style()` 约第 44 行优先选择插件配置，未先查目标项目的风格文件。其他项目应优先采用其已有 `.clang-format`/`.swiftformat`/lint 约束，不能安装插件就换风格。
4. **宿主缓存绑定**：同一脚本 `find_xcindent()` 约第 96 行使用 `baitu-workshop/wk-xcindent/*`；移入个人插件后不能依赖这条路径继续存在。包内共享脚本或显式配置更可移植。
5. **业务归属绑定**：`plugins/wk/skills/symbol-reference-scan/SKILL.md` 按 `BT* / PLA* / Pop*` 判业务模块，其他前缀判三方。其他项目必须改用仓库、target 和依赖目录证据，不能照搬前缀。
6. **规则不等于所有项目的要求**：`ios-dev-rules` 的语言 README 固定 Masonry/SnapKit、Swift 版本和 400/40 阈值。`wk-simplify` 的 `check_thresholds.py` 同样写死 400/40，函数跨度用花括号近似计算。应区分提示与门禁，规则由项目选择。
7. **临时目录时间不代表无人使用**：`tmp_guard.py` 的 `is_active()` 按 mtime / `.wk-keep` 保留；Skill 也明确保留标记不保护显式 purge、会话结束等操作。迁移时不能宣称它能可靠证明长时间只读任务已经结束，应增加明确归属/保留语义并默认预览。
8. **文档生成器不在插件里**：`lark-wiki` / `lark-wiki-batch` 调用外部 `mcp-ios-components/tools/generate_api_docs.py` 与 `mcp_app`。能复用的是增量工作流，不能复制几条命令就宣称已有通用 API 文档生成器。

## 建议组织方式

推荐按能力分组，而非照搬上游目录，也不把所有能力塞到一个大插件。

| 个人插件 | 内容边界 | 原因 |
| --- | --- | --- |
| `xym-ios-build`（新增） | 构建/测试/归档、Pods、结果/覆盖率、可配置 Proto 生成 | 共享工具链和日志处理；可单独安装 |
| `xym-ios-quality`（新增） | ObjC/Swift/Ruby 规则、格式检查、词表、TDD、组件复用、本地 API 文档 | 跟随项目规范，不要求公司平台；不同能力按需加载 |
| `xym-ios-diagnostics`（新增） | dSYM/地址符号化、崩溃复现、引用扫描、清理候选审计 | 以本地源码/二进制证据为主，不依赖发布系统 |
| `xym-dev-tools`（已有，扩展） | Git/GitHub、代码审查、简化、设计、提交与经验提炼 | 保留跨语言能力，不重复新建小插件 |
| `xym-lark-tools`（已有，扩展） | 文档/OKR，加周复盘和必要的结构化文档更新 | 统一飞书身份、请求与回查，避免重复 API 脚本 |
| `xym-tmp-guard`（新增，可选） | 任务临时资产盘点、保留、受控清理 | 删除策略与 hook 需独立选择，不随 iOS 开发默认启用 |
| `xym-visual-patch`（新增，可选） | 本地截图标注和修改反馈 | 带 Node/Web runtime，单独安装和验证 |

其他可行组织：

- **按上游一对一镜像**：较容易追踪上游更新，但仍要处理 wk 内部的多领域能力，重复维护与跨插件依赖较多。
- **一个总插件**：入口少，但 iOS 用户会带上飞书、Node 标注工具和临时清理策略；依赖与副作用边界不清晰。

以上是供确认的拆分建议，不是已经实现的新增能力。原 `xym-compoments-publish` 保持独立，不扩大发布权限；上轮未提交的改动保持原样。

## 后续验证需覆盖的真实场景

- UIKit + CocoaPods 工程与 SwiftUI + SwiftPM 工程分别运行，不能只用 BT Example 证明通用。
- 自定义业务前缀、空格/非 ASCII 路径、部分暂存、已有格式配置和同名工具共存。
- 工具缺失、无真机、多目标/多 scheme、仅模拟器可用、Xcode 版本差异；退出码必须准确。
- dSYM UUID/arch 匹配与不匹配、多 image 歧义、无法还原帧；不把原始地址回显当成功。
- 格式化区间、字符串/注释/宏、幂等、工作区与索引区分；检查模式不写回。
- 词表可替换、误报白名单、读取失败、proto 生成失败/无变化/输出边界。
- 临时资源越界/符号链接/运行中任务/保留标记；未经授权不清理。
- VisualPatch 默认仅本机访问、token、路径边界、运行时打包与无依赖项目启动；不访问剪贴板作为默认检测。

在没有完成这些验证前，只能报告已实现和已测试的具体能力，不能声称“适用于所有 iOS 项目”。改编时继续保留上游许可证与归属说明。
