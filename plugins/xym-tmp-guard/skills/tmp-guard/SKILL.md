---
name: tmp-guard
description: "用户明确需要为任务分配、保留或清理临时目录时使用；基于所有权与显式完成状态，不按时间猜测任务结束，不安装全局钩子。"
---

# 临时任务目录保护

只管理本技能显式创建的任务槽；“清理电脑”不是递归删除所有缓存的授权。先确定专用 ROOT，必须为项目子目录或真实临时目录下的 xym-tmp，不能使用工作区本身、家目录或系统根目录。session/slot 使用简单唯一名称。
PLUGIN_ROOT 为本技能目录（包含 SKILL.md）的 ../..。所有 CLI 动作默认 preview：
`python3 "$PLUGIN_ROOT/scripts/tmp_guard.py" create --root "$ROOT" --session "$SESSION" --slot "$SLOT"`
加 --execute 创建 active 槽；生成的 .xym-owner.json 是范围证据，不能补造标记接管已有目录。放入 .keep 可明确保留。
已有未知目录时换一个唯一 slot；需要了解旧目录时只做只读检查，不补造标记接管。
只有已确认任务结束且文件不再被进程使用时才执行 complete --execute。mtime 很旧也不代表结束；不自动读取其它任务来推断。
active 只是显式状态保护，不是操作系统进程占用检测。结束后可按以下顺序调用同一组 ROOT/SESSION/SLOT：

```bash
python3 "$PLUGIN_ROOT/scripts/tmp_guard.py" complete --root "$ROOT" --session "$SESSION" --slot "$SLOT" --execute
python3 "$PLUGIN_ROOT/scripts/tmp_guard.py" clean --root "$ROOT" --session "$SESSION" --slot "$SLOT"
# 确认预览路径和不可恢复删除范围后：
python3 "$PLUGIN_ROOT/scripts/tmp_guard.py" clean --root "$ROOT" --session "$SESSION" --slot "$SLOT" --execute
```
清理前先 clean 预览完整目标，再在用户授权清理该槽后 clean --execute。active、.keep、路径链接、所有权不匹配一律拒绝，不能删标记绕过。清理为不可恢复删除；不清理 session/root 父目录，完成后告知删除的精确范围与恢复性。
工具不会安装 SessionEnd/Stop hook，不会修改全局配置。并发恶意改写目录不属于锁定保证；目标有其他写入者就暂停清理。
