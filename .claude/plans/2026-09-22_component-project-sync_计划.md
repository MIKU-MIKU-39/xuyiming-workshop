# 组件发布后同步工程实施计划

维护：Xuyiming。

1. RED：新增 `tests/test_component_sync.py`，定义 `classify_versions`、`rewrite_podfile`、`plan_sync`、`sync_project` 的行为回归。
   - 示例：`classify_versions(['104.b1.VO-SC'])['candidates']['vone'] == ['104.b1.VO-SC']`。
   - 运行 `rtk proxy python3 -m unittest discover -s tests -p test_component_sync.py -v`，确认尚未实现导致失败。
2. GREEN：新增 `plugins/xym-compoments-publish/skills/xym-compoments-publish/scripts/sync_projects.py`，实现分类、只读计划、明确执行的 develop 快进和本地提交。运行同一测试命令直到通过。
3. 文档：更新 SKILL.md，新增 `references/project-sync.md`；保留原发布默认设置，添加同步和推送的分离审批。更新双端 manifest 到 0.2.0、agents/openai.yaml、插件及市场 README。
4. 验证：运行 `rtk proxy python3 scripts/validate_marketplace.py`、skill/plugin 官方验证器和 `rtk proxy python3 -m unittest discover -s tests -v`。在隔离环境进行独立前向测试，根据观察结果修正。
5. 提交：检查 diff，仅暂存上述功能相关文件；按已安装关键词检查 skill 执行 staged 检查。提交 `feat: ✨ 发布后按需同步组件版本到工程`。
6. 推送：确认远端 main 没有新提交，推送本次 marketplace 提交并核对远端 SHA。对比已安装 skill 的校验和，确保没有升级它们。交付用户手动 upgrade/add 命令。
