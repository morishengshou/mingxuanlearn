简要答案
- 大体上独立，但分“UID 级”和“包级”两类设置，行为略有差别。
- 在多用户设备上，AppOps 的存储与生效是“按用户隔离”的；同一应用在不同用户下通常拥有各自的 AppOps 配置与状态。
- 但涉及 UID 维度的设置会和“用户 ID 前缀”绑定，因此看起来既独立又遵循 Android 的 multi-user UID 规则。

展开说明
- 存储与作用域
  - AppOps 配置按用户分别持久化在每个用户的数据空间中。不同 userId（如 0、10）的设置互不影响。
  - appops 的持久化文件和 Package/Settings 数据一样，位于每个用户独立的目录（具体路径实现可能随版本变化，核心是 per-user 存储）。
- 维度区分
  - 按包名设置（setMode(op, uid, packageName, mode)）：影响的是特定“用户下的该包”。换到另一个用户，即使包同名，也不会共享这条记录。
  - 按 UID 设置（setUidMode(op, uid, mode)）：这里的 uid 是“合成 uid = userId 前缀 × 100000 + appId”。因此同一个物理 APK 安装到不同用户，会有不同的 uid（不同前缀），其 AppOps 也随之独立。
- 查询/修改时的要点
  - 你必须针对正确的用户上下文和该用户下的包/uid 操作：
    - 取 uid 时用 PackageManager for user 或 Context.createContextAsUser，确保拿到该用户的 uid。
    - 跨用户操作需要 INTERACT_ACROSS_USERS 或 INTERACT_ACROSS_USERS_FULL 等系统权限。
  - 如果你错误地用 user 0 的 uid 去改 user 10 的应用，设置不会生效，查询也会错位。
- on-change 监听
  - AppOps 的监听与回调同样是按用户隔离的。对特定用户注册的监听只会收到该用户空间内的变化。
- 和权限授予的关系
  - 运行时权限授予本身也是 per-user 的；AppOps 通常与之相匹配，都是在各自用户里独立管理。
- 例外与厂商定制
  - AOSP 语义如上。部分 OEM 可能引入跨用户的策略同步（如家长/企业策略），从而在策略层面把多个用户的 AppOps 设定“联动”，但实现仍是分别写入各自用户空间。

实用示例（Java，系统应用）
- 获取特定用户的 uid 并读取/设置其 AppOps。

```java
UserHandle targetUser = UserHandle.of(10); // 目标用户，如 10
Context userCtx = context.createContextAsUser(targetUser, 0);
PackageManager pmUser = userCtx.getPackageManager();

ApplicationInfo ai = pmUser.getApplicationInfo("com.example.target", 0);
int uidForUser = ai.uid; // 注意：这是带 userId 前缀的 uid

AppOpsManager appOps = userCtx.getSystemService(AppOpsManager.class);
String op = AppOpsManager.permissionToOp(android.Manifest.permission.CAMERA); // 例：映射到 android:camera

// 查询
int mode = appOps.unsafeCheckOpNoThrow(op, uidForUser, "com.example.target");

// 修改（需要 MANAGE_APP_OPS_MODES 等系统权限）
appOps.setMode(op, uidForUser, "com.example.target", AppOpsManager.MODE_IGNORED);
```

结论
- 是的，Android 的 AppOps 在多用户环境下是“按用户隔离”的：每个用户空间有自己独立的 AppOps 配置与生效结果。确保在正确的 user 上下文与 uid 下进行查询/修改即可。