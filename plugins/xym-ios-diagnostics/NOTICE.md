# 来源与改编说明

维护者：Xuyiming。

上游 [BaiTu-iOS/workshop](https://github.com/BaiTu-iOS/workshop)，MIT，参考提交 `710f119995332658a926919ebdb7c87049020e65`。

plugins/wk/skills/dsym-crash、crash-repro-fix、symbol-reference-scan、scan-clean-code。symbolicate.py 提炼 IPS/dwarfdump/atos 链路并重新实现严格匹配；引用脚本重新编写，去掉业务分类与外部 timeout 依赖。

保留上游 MIT 版权声明，新增部分同样采用 MIT。本插件不是 BaiTu-iOS、Apple 或相关服务商的官方插件；不包含公司账号、凭据、私有 API 地址或业务组件实现。
