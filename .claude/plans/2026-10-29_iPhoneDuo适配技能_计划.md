# iPhone Duo 适配技能实施计划

Created by Xuyiming on 2026/10/29.

**目标：** 交付保持原 UI 的最小侵入适配技能，每 1–3 页由独立子 Agent 审核和模拟器回归。

**架构：** 一个插件包含一个技能，以入口约束实施范围，详细参考约束布局选择和证据验收。复用宿主与项目工具，不新增业务框架或测试服务。

**技术栈：** Markdown、JSON、YAML、现有 marketplace 校验器、宿主子 Agent。

## Task 1：制作与验证插件

1. 在插件缺失状态检查市场目录，记录当前只有 9 个插件；列出验收情景：四页面任务须拆批、同文件出现无关业务改动须拒绝混入、缺普通 iPhone 基线不得给 UI 通过。
2. 创建 plugins/xym-iphone-duo-adapt 下双端 plugin.json、skills/xym-iphone-duo-adapt/SKILL.md、agents/openai.yaml、三个 references 文件和 assets/batch-review.md。示例策略：`已修正页面数 <= 3` 时派发 reviewer；结果为 `blocked` 时不进入下一批，不改成 `pass`。
3. 更新 .agents/plugins/marketplace.json、.claude-plugin/marketplace.json 和根 README，保持旧插件不变。
4. 运行 `rtk proxy python3 -B scripts/validate_marketplace.py` 和 skill-creator 的 quick_validate.py；核对所有相对引用。派发只读 reviewer 做情景试用，按实际发现修订并复验。
5. 检查定向 diff 和暂存内容，创建本次新插件提交，正常推送 origin/main。
6. 更新个人市场并安装 xym-iphone-duo-adapt@xuyiming-workshop；核对版本、启用状态、安装内容与源码一致，再关闭目标。真实业务适配回归留给指定业务工程后的技能调用，不在本次伪造通过。

## 发布前验证记录（2026-10-29）

- 双端市场校验通过：10 个插件、27 个技能；quick_validate 通过；7 处本插件相对引用、展示元数据与默认调用一致性通过。
- 现有 113 项仓库测试全部通过。首次沙箱运行因本地 HTTP 测试无法绑定回环端口中断，申请权限重跑后通过；未更改测试来跳过失败。
- 独立 reviewer `duo_skill_forward_review` 完成两个离线场景试运行：四页共享容器按影响集拆批；已知越界改动判代码 fail，缺双机型基线/交互/访问能力判 UI blocked，不放行下一批。未发现必须修正项。
- 主 Agent 读取原 PPT 与讲者备注，并结合官方网页、SDK 公开头形成引用；reviewer 独立复核关键公开 API，未独立读取 PPT。未提供业务工程，因此本次没有业务 App 的 UI 实测结论。
