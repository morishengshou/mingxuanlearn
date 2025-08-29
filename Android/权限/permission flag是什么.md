Android 权限的 flags 通常指的是在系统中用于描述“某个权限或授权状态的附加属性/标志位”的整型位标志。它们存在于不同层面（权限声明、安装时授予、运行时授权记录、包信息等），在 Android 框架里以 bit flags 的方式表示，用以控制或描述权限的行为、来源、可见性和授予状态。

下面按常见场景归类说明（概念+常见取值示例）。注意：具体值会因 Android 版本而变化，最好参考对应版本的 AOSP 源码或 SDK 常量。

一、Manifest 声明相关（权限本身的属性）
- 权限定义位置：AndroidManifest.xml 的 <permission>、<uses-permission>。
- 结构体/类：在系统里权限会对应到 PermissionInfo、PermissionGroupInfo。
- 常见 flags（PermissionInfo.flags）：
  - FLAG_INSTALLED：表示该权限已被安装在设备上（系统内部用途）。
  - FLAG_COSTS_MONEY：使用该权限的操作可能产生费用（早期语义，现代系统基本不以此展示给用户）。
  - FLAG_HARD_RESTRICTED / FLAG_SOFT_RESTRICTED：受限制权限（例如在特定地区/合规要求下受控）。
  - FLAG_IMMUTABLY_RESTRICTED：受不可变限制（OEM/系统策略强约束）。
  - FLAG_REMOVED：权限被标记为移除（兼容旧应用）。
  - 另有 protectionLevel（非 flags 但很关键）：如 dangerous、normal、signature、signatureOrSystem（已废弃）、privileged 等，用于决定授权模型和可授予性。

二、运行时授权记录（授予状态的标志）
- 权限授予对象：单个 App 的单个权限（或权限组）的当前授权状态。
- 数据来源：PackageManager、AppOps、PermissionManager。
- 常见 flags（PackageManager 或 PermissionManager 返回的 Permission flags）：
  - FLAG_GRANT_STATE_GRANTED：已授予。
  - FLAG_GRANT_STATE_DENIED：被明确拒绝（某些接口区分拒绝类型）。
  - FLAG_USER_SET：用户手动更改过该权限的状态。
  - FLAG_USER_FIXED：用户勾选了“不再询问”，导致请求对话框不再弹出。
  - FLAG_POLICY_FIXED：由设备策略（Device Policy Manager/企业策略）强制固定。
  - FLAG_REVOKE_ON_UPGRADE：应用升级后需撤销并重新请求。
  - FLAG_SYSTEM_FIXED：系统固定（不可由用户更改）。
  - FLAG_ONE_TIME：一次性授权（Android 11+ 的“仅此次”）。
  - FLAG_AUTO_REVOKED：长期未使用自动回收（Android 11+ 的权限自动重置）。
  - FLAG_RESTRICTION_UPGRADABLE：可根据限制策略动态调整。
  - 注：具体常量名在不同类中可能是 PERMISSION_FLAG_... 或 GRANT_FLAG_...，且可能拆分到 AppOps 中表达更细粒度状态。

三、安装/授予时使用的“授予标志”（Grant Flags）
- 使用位置：安装时（PackageManager#grantRuntimePermission / setInstallReason 等）、pm 命令行、系统内部授予。
- 常见值（GRANT_FLAG_* 或 PackageManager.FLAG_PERMISSION_*）：
  - GRANT_FLAG_USER_SET / USER_FIXED：与用户决策相关。
  - GRANT_FLAG_POLICY_FIXED：由策略固定。
  - GRANT_FLAG_SYSTEM_FIXED：系统固定。
  - GRANT_FLAG_UPGRADE：随系统或应用升级流程自动授予。
  - GRANT_FLAG_ONE_TIME：一次性授权。
  - GRANT_FLAG_REVIEW_REQUIRED：需要权限审核/复核（早期安装审查模型）。

四、查询权限信息时在 PackageInfo/PackageManager 中看到的 flags
- PackageInfo.requestedPermissionsFlags（与 requestedPermissions 对应的并行数组）：
  - REQUESTED_PERMISSION_GRANTED：该权限当前是否已授予给该应用。
  - REQUESTED_PERMISSION_REQUIRED：是否为必需权限（缺失会导致安装失败，通常系统/特权场景）。
  - REQUESTED_PERMISSION_NEVER_FOR_LOCATION：位置权限合规相关标志（避免误用）。
  - REQUESTED_PERMISSION_NO_HARD_RESTRICTIONS / SOFT_RESTRICTIONS：与限制策略关联。
  - 不同 Android 版本里还会包含诸如 REQUESTED_PERMISSION_IMPLICIT 等标志。

五、AppOps 相关（与权限强关联的操作位）
- AppOps 用于在权限之上做更细粒度的准入控制（如后台/前台位置、精确/粗略位置）。
- 常见状态：MODE_ALLOWED、MODE_IGNORED、MODE_ERRORED、MODE_DEFAULT 等。
- 虽然不是“权限 flags”，但很多系统行为（特别是后台访问限制、精确位置切换、近年新增的可见性限制）最终由 AppOps 决定。你在调试授权问题时通常会同时查看权限 flags 与 AppOps。

六、用户可见的授权模式演进（帮助理解 flags 的意义）
- Android 6.0：引入运行时权限（dangerous 需要动态授予）。
- Android 10：位置权限增加“仅在使用时”。
- Android 11：一次性授权、自动重置（对应 ONE_TIME、AUTO_REVOKED 类标志）。
- Android 12：精准/模糊位置切换；蓝牙权限拆分；附近设备权限；麦克风/摄像头指示器与开关。
- 这些演进对应了新的 flags 和 AppOps 模式，用来记录用户选择与系统策略。

七、开发与调试如何查看/使用
- 代码层面：
  - PackageManager#getPackageInfo(..., GET_PERMISSIONS) 并读取 requestedPermissionsFlags。
  - Context#checkSelfPermission / ActivityResult API 获取授权状态。
  - PermissionController/PermissionManager 的查询接口（受系统权限限制）。
- 命令行：
  - pm list permissions -d -g 查看权限与分组。
  - pm dump permissions 或 dumpsys package your.package 观察权限/ops 状态与 flags。
  - appops get your.package 查看具体 AppOps。
- 日志与源码：
  - 查看 frameworks/base/core/java/android/content/pm 相关类（PermissionInfo、PackageInfo、PackageManager）。
  - PermissionManagerService、AppOpsService 在 system_server 中对 flags 的维护逻辑。

简要总结
- “权限的 flags”是对权限或授权状态的元数据标志，用 bit 位表示，用来表达：谁授予的、是否固定、是否一次性、是否被自动回收、是否受限制等。
- 它们分布在多处：PermissionInfo.flags（定义层）、requestedPermissionsFlags（请求结果层）、grant flags（授予动作层）、以及 AppOps（执行层）。
- 使用时要对照你的目标 Android 版本查常量名与含义，避免版本差异导致的误判。

如果你提供目标 Android 版本或具体 API/场景（比如你在读哪个字段、遇到什么差异），我可以给出对应版本的精确常量名和代码示例。