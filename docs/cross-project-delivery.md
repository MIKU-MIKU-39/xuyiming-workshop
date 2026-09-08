# Xuyiming：跨项目工具交付说明

日期：2026-09-08。依据 [前期审计](baitu-reuse-audit.md) 中用户确认的分组实现。
来源为本地 BaiTu-iOS/workshop 提交 `710f119995332658a926919ebdb7c87049020e65`。每个提炼插件保留独立 LICENSE/NOTICE，插件源码不依赖上游安装缓存。

## 插件映射

| 上游插件 | 通用部分去向 | 主要差异 |
| --- | --- | --- |
| wk-xcodebuild | xym-ios-build | Python 包装；显式目的地、Bundler、原始日志、真实退出码、结果/覆盖率 JSON |
| ios-dev-rules | xym-ios-quality | 项目规则优先；不带固定布局库/Swift 版本/公司组件规则，不启用全局 hook |
| ios-blocked-words-check | xym-ios-quality / project-terms | 自定义词表；暂存区读 index blob；不附带公司黑名单或审核保证 |
| wk-xcindent | xym-ios-quality / ios-format | 保留词法缩进核心，默认 diff；高风险语法拒绝；不宣称 Xcode 完全等价 |
| wk-simplify | xym-dev-tools / simplify | 保留证据驱动的过度设计审查，移除固定行数阈值 |
| wk-tmp-guard | xym-tmp-guard | 显式所有权、active/complete、.keep；清理默认预览；不按 mtime 猜空闲 |
| wk-visual-patch | xym-visual-patch | 本地 Python HTTP + HTML，随机令牌、固定保存目录、独立 JSON 文件；无 npm |
| wk | 下表按 18 个技能分配 | 去掉固定业务路径、强制公司 MCP、租户映射和默认推送 |

## wk 的 18 个技能

| 上游技能 | 个人市场中的入口 |
| --- | --- |
| which | README 中的插件/技能索引，不新增空路由技能 |
| brainstorm | xym-dev-tools / design-plan |
| tdd | xym-ios-quality / ios-tdd |
| review | xym-dev-tools / code-review + git-context |
| gh-pr-review-fix | xym-dev-tools / github-review |
| dsym-crash | xym-ios-diagnostics / crash-symbolicate |
| crash-repro-fix | xym-ios-diagnostics / crash-repro |
| scan-clean-code | xym-ios-diagnostics / code-cleanup |
| symbol-reference-scan | xym-ios-diagnostics / symbol-references |
| ios-component-reuse | xym-ios-quality / component-reuse |
| sync-pb | xym-ios-build / proto-sync |
| lark-wiki | xym-ios-quality / api-docs，本地文档与上传分离 |
| lark-wiki-batch | 同 api-docs，哈希增量与逐组件检查 |
| okr-sync | xym-lark-tools / lark-okr |
| okr-report | xym-lark-tools / lark-report |
| git-commit | xym-dev-tools / git-submit |
| learn | xym-dev-tools / learn-patterns |
| skill-create | 同 learn-patterns，输出可核实草稿而非自动写全局规则 |

不另复制旧 `ios-blocked-words-hook`：其通用检查能力归入 project-terms，自动 hook 不启用。
`xym-compoments-publish` 保持独立，原有发布行为与版本没有在本次改变。

## 可执行资源

- xym-dev-tools：git_context.py、github_review.py。
- xym-lark-tools：lark_api.py，新增 XML / reference-map 支持。
- xym-ios-build：ios_build.py、proto_generate.py。
- xym-ios-quality：format_code.py、objc_indent.py、term_check.py、api_index.py。
- xym-ios-diagnostics：symbolicate.py、reference_scan.py。
- xym-tmp-guard：tmp_guard.py。
- xym-visual-patch：visual_patch.py、assets/index.html。

审查、TDD、经验提炼等属于 Agent 的工作流指导，不伪装成能自动推断全部代码语义的扫描器。API 候选索引是正则辅助，不是 AST；二进制 strings 不是调用图；符号化不等于根因。所有这些边界均写入对应技能。

## 验证与授权边界

行为测试位于 tests，覆盖真实隔离 Git 状态、index/worktree 差异、格式预览/并发修改、严格 UUID/架构、API 参数、分页/业务错误、XML 引用映射、临时目录保护及本地 HTTP 鉴权/路径限制。
原生构建/测试运行、真实项目 Protobuf 生成、真实崩溃 dSYM 对照与飞书租户写入仍需在使用者自己的项目和权限下验证；离线替身测试不等于这些集成验证已经完成。

本次验证记录：

- `python3 -B -m unittest discover -s tests`：68 项通过；本地 HTTP 项需要回环监听权限。
- 本仓库双端一致性校验：8 个插件、25 个技能通过。
- Codex 官方 validate_plugin / quick_validate：8 个插件、25 个技能通过。
- Claude Code 原生 `plugin validate`：市场和 8 个插件分别通过。
- 13 个插件根目录 Python 脚本的 `--help` 均成功；标注页面 JavaScript 语法检查通过。
- 本机 SwiftFormat 0.61.0、clang-format、ObjC 缩进器对隔离样例输出预期 diff，不写回样例；样例通过本机 iOS 关键词检查。
- 构建包装器真实执行 `xcodebuild -version`，保留退出码 0 与原始日志；未据此声称实际 App 构建通过。
- 独立临时目录试用：已完成槽可清理，活动槽/.keep/未知目录保持不动；据反馈补充了路径与完整命令示例。
- 浏览器冒烟：隔离 PNG 加载成功、未框选提示正确、空标注 JSON 保存并核对文件成功。非空标注保存/越界/未知路径由本地 HTTP 测试覆盖；未把这记成完整拖拽交互测试。

临时校验依赖只安装到本次专用临时目录，不纳入插件，也不改变全局 Python/npm 环境。

源码已加入双端 marketplace 清单；这不代表已发布或安装。需要用户授权 commit/push 后，远端升级命令才会获得本次内容。本次不自动提交、推送、安装插件或启用全局 hook。
