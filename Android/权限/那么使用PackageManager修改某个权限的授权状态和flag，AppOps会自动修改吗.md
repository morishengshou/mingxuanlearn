短答：不一定自动，但常见“标准权限↔对应 AppOps”的联动通常会由系统在同一条路径里一起更新；而你绕过标准授予流程、直接改 flag/授予位，AppOps 不保证自动同步。

详解分场景：

- 通过正式授予/撤销流程
  - 用户在系统设置里授予/撤销、应用调用运行时请求被系统授予、DevicePolicyManager.setPermissionGrantState()、adb pm grant/revoke（走系统服务）等，这些路径会触发 PackageManager/PermissionManager 和 AppOps 的联动更新：
    - 相关 op 被设置为相应的 MODE（通常是 MODE_ALLOWED 或 MODE_DEFAULT/IGNORED，定位可能是 FOREGROUND 等）。
    - 厂商实现可能有细节差异，但 AOSP 中核心路径会同步更新。
  - 因此：用“正规 API 修改授予状态”时，AppOps 一般会随之调整。

- 仅修改“权限 flags”（如 USER_FIXED/POLICY_FIXED/SYSTEM_FIXED）
  - 这些 flag 只是“状态来源和可变性”的标记，本身不等同于授予与否。
  - 仅改 flag 不一定改变授予状态；也就不会必然引发 AppOps 变化。
  - 例如把某权限标记为 POLICY_FIXED=拒绝，并不会自动把 op 改成某个模式，除非你同时撤销该权限或策略通道会触发相应处理。

- 通过隐藏/内部 API 或直接改系统数据库
  - 如果你用隐藏接口直接 setPermissionFlags() 或内部结构修改，而没有走授予/撤销的标准入口，AppOps 可能不会被更新，需要你显式调用 AppOpsManager.setUidMode()/setMode() 同步调整。
  - 系统/ROM 里通常在 PermissionManagerService 中的 grant/revoke 路径会调用 AppOpsService 更新；绕过它就没有联动。

- 特例与版本差异
  - 某些权限与多个 AppOps 关联，或有前台/后台区分，系统会根据授予类型（如仅前台）设置不同的 mode（如 MODE_FOREGROUND）。
  - 厂商 ROM 或企业策略可能在策略层再次覆盖 AppOps，导致即便联动更新了，随后又被策略改回。

建议实践
- 普通第三方应用：不要尝试修改权限 flags；只能通过标准权限请求流程，系统会负责 AppOps 联动。
- 系统/企业应用：
  - 修改授予状态时尽量使用公开/系统 API 的授予入口（PermissionController/PermissionManager/DevicePolicyManager），以获得自动联动。
  - 若必须直接操作 flags，完成后请根据权限与 op 的映射，显式调整相关 AppOps（AppOpsManager.setMode/setUidMode），确保一致性。
  - 变更后用 AppOpsManager.checkOpNoThrow()/unsafeCheckOpNoThrow() 验证最终 mode。

如你提供目标权限名和 Android 版本，我可以说明它映射到哪些 AppOps 以及授予/撤销时系统默认会设置成什么 mode。