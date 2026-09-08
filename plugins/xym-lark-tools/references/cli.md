# 飞书 CLI 与接口参考

维护者：Xuyiming。核对日期：2026-09-07。使用官方 [larksuite/cli](https://github.com/larksuite/cli)，不复制企业私有凭据或绑定租户。CLI 会演进，实际执行前以本机 `--help` 验证下列能力；缺少参数时停止并说明版本差异，不静默回退旧写法。

## 依赖与身份

只读检查：`lark-cli --version`、`lark-cli auth status`。需要时用户自行完成安装、配置和授权：

```bash
npx @larksuite/cli@latest install
lark-cli config init --new
lark-cli auth login --recommend
```

安装和登录不是本插件脚本的副作用。仅在用户明确要求时协助这些操作；不索取密码、token，不读取其他应用的登录缓存。执行统一使用 `--as user`，所需 scopes 由具体接口决定，遇到不足时说明实际缺失权限。

若宿主要求 RTK，在下列命令外加 `rtk proxy` 以保持原始 JSON。使用标准库 `subprocess` 的脚本通过参数数组传递内容，不使用 `shell=True`、拼接 shell 或 `eval`。OKR 正文为 JSON 参数，可能出现在本机进程参数/计划输出中；不要把密码等凭据作为正文。

## 当前调用契约

- [文档创建](https://github.com/larksuite/cli/blob/main/skills/lark-doc/references/lark-doc-create.md)：`docs +create --doc-format markdown --content - --title ... --parent-token ...`，Markdown 通过 stdin 传入。
- [文档更新](https://github.com/larksuite/cli/blob/main/skills/lark-doc/references/lark-doc-update.md)：`docs +update --doc ... --command append|overwrite|block_replace|block_insert_after --doc-format markdown --content -`。块操作传 `--block-id`，版本前置条件传 `--revision-id`。
- [文档读取](https://github.com/larksuite/cli/blob/main/skills/lark-doc/references/lark-doc-fetch.md)：`docs +fetch --doc ... --detail full --doc-format xml` 可取得定位所需信息。分页/分段参数看本机帮助；保留引用映射。
- [创建单个 KR](https://github.com/larksuite/cli/blob/main/skills/lark-okr/references/lark-okr-create.md)：`okr +create --level key-result --objective-id ... --style simple --content '{"text":"..."}'`。
- [记录进展](https://github.com/larksuite/cli/blob/main/skills/lark-okr/references/lark-okr-progress-create.md)：`okr +progress-create --target-id ... --target-type key_result --style simple --content '{"text":"..."}'`，按需指定 progress-percent / progress-status。
- [OKR 查询与指标资源](https://github.com/larksuite/cli/blob/main/skills/lark-okr/SKILL.md)：需要详细回查时先执行 `lark-cli okr key_result.indicators list --help` 或 `lark-cli okr objective.indicators list --help`，按当前 schema 指定已经核实的目标 ID；不猜原始 API 参数名。

全部请求增加 `--as user --format json`。不再使用旧版 `--markdown-file`、`--wiki-node`、`--api-version v2` 原生参数；本包装器的 `--markdown-file` 是本地输入选项，会转换为当前命令。

## XML 与引用映射

本地包装器的 docs-fetch/create/update 都接受 `--doc-format xml`（默认 markdown）。create/update 的 `--content-file` 与旧 `--markdown-file` 是同一个输入选项。XML 更新另支持 `--reference-map-file`，读取 JSON 对象后作为独立 `--reference-map` 参数发送；正文仍从 stdin 输入。必须保存 fetch 返回的原始引用映射和块结构，不凭空生成 token。使用正整数 revision-id；0 在当前 CLI 中不发送版本前置条件，因此本包装器拒绝它。

## 业务结果

不能只看进程退出码。检查 `ok`/`code`、`data.result`、创建 ID，以及 warnings。文档 `partial_success` 即使退出码为 0 也按未完整成功处理，并提示回查，防止重试产生重复写入。外层包装器报告 executed 表示 CLI 返回了符合契约的成功响应，不代替业务回查。
