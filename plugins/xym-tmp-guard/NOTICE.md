# 来源与改编说明

维护者：Xuyiming。

上游 [BaiTu-iOS/workshop](https://github.com/BaiTu-iOS/workshop)，MIT，参考提交 `710f119995332658a926919ebdb7c87049020e65`。

plugins/wk-tmp-guard 的 session/slot/保留标记与范围保护思想。重新实现显式 active/complete 生命周期，不复制按 mtime 判空闲及自动 SessionEnd 删除策略。

保留上游 MIT 版权声明，新增部分同样采用 MIT。本插件不是 BaiTu-iOS、Apple 或相关服务商的官方插件；不包含公司账号、凭据、私有 API 地址或业务组件实现。
