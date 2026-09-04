# xuyiming-workshop

Xuyiming 的个人 Codex Plugin Marketplace。

## 首次安装

```bash
codex plugin marketplace add MIKU-MIKU-39/xuyiming-workshop && codex plugin add xym-compoments-publish@xuyiming-workshop
```

## 升级或重新安装

```bash
codex plugin marketplace upgrade xuyiming-workshop && codex plugin add xym-compoments-publish@xuyiming-workshop
```

安装完成后请新建 Codex 任务，使新 Skill 生效。发布 CocoaPods 组件时可直接提出“发布当前组件”，或显式使用 `$xym-compoments-publish`。

## 插件

- `xym-compoments-publish`：检查当前组件的增量发布信息、混淆策略与发布环境，确认后通过 Wukong 发布。
