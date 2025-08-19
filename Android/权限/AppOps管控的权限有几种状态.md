AppOps（应用操作）对每个操作(op)维护一个“模式”（mode），用来决定该操作当前是否被允许以及如何处理。常见模式如下（不同 Android 版本可能略有增减，但核心一致）：

- MODE_ALLOWED
  - 允许。调用通过，系统照常提供数据/能力。

- MODE_IGNORED
  - 拒绝且静默忽略。调用方通常拿到空数据/默认值或无效果，不抛显式权限错误。

- MODE_ERRORED
  - 拒绝并视为错误。调用往往会被拒绝并可能抛出 SecurityException 或返回错误码（具体取决于服务实现）。

- MODE_DEFAULT
  - 使用默认策略。通常等价于“按权限或全局默认处理”：若没有更具体的 per-app 设置，就走系统/设备默认或关联权限的授予状态。
  - 对很多危险权限来说，DEFAULT 往往意味着“遵循权限授予结果”：已授予则等同 ALLOWED；未授予则被拒（有的服务会当作 IGNORED）。

- MODE_FOREGROUND（Android 9+ 引入，用于部分位置/传感器等）
  - 仅在前台允许。应用处于前台（或前台服务满足条件）时允许，后台时视为拒绝（多表现为 IGNORED）。
  - 具体判定依赖 Activity 可见性或前台服务类型（如 location/microphone 等）。

- MODE_ALLOWED_WITHOUT_DELAY（少见，内部使用）
  - 与 ALLOWED 接近，跳过延迟/提示等处理，更多用于系统内部策略。

- MODE_UNKNOWN/无效值
  - 不常对外出现。如果你用低层 AIDL 或反射读取，遇到未识别值应按保守策略处理。

实务要点
- 模式优先于权限：即使权限已授予，若 AppOp 处于 IGNORED/ERRORED，实际操作仍会被拦截。
- DEFAULT 的语义依赖具体 op 与系统版本，建议在执行前使用 AppOpsManager.unsafeCheckOpNoThrow/noteOpNoThrow 获取实际 mode 并结合权限授予状态共同判定。
- 对“前台限定”的资源，除了检查 MODE_FOREGROUND，还要结合应用是否在前台或是否运行了带正确前台服务类型的 Foreground Service。
- OEM/企业策略可能动态切换模式；可使用 OnOpChangedListener 监听模式变化。