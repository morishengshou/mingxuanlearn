你可能想查两类“flag”，查询方式不同：

A) 权限定义的标志（PermissionInfo.flags 等）
- 含义：描述“这个权限本身”的属性（是否系统权限、软/硬限制等）。
- 查询 API：PackageManager.getPermissionInfo(...)
- 示例（Kotlin/Java 通用逻辑）：
```kotlin
val pm = context.packageManager
val pInfo = pm.getPermissionInfo("android.permission.CAMERA", 0)
val flags = pInfo.flags
val isSystem = (flags and PermissionInfo.FLAG_SYSTEM) != 0
val isSoftRestricted = (flags and PermissionInfo.FLAG_SOFT_RESTRICTED) != 0
val isHardRestricted = (flags and PermissionInfo.FLAG_HARD_RESTRICTED) != 0

val protection = pInfo.protectionLevel // normal/dangerous/signature...
```
- 适用场景：想了解该权限由谁提供、保护等级、是否受限制等。

B) 应用-权限授予状态的标志（如 FLAG_PERMISSION_USER_FIXED / POLICY_FIXED / SYSTEM_FIXED）
- 含义：描述“某个应用对某个权限”的当前授予状态，被用户或策略/系统固定等。这类标志不会出现在 PermissionInfo.flags 里。
- 官方公开 API 没有直接返回这些 flags 的整型位掩码，但有可行途径：

方法 B1. 通过 dumpsys 解析（调试/内部工具用）
- 用于开发/调试阶段，非正式应用内方案。
```kotlin
fun dumpPermissionFlags(packageName: String): String {
    val proc = Runtime.getRuntime().exec(arrayOf("sh", "-c", "dumpsys package $packageName"))
    return proc.inputStream.bufferedReader().use { it.readText() }
}
// 输出中查找权限名，后缀会带 flags，如: granted=true, flags=[ user_fixed policy_fixed ]
```

方法 B2. 使用 PackageManager 的隐藏 API getPermissionFlags
- Android 源码里有 PackageManager#getPermissionFlags(String perm, String pkg, UserHandle user)，但它是 @SystemApi/隐藏接口。普通第三方应用无法直接调用；需要系统权限或反射/hidden API 访问（会被限制，且不建议在商店应用使用）。
- 如果你在做系统应用/ROM/企业设备管理，可通过系统权限或 @SystemApi 使用：
  - 相关常量位于 PackageManager.FLAG_PERMISSION_...（多为 @SystemApi）。
  - 示例（伪代码，需系统签名/privileged 权限）：
```java
int flags = pm.getPermissionFlags(permName, packageName, UserHandle.of(userId));
boolean policyFixed = (flags & PackageManager.FLAG_PERMISSION_POLICY_FIXED) != 0;
boolean systemFixed = (flags & PackageManager.FLAG_PERMISSION_SYSTEM_FIXED) != 0;
boolean userFixed   = (flags & PackageManager.FLAG_PERMISSION_USER_FIXED) != 0;
```

方法 B3. 企业/设备管理场景下的侧面查询
- 如果你是 Device Owner/Profile Owner（MDM/EMM），可以通过 DevicePolicyManager 与 PackageManager 的政策接口间接判断：
  - 例如使用 setPermissionGrantState()/setPermissionPolicy() 之后，配合 PackageManager.checkPermission()/Context.checkSelfPermission() 和 Settings UI 状态来验证。
  - 但仍没有公开 API 直接返回“policy_fixed/system_fixed”位。

方法 B4. AppOps 辅助判断（有限）
- 某些权限映射到 AppOps 操作。你可以用 AppOpsManager.noteOp/checkOpNoThrow 查询模式（MODE_ALLOWED/ERRORED/IGNORED），但这不是权限 flag，本质不同，仅作补充信号。

实用建议
- 普通第三方应用：只能可靠地获取“是否已授予”（checkSelfPermission）与“是否应显示解释”（shouldShowRequestPermissionRationale）。无法在应用内正式读取 policy_fixed/system_fixed 这类标志。
- 系统/企业场景：使用 getPermissionFlags（@SystemApi）或解析 dumpsys。
- 调试定位：adb shell dumpsys package your.package 查看每个权限行后的 flags 列表。

如果你说明你的应用场景（普通应用/系统应用/MDM）和目标 Android 版本，我可以给出更具体的可用代码路径。