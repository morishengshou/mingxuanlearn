要在代码里判断“某个权限是否受 AppOps 管控（即是否存在对应的 AppOp）”，可用以下思路与做法。你是系统应用，可使用部分隐藏/系统 API 或反射获得更准确结果。

核心思路
- AppOpsManager 以“op”（如 OPSTR_FINE_LOCATION）而不是“权限名”运作。
- 多数运行时危险权限在系统里有“权限→op”的映射。
- 判断步骤：先把权限映射为 op，再检查该 op 是否存在/可用；或直接对 op 执行一次 no-op 的 note/check，看是否返回 MODE_ERRORED/抛异常。

实现方案一：使用 AppOpsManager.permissionToOp
- 适用：公开 API；user app 也能用。
- 步骤：
  1) 用 AppOpsManager.permissionToOp(String permission) 获取对应 op（返回字符串或 null）。
  2) 返回 null 基本表示没有对应 AppOp（即不受 AppOps 控制）。
  3) 若有 op，再用 noteOpNoThrow 或 unsafeCheckOpNoThrow 尝试一次，确认系统是否认这个 op。

示例（Kotlin/Java，公开 API）：
- Kotlin
  val appOps = context.getSystemService(AppOpsManager::class.java)
  val op = AppOpsManager.permissionToOp(permissionName)
  val isControlledByAppOps =
      if (op == null) {
          false
      } else {
          // 对自身包做一次 no-throw 检查
          val mode = appOps.unsafeCheckOpNoThrow(
              op,
              android.os.Process.myUid(),
              context.packageName
          )
          // 若能返回有效 mode，说明该 op 存在并受 AppOps 框架管理
          mode != AppOpsManager.MODE_ERRORED
      }

- Java
  AppOpsManager appOps = context.getSystemService(AppOpsManager.class);
  String op = AppOpsManager.permissionToOp(permissionName);
  boolean isControlledByAppOps;
  if (op == null) {
      isControlledByAppOps = false;
  } else {
      int mode = appOps.unsafeCheckOpNoThrow(op, android.os.Process.myUid(), context.getPackageName());
      isControlledByAppOps = (mode != AppOpsManager.MODE_ERRORED);
  }

说明：
- permissionToOp 覆盖常见危险权限，但对很多普通权限会返回 null。
- MODE_ERRORED 通常表示该 op 存在但当前不允许；若抛 SecurityException/IllegalArgument 等说明 op/调用不被允许，你可以用 try/catch 捕获并据此判定。

实现方案二：反射/访问隐藏 API 查询完整映射
- 适用：系统应用，目标是更完备地识别所有注册的 AppOps。
- 方式A：读取 frameworks 定义的 appops 列表（AppOpsManager 中的 sOpToSwitch / sOpNames 等隐藏数组）并进行反查。
- 方式B：直接用 IAppOpsService 接口（android.app.AppOpsManager$OnOpChangedListener 背后服务）查询。
  - 通过 ServiceManager.getService("appops") 获取 IAppOpsService binder（系统 app 可行）。
  - 使用其公开的 AIDL 方法（如 checkOperation）对任意 op 字符串试探调用，若返回 MODE_* 则该 op 有效。
- 方式C：解析系统资源 res/xml/appops.xml（AOSP 有时用于生成/声明 op），但不同版本实现差异大，建议以服务接口为准。

实现方案三：试探法（当你已知可能的 op 名）
- 若你怀疑某权限可能对应某 op（比如 CAMERA→android:camera），可直接对该 op 执行 unsafeCheckOpNoThrow/noteOpNoThrow。
- 若返回 MODE_* 而非抛“unknown op”类异常，则可以认定该 op 存在。

补充细节与坑位
- 一对多与多对一：有的权限映射到同一个“switch op”；注意 AppOps 还有“switchOp”的概念，多个具体 op 受一个总开关控制。公开 API 不直接给出映射，但 check/note 会按 switch 规则生效。
- 版本差异：permissionToOp 的覆盖集合会随 Android 版本变化。新权限（如 POST_NOTIFICATIONS）可能不走传统 AppOps。
- 普通权限与签名权限：很多 normal 或纯签名权限无 AppOp，permissionToOp 返回 null。
- 多用户/跨 uid：检查其他包时请传入其 uid 和 packageName，避免误判：
  val ai = pm.getApplicationInfo(targetPkg, 0)
  val uid = ai.uid
  val mode = appOps.unsafeCheckOpNoThrow(op, uid, targetPkg)

快速封装函数示例（Kotlin）
fun isPermissionControlledByAppOps(context: Context, permission: String, pkg: String = context.packageName): Boolean {
    val appOps = context.getSystemService(AppOpsManager::class.java)
    val op = AppOpsManager.permissionToOp(permission) ?: return false
    return try {
        val uid = if (pkg == context.packageName) android.os.Process.myUid()
                  else context.packageManager.getApplicationInfo(pkg, 0).uid
        val mode = appOps.unsafeCheckOpNoThrow(op, uid, pkg)
        // 只要能返回一个有效 MODE，就认为该 op 存在且受 AppOps 管控
        mode == AppOpsManager.MODE_ALLOWED ||
        mode == AppOpsManager.MODE_IGNORED ||
        mode == AppOpsManager.MODE_DEFAULT ||
        mode == AppOpsManager.MODE_ERRORED
    } catch (t: Throwable) {
        false
    }
}

系统应用加成
- 你可通过 binder 直接调用 IAppOpsService 的 checkOperation/unsafeCheckOperation 来绕过部分限制，从而判断任意 op 是否存在与可用。
- 也可以读取 Settings 全局/每用户数据库中 appops 的持久化表（不推荐用于判定映射，只适合调试）。

结论
- 首选 AppOpsManager.permissionToOp(permission) 判断是否存在映射；若存在，再用 unsafeCheckOpNoThrow/noteOpNoThrow 验证。
- 系统应用若需更完整与稳定的判断，可直接使用 IAppOpsService 进行检查或读取隐藏映射。