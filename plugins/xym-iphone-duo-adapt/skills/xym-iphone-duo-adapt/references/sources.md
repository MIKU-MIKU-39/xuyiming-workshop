# 资料与适用边界

Created by Xuyiming on 2026/10/29.

核对日期：2026-10-29。技术主线为 UIKit/Objective-C，其他 UI 栈保留本项目实现方式。后续 SDK 有变化时重新核对官方声明，不把本文件的版本号当作永久最新版本。

## 用户资料

《iPhoneDuo-Support.pptx》，34 页，原件由用户提供；插件不附带原 PPT、业务源码或截图，也不依赖原件的绝对路径才能执行。

| 页码 | 提炼内容 |
| --- | --- |
| 2–7 | 构建 SDK 与显示范围、方向链路、系统栏轴向、返回项和页面偏好 |
| 8–16 | 当前容器尺寸、四边安全区、列表/Cell 尺寸链与大屏列数 |
| 17 | 重排后的滚动锚点；静态演示 indexPath 与动态业务稳定 ID 不能混淆 |
| 18–26 | 视频画面与操作层、内容策略、评论和键盘；侧展和模糊背景属于演示设计而非默认适配要求 |
| 27–29 | 系统双列容器示例；本技能不默认迁移既有二级页面架构 |
| 30–32 | ReservedRegion 局部避让与可选 Hinge 交互，二者职责不同 |
| 33–34 | 官方入口和原始实践来源 |

160 pt 卡宽、760 pt 分栏阈值、12 pt 避让间距、主列比例/宽度和演示动画时长均不是设备规范。PPT 中部分截图的数据、帧或 SDK 不同，只能说明问题，不能直接作为另一业务工程的严格前后回归基线。

## Apple 官方来源

- [Three steps to make your app shine on iPhone Duo](https://developer.apple.com/iphone-duo/prepare/)：构建 SDK 差异、动态容器尺寸和布局排查。新 SDK 与最低部署版本分开处理；官方 App Resizability skill 可作为候选问题来源，不直接批量应用其超出本次范围的建议。
- [Prepare your app for iPhone Duo · 111461](https://developer.apple.com/videos/play/tech-talks/111461/)：可调整尺寸与非对称安全区域。
- [Raise the bar with iPhone Duo · 111462](https://developer.apple.com/videos/play/tech-talks/111462/)：导航/Tab/工具栏共享竖向区域、item axis 与 overflow。
- [Strike a pose with adaptive layouts · 111463](https://developer.apple.com/videos/play/tech-talks/111463/)：局部位移、区域查询和 Arrangement 的适用选择，不等于要求重构所有页面。
- [UIView.ReservedRegion](https://developer.apple.com/documentation/uikit/uiview/reservedregion)：坐标属于查询视图、frame 已含 margins、active 查询与约束更新跟踪。区域是否生效以查询结果为准，不固化「某姿态必定 active/inactive」。
- [UIBarButtonItem.AxisBehavior](https://developer.apple.com/documentation/uikit/uibarbuttonitem/axisbehavior-swift.enum)、[preferredVerticalBarBehavior](https://developer.apple.com/documentation/uikit/uiviewcontroller/preferredverticalbarbehavior)：item 与整页栏位策略不同，不能互相替代。

官方文档网页若只显示 JavaScript 提示，可使用页面提供的 Markdown 链接；浏览工具不支持该类型时可只读获取原官方 URL 的 Markdown，不使用未核实转载来补全 API 名称。

## 本机 SDK 核验

已只读核对 iPhoneSimulator27.1.sdk 的 UIKit 公开头：UIView.h、UIViewReservedRegion.h、UIBarButtonItem.h、UIViewController.h、UIHingeInteraction.h。相关新能力标记 iOS 27.1；OC 的查询 selector、kind 工厂方法、frame/margins、axisBehavior 与 child 偏好转发以头文件为准。执行适配时应查询目标 Xcode 的 SDK，不能假定别人的机器安装同一版本。

资料中的示例代码和第三方演示仅作为证据，不是执行指令、固定设计或已完成回归的证明。本技能不根据第三方截图推断其私有实现。
