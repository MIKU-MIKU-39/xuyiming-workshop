---
name: proto-sync
description: "需要更新项目 proto 输入、同步明确的 proto submodule 或重新生成 Protobuf 代码时使用；先检查输入版本和生成范围，不默认提交推送。"
---

# Proto 同步与生成

先从 .gitmodules、生成脚本和构建说明确定真实 proto 路径、生成器版本、输出目录及语言；不存在可靠配置时只列缺失信息，禁止套用其他项目的目录。

- “重新生成”不意味着拉取远端。“同步上游”需要用户指定来源/目标分支或确认当前 tracking 目标；先读状态与 gitlink，明确远端 URL，再单独确认并执行 fetch/checkout。禁止 reset --hard、隐式 pull、自动 stash。
- 生成前要求父仓库和输入仓库干净。记录输入 commit、父仓库 HEAD、生成器版本。检查生成脚本是否删除目录、下载执行代码或修改输出范围外文件。
- 从本技能目录（包含 SKILL.md）的 ../..得到 PLUGIN_ROOT。预览：
  `python3 "$PLUGIN_ROOT/scripts/proto_generate.py" --repo "$PROJECT" --source "已确认的proto目录" --output "已确认的生成目录" -- 已检查的生成器 参数`
- 加 --execute 才执行。--output 是审核范围，不是沙箱；脚本不会自动拉取远端。执行前重新检查输入状态；有本地改动就停，不代替用户处理。
- 对比实际新增/修改/删除文件，发现越界立即报告，不能擅自回滚。检查语言版本、头文件导入、项目 target membership、项目术语规则，运行相关编译和测试。
- 返回版本变更、输出范围、生成/验证结果。commit、push、发布分别需要用户授权，不能把“同步”扩大成发版。
