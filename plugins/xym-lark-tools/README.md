# Xym Lark Tools

Xuyiming 维护的飞书公共调用插件，版本 `0.1.0`。

| 技能 | 能力 |
| --- | --- |
| `lark-docs` | 读取文档、在明确的父节点下新建 Markdown 文档、追加和按块更新 |
| `lark-okr` | 核实身份/周期/目标、创建单个 KR、记录进展、按需更新指标值 |
| `lark-report` | 周报草稿、保留 OKR 嵌套结构的 XML 按块更新与版本保护 |

三个技能共用 `scripts/lark_api.py`，包内不含租户配置、员工 ID、文档映射或 token。默认只生成本地 JSON 计划；`--execute` 才调用用户自己的 `lark-cli`。这是 CLI 技能插件，不是 MCP 服务。

## 安装与调用

推送到市场远端后，通过已添加的 `xuyiming-workshop` 安装：

```bash
codex plugin marketplace upgrade xuyiming-workshop
codex plugin add xym-lark-tools@xuyiming-workshop
```

Claude Code 使用 `claude plugin install xym-lark-tools@xuyiming-workshop --scope user`。

- Codex：“使用 $lark-docs 将这份 Markdown 追加到指定文档，先预览。”
- Codex：“使用 $lark-okr 为这个 KR 整理进展，先核对周期和指标。”
- Claude Code：`/xym-lark-tools:lark-docs` 或 `/xym-lark-tools:lark-okr`。

## 依赖与直接运行

本地预览仅需 Python 3.9+；实际请求还需要官方 `@larksuite/cli` 的 `lark-cli`，完成用户身份登录并具备目标权限。安装和登录不自动执行，见 [CLI 参考](references/cli.md)。

在插件根目录运行：

```bash
python3 scripts/lark_api.py docs-create --title "发布说明" --parent-token VERIFIED_PARENT --markdown-file ./draft.md
python3 scripts/lark_api.py docs-update --doc VERIFIED_DOC --markdown-file ./draft.md
python3 scripts/lark_api.py okr-create-kr --objective-id 123456789 --text-file ./kr.txt
python3 scripts/lark_api.py okr-progress --target-id 123456789 --target-type key_result --text-file ./progress.txt
```

这些 ID 是占位示例，执行前必须替换为查询核实的 ID。文档更新默认 append，全文 overwrite 需明确授权。百分比/指标值只有显式指定 `--percent` 才修改；不设置评分和权重。

包装器支持 `--doc-format markdown|xml`，`--content-file` 与原 `--markdown-file` 是本地输入别名。XML 更新可用 `--reference-map-file` 传入读取到的 JSON 引用映射，配合 `--block-id` 和正整数 `--revision-id`；不会自动创建或上传图片附件，也不封装所有飞书 API。复杂文档优先按块更新并回查，预览会显示正文和引用映射，不要输入凭据。

## 验证范围

命令契约已对照官方 CLI 文档/代码核查；离线测试覆盖参数构造、JSON、数值校验、默认预览、业务错误、部分成功和写入超时不重试。当前开发机器未安装 `lark-cli`，未进行租户真实请求联调，不能将离线测试当成账户权限验证。

CLI 更新或租户权限差异可能影响执行；执行前核对 `--help`，执行后读取远端确认。失败不自动改为新建，不自动扩大 OAuth 权限。

来源及许可见 [NOTICE.md](NOTICE.md) 和 [LICENSE](LICENSE)。
