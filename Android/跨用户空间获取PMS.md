在 Android 多用户环境下，不同用户有各自的独立应用和数据空间。要在 U0（owner/系统主用户）之外访问其他用户空间的 PackageManager（比如查询另一个用户里安装的包），需要同时满足权限前提，并使用带用户上下文的 API 获取对应用户的 Context/PackageManager。

关键点与做法如下：

1) 权限与前提
- 你的应用必须是系统应用或持有相应特权权限，普通第三方应用无法跨用户枚举/访问其他用户的安装信息。
- 典型需要的权限：
  - INTERACT_ACROSS_USERS 或 INTERACT_ACROSS_USERS_FULL
  - QUERY_ALL_PACKAGES（如果要无约束查询包）
  - MANAGE_USERS（某些用户相关操作）
- 这些多为 signature|privileged 级别，需预装到 /system/priv-app 且与平台签名一致，或通过企业设备管理（Device Owner/Profile Owner）途径间接获得能力。

2) 通过 createPackageContextAsUser / createContextAsUser 获取其他用户的 PackageManager
- 从 API 24+ 可使用：
  - Context#createPackageContextAsUser(String packageName, int flags, UserHandle user)
  - Context#createContextAsUser(UserHandle user, int flags)
- 拿到对应用户的 Context 后，调用 getPackageManager() 即可得到该用户视角的 PackageManager。

示例（Kotlin）：
```kotlin
@SuppressLint("WrongConstant")
fun getPmForUser(context: Context, userId: Int): PackageManager {
    val userHandle = android.os.UserHandle.of(userId)
    // flags 通常用 0；如果需要忽略安全限制可能需要特权
    val userContext = context.createContextAsUser(userHandle, /* flags = */ 0)
    return userContext.packageManager
}
```

示例（Java）：
```java
public static PackageManager getPmForUser(Context context, int userId) {
    UserHandle userHandle = android.os.UserHandle.of(userId);
    Context userContext = context.createContextAsUser(userHandle, 0);
    return userContext.getPackageManager();
}
```

3) 备用：使用 Context#createPackageContextAsUser
- 如果你只需要以“某个包”的身份在目标用户下创建上下文：
```kotlin
val userHandle = UserHandle.of(userId)
val pkgContext = context.createPackageContextAsUser(
    context.getPackageName(), 0, userHandle
)
val pm = pkgContext.packageManager
```
- 对同一应用在不同用户的实例特别有用。

4) 直接使用跨用户 PackageManager API（系统/设备管理员场景）
- 某些接口支持传入 userId，例如：
  - PackageManager#getInstalledPackagesAsUser(flags, userId)（隐藏/系统 API，或通过 PackageManager Hidden API 在 AOSP/系统进程可用）
  - IPackageManager AIDL（系统进程层），需系统权限。
- 企业管理（DevicePolicyManager）下，可以通过 DPC 提供的接口间接查询/安装到特定用户/工作配置文件。

5) 检查是否具备权限并处理异常
- 在没有相应权限时，createContextAsUser 会抛出 SecurityException，或者返回的 PackageManager 在访问跨用户数据时失败。
- 建议：
```kotlin
try {
    val pm = getPmForUser(context, targetUserId)
    // 使用 pm 执行查询，如 pm.getApplicationInfo(pkg, 0)
} catch (se: SecurityException) {
    // 记录并提示缺少 INTERACT_ACROSS_USERS(_FULL) 或相关权限
} catch (e: Exception) {
    // 其他异常处理
}
```

6) 获取可用的用户列表
- 需要 MANAGE_USERS 或通过 UserManager 的受限方法：
```kotlin
val um = context.getSystemService(UserManager::class.java)
val users: List<UserHandle> = um.userProfiles // 受限，仅返回与当前用户相关的
// 系统/特权可用 getUsers() 等更广方法（隐藏 API）
```

7) Q+ 的额外限制
- Android 10+ 强化了包可见性与跨用户访问限制。你可能还需要：
  - 在 manifest 中声明 queries 或使用 QUERY_ALL_PACKAGES
  - 针对特定包名用 <queries> 白名单
- 没有这些声明，哪怕拿到目标用户的 PM，也可能返回空结果或抛异常。

简要结论
- 普通应用无法直接获取其他用户空间的 PackageManager。
- 若你是系统/预装/企业管理应用，使用 createContextAsUser(UserHandle.of(targetUserId), 0).getPackageManager() 是推荐方式；务必具备 INTERACT_ACROSS_USERS(_FULL) 等权限，并根据平台版本满足包可见性要求。