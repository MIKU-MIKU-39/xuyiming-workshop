---
name: crash-symbolicate
description: "收到 Apple IPS、dSYM 或未解析崩溃帧，需要本地校验 UUID/架构并符号化时使用；不猜测镜像或上传崩溃日志。"
---

# 崩溃符号化

确认 .ips 和对应版本 dSYM 的实际本地路径。不自动下载或上传符号；路径不存在时请用户提供，不从其他版本猜。

PLUGIN_ROOT 为本技能目录（包含 SKILL.md）的 ../..：
- 列镜像：python3 "$PLUGIN_ROOT/scripts/symbolicate.py" --ips "$IPS" --dsym "$DSYM" --list-images
- 符号化：python3 "$PLUGIN_ROOT/scripts/symbolicate.py" --ips "$IPS" --dsym "$DSYM"
- 多个匹配时补充精确 --image 名称/路径/UUID 和 --arch。UUID、架构必须唯一匹配；脚本不提供强制忽略不匹配开关。

需 macOS Xcode 命令行工具（xcrun dwarfdump/atos）。支持 JSON IPS（一个 payload，可带头部对象），不支持旧文本 crash 或任意地址输入；这些情况分别检查原始格式后手工规划，不能声称脚本已覆盖。
atos 地址原样返回会标记 resolved=false；没有符号的帧不能附会源码位置。报告异常类型、触发线程、首个可信业务帧、证据与仍缺的材料。符号化只完成地址还原，不等于确定根因或授权修复。
