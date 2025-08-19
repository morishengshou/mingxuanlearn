在 Android 中，大多数敏感操作既受权限（manifest/运行时权限）约束，又受 AppOps（应用操作）层面的细粒度管控。但也有一些权限/能力并不由 AppOps 管控，主要包括以下几类：

1) 普通权限（protectionLevel: normal）
- 特点：安装时自动授予，无需运行时同意；通常只授予对低风险 API 的访问。
- 通常不对应任何 AppOps 项目，因此不受 AppOps 开关控制。
- 示例（随版本有所差异）：INTERNET、ACCESS_NETWORK_STATE、VIBRATE、SET_WALLPAPER、BLUETOOTH、NFC、USE_BIOMETRIC（仅作能力标记，实际生物识别走框架内部策略）等。
- 说明：INTERNET 等权限长期没有对应的 AppOps；即使在新版本中增加了网络相关 AppOps（如 ACCESS_MEDIA_LOCATION 等媒体相关），也不影响普通权限大多没有 AppOps 的事实。

2) 签名级/系统级权限，仅靠权限本身 gate 掉
- 特点：protectionLevel 为 signature / signatureOrSystem / privileged 等；只授予同签名或系统应用。
- 很多这类权限没有对应 AppOps，因其本身已经通过签名/系统地位严格限制。
- 示例：WRITE_SECURE_SETTINGS、SHUTDOWN、SET_TIME、SET_TIME_ZONE、UPDATE_APP_OPS_STATS（系统内部使用）等。
- 说明：有些高危能力既有签名权限又有 AppOps（比如 MANAGE_IPSEC_TUNNELS 在某些版本有相关 AppOps），但不少纯靠权限本身控制。

3) 安装时权限模型控制的“标志型能力”
- 特点：不是通过 AppOps，而是通过 PackageManager 的特权标志或角色（roles）/设备策略等控制。
- 示例：REQUEST_INSTALL_PACKAGES（开启未知来源安装能力）、QUERY_ALL_PACKAGES（包可见性，受查询规则/过滤器而非 AppOps 控制）、BIND_ACCESSIBILITY_SERVICE（可访问性由系统设置开关与服务白名单控制，而非 AppOps）。
- 说明：这些更多走系统设置或策略路径，不走 AppOps。

4) 受系统设置或设备策略（Device Policy）而非 AppOps 控制的能力
- 示例：
  - USE_FULL_SCREEN_INTENT（通知的全屏意图，受通知策略/重要性而非 AppOps）
  - SCHEDULE_EXACT_ALARM（Android 12+，受特殊 App 例外与电量策略，非传统 AppOps）
  - REQUEST_IGNORE_BATTERY_OPTIMIZATIONS（白名单由系统电量优化管理）
  - BIND_DEVICE_ADMIN（设备管理器，走 DPM 审批）
  - FOREGROUND_SERVICE（前台服务启动限制走调度/后台限制规则）
  - POST_NOTIFICATIONS（Android 13+ 的运行时权限，主要由通知管理器授权，不通过通用 AppOps 开关）

5) 仅框架内部校验、无对外 AppOps 映射的权限
- 特点：一些历史或内部用途权限仅在特定服务中做直接权限检查，未注册对应的 AppOps。
- 示例：READ_SYNC_SETTINGS、WRITE_SYNC_SETTINGS、SET_ALARM（旧版）、EXPAND_STATUS_BAR（部分版本直接权限检查）。

重要补充与辨析
- AppOps 覆盖面会随 Android 版本演进而变化。比如摄像头、麦克风、位置信息、通话记录、短信、传感器、剪贴板等常见高敏操作普遍存在 AppOps 项目；而网络、震动、壁纸、蓝牙基础操作等普通权限通常没有 AppOps。
- 同名不等于受控：拥有某权限不代表一定有对应的 AppOps 项。需要查看 frameworks/base/core/proto/android/app/或 appops.xml、AppOpsManager 源码以确证。
- 设备厂商定制：OEM 可能新增私有 AppOps 或把一些普通权限接入自家管控平台，因此在不同 ROM 上表现不一。
- 验证方法：
  - 通过 adb shell appops query-op 或 appops get <package> all 查看某应用的 AppOps 列表；
  - 查阅 AOSP 源码：frameworks/base/core/java/android/app/AppOpsManager.java 和 frameworks/base/core/res/res/xml/appops.xml；
  - 在目标 Android 版本的 Settings 或开发者选项中检查是否存在相应开关。

小结
- 不受 AppOps 管控的典型：大多数 protectionLevel=normal 的权限（如 INTERNET、ACCESS_NETWORK_STATE、VIBRATE、SET_WALLPAPER、BLUETOOTH 基础等）；
- 许多签名/系统专用权限（WRITE_SECURE_SETTINGS、SET_TIME 等）；
- 通过系统设置/角色/设备策略管理的能力（REQUEST_INSTALL_PACKAGES、QUERY_ALL_PACKAGES、BIND_ACCESSIBILITY_SERVICE、POST_NOTIFICATIONS 等）。
具体到某个权限是否有 AppOps，请以目标 Android 版本的 AppOpsManager 列表为准。