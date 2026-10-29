# 最小侵入适配要点

Created by Xuyiming on 2026/10/29.

按页面实际问题选取条目，不将本清单整体变成代码。PPT 页码与官方来源见 [资料索引](sources.md)。

## 容器、基本页面与二级页面

1. 先追踪窗口/Scene、Tab/Navigation、分页容器、子控制器到具体视图的尺寸传递，找到最靠近原因的一层修正。现有系统容器可用则保留，自定义容器不因适配而整套迁移。
2. 页面实际宽高来自当前布局容器的 `bounds`。固定屏宽宏先查定义，不能全局替换所有 UIScreen 用途；显示尺度与屏幕信息不是页面尺寸。布局随开合、旋转、窗口和系统栏变化持续更新，不能仅在初始化读一次。
3. 四边安全区分别处理，左右可能不对称。背景可铺满，前景可读内容和操作控件避让。分清哪层负责每条边及 scroll view 的 adjustedContentInset，避免父容器、安全区约束、手动 inset 重复扣减。
4. Auto Layout 保持原约束关系，必要时改锚点或常量；手写 frame 在已有 layout 回调读实时尺寸。不要每次 layout 重建所有视图或无条件 remake 全套约束。已有 layer、遮罩和渐变跟随所属 view 的实际尺寸，保持原颜色/圆角参数。
5. push/pop、present/dismiss、返回一级页、Tab 来回切换后都检查尺寸与系统栏恢复，不能只看首页。保留页面实例、选中项和业务状态，不在尺寸回调重新请求或加载业务数据。
6. Info.plist、AppDelegate、根/子导航容器的方向约束应一致；仅修改阻碍目标适配的配置。普通 iPhone 原本的方向体验不得因全局放开而无意改变。不要以 UIDevice 方向或 size class 猜机型，布局决策使用当前可用区域。

## 列表与按钮

- 表/集合/瀑布流按自己的可用宽度测量，不再从全局屏幕重复推算；容器 frame、列宽、Cell 内部约束和必要的布局失效应形成同一条尺寸链。
- 普通 iPhone 保留原列数、间距和卡片形态。大屏是否增加列数以现有设计和实际拉伸问题决定，不能盲目放大卡片或套用固定断点。涉及半折网格时按实际 division 区域检查跨折痕项，不能假定偶数列自动解决所有遮挡。
- Texture 的异步测量沿用传入的 constrainedSize，不在后台测量中访问 UIView。系统列表项尺寸变化后使用现有机制重排，不顺带更换布局框架。
- 转场应保持用户正在看的内容。若重排导致实际跳动，再沿用项目的稳定标识和布局完成时机恢复锚点；不能拿静态 Demo 的 indexPath 方案强套实时更新列表，也不新增全局状态恢复框架。
- 控件保留原字体、颜色、尺寸、圆角、间距、图标与点击逻辑。修正位置/约束，不靠缩小点击区域、隐藏文案或覆盖其他内容解决冲突。同时检查视觉 frame 和命中区域。

## TabBar、NavigationItem 与系统栏

- iOS 27.1 SDK 构建会启用新的栏位行为，与最低系统版本分开看。优先让既有 UINavigationController/UITabBarController 管理系统栏；独立拼装的 UINavigationBar/UITabBar 不能假定会自动加入系统竖栏。
- `axisBehavior` 是单个 UIBarButtonItem 的轴向策略。`HorizontalOnly` 在没有横栏时可能不显示；`VerticalPreferred` 支持两种轴且偏好竖向，不保证所有姿态都有竖栏。默认策略可用就不要重复设置。
- 返回操作仍保持 leading 语义及原有 pop/dismiss 行为；不要通过 left/rightBarButtonItem 或硬编码右侧宽度强搬整个系统栏。原按钮缺少竖向表示时才补必要表示，尽量复用原图标与标题。
- `preferredVerticalBarBehavior` 决定页面/容器的栏位偏好，`childViewControllerForPreferredVerticalBarBehavior` 决定向哪个子页取偏好。先检查现有转发链；不要新增一个无效 override，也不要为局部按钮问题全局禁用竖栏。
- 标题、customView、搜索、工具栏、overflow、已选 Tab 和返回按钮都要验证可见与可操作。必要时为既有自定义操作提供系统支持的菜单表示；不能让重要操作在竖栏中悄悄消失。系统栏在哪侧以实际环境为准。

## ReservedRegion

在确有局部内容跨折痕或相机遮挡的自定义布局处使用，已有系统容器能够处理时不叠加重复避让。区分 `.division`（分隔）和 `.occlusion`（遮挡）。列表/scroll view 不会天然把每个条目分到折痕两侧。

本机 27.1 SDK 的 Objective-C 公开入口为 `reservedRegionsOfKind:` / `reservedRegionsOfKind:options:`，kind 使用 `UIViewReservedRegionKind.divisionRegionKind` 或 `.occlusionRegionKind`；Swift 使用 `reservedRegions(kind:options:)`。按项目实际 SDK 编译与部署范围做可用性处理，不用私有 selector、反射或手造区域来兼容缺失 SDK。

区域 frame 使用查询 view 的坐标、单位为 pt，已经包含 margins。与被移动内容在同一坐标系比较，不重复添加系统 margins。默认查询 active 区域；仅确实需要 inactive 信息时使用 IncludeInactive，并按 `isActive` 决定当前避让。不要用设备姿态代替区域状态判断，也不要假定只会有一条竖折痕。

在负责布局的 view 中查询；UIKit 可追踪 `updateConstraints` 中读取的区域并在变化后重新调用。根据原始未避让布局计算本次最小位移/约束，不拿上次移动后的 frame 继续累计。移开后仍需处于可用区域，不能只避开折痕却挤出屏幕；inactive 后回到原布局。支持实际遇到的横向/纵向分隔，保留原有动效风格和减少动态效果约定。

UIHingeInteraction 用于确需物理角度/状态的业务交互，不是普通布局避让的前置条件。多栏/Arrangement 只在既有两个内容区确有需要且用户批准时引入，不默认把所有二级页改成分栏。

## 视频、直播与输入

- 播放画面与操作层分开布局：沿用原播放器，更新 layer/frame 或现有约束；交互、字幕和浮层遵循实际安全区域。
- 是否从 Fill 改成 Fit 取决于宽容器中主体是否被不合理裁掉及原内容策略，不全局切换，也不新增模糊背景、特效或播放器实现。
- 评论面板默认保留原呈现方式，只修遮挡和尺寸问题；侧边评论或双列设置属于额外产品布局，不能因为 PPT 展示了就自行引入。
- 使用现有键盘避让；需要时接入公开 keyboardLayoutGuide，而非固定键盘高度。开合/旋转/评论开关前后验证视频索引、播放/暂停位置、选中项、草稿、滚动位置，不为测试篡改生产业务状态。
