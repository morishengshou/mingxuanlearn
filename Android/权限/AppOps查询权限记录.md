下面给出在系统应用中，使用 Java 通过 AppOpsManager 查询敏感权限（AppOps）历史记录的可行做法、前提条件、关键 API、示例代码与注意事项。由于“历史记录”能力涉及隐私与性能，Android 不同版本差异较大，且很多接口为系统/隐藏 API，仅系统应用或持有相应权限的应用才能调用。

重要前提
- 仅系统应用或具有相应签名权限的应用可用。常见需要的权限：
  - android.permission.GET_APP_OPS_STATS（系统权限）
  - android.permission.PACKAGE_USAGE_STATS（有时与历史/统计相关）
  - android.permission.INTERACT_ACROSS_USERS / INTERACT_ACROSS_USERS_FULL（跨用户/工作资料场景）
  - 查询指定包时需要 PACKAGE_USAGE_STATS 或特定 AppOps 权限
- 设备需是系统镜像或已将应用以 Privileged App 安装到 /system/priv-app，并具有相应权限授予。
- 厂商 ROM 可能裁剪或限制 AppOps 历史接口。

关键概念
- AppOps 与权限并非完全一一对应。权限在运行时授予/拒绝，而 AppOps 记录具体“操作”（op），如 android:camera、android:record_audio、android:fine_location 等。
- 历史记录 vs 近期访问：有的版本只提供“最近访问”与“统计”，真正的“历史”可能依赖内部接口或历史持久化配置。
- 自 Android 10+ 起，AppOpsManager 增加了 OnOpNotedCallback（op noted/started/finished 回调），可实时获知访问，但历史检索 API 在 AOSP 中多为系统隐藏接口。

可用路径概览
1) 实时/近实时监听（推荐，最稳定）
   - 使用 AppOpsManager.setOnOpNotedCallback 注册回调，监听敏感操作访问事件，自己落库形成历史。
   - 适合从现在开始构建自有历史。

2) 读取近期访问（公共 API 较少且受限）
   - 某些版本可通过 AppOpsManager.unsafeCheckOpNoThrow() 或 checkOp… 读取当前状态，但不是历史。
   - UsageStatsManager 可提供前后台与应用使用时段，但不是直接的敏感权限访问。

3) 系统/隐藏 API 查询历史（仅系统且需反射/系统 SDK）
   - AOSP 中存在历史查询接口与 NoteOp collections，但大多为 @hide。系统应用可用反射或使用系统 SDK（platform SDK / system server context）调用，如 getHistoricalOps 等。
   - 需要 GET_APP_OPS_STATS，并可能需要 MANAGE_APP_OPS_MODES。

示例：实时监听敏感操作并自行记录（适配性强）
- 适用于 Android 10（API 29）及以上，系统应用可收到更多细节。你可以监听诸如 ACCESS_FINE_LOCATION、RECORD_AUDIO、CAMERA 等操作。

```java
public class AppOpsMonitor {
    private final Context context;
    private final AppOpsManager appOps;
    private final Executor executor = Executors.newSingleThreadExecutor();

    public AppOpsMonitor(Context ctx) {
        this.context = ctx.getApplicationContext();
        this.appOps = (AppOpsManager) context.getSystemService(Context.APP_OPS_SERVICE);
    }

    @RequiresApi(api = Build.VERSION_CODES.Q)
    public void start() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;

        AppOpsManager.OnOpNotedCallback callback = new AppOpsManager.OnOpNotedCallback() {
            @Override
            public void onNoted(@NonNull SyncNotedAppOp op) {
                handleOp("NOTED", op.getOp(), op.getAttributionTag(), op.getUid(), op.getPackageName(), System.currentTimeMillis(), null);
            }

            @Override
            public void onSelfNoted(@NonNull SyncNotedAppOp op) {
                handleOp("SELF_NOTED", op.getOp(), op.getAttributionTag(), op.getUid(), op.getPackageName(), System.currentTimeMillis(), null);
            }

            @Override
            public void onAsyncNoted(@NonNull AsyncNotedAppOp op) {
                handleOp("ASYNC_NOTED", op.getOp(), op.getAttributionTag(), op.getUid(), op.getPackageName(), System.currentTimeMillis(), op.getMessage());
            }
        };

        appOps.setOnOpNotedCallback(executor, callback);
    }

    private void handleOp(String type, String op, String attributionTag, int uid, String pkg, long ts, String msg) {
        // 将事件写入你自己的存储（Room/SQLite/Proto/文件）
        // 也可过滤仅关心的敏感操作：
        // CAMERA, RECORD_AUDIO, ACCESS_FINE_LOCATION, ACCESS_BACKGROUND_LOCATION, READ_SMS, READ_CALL_LOG 等
        Log.d("AppOpsMonitor", type + " op=" + op + " uid=" + uid + " pkg=" + pkg
                + " attr=" + attributionTag + " t=" + ts + " msg=" + msg);
    }

    public void stop() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.setOnOpNotedCallback(null, null);
        }
    }
}
```

说明
- 该方式不会“回溯”历史，只能从注册后开始记录。优点是稳定、依赖公共 API，无需反射。
- 对于系统应用，可以更完整地收到跨包的回调；普通应用通常只能收到自身进程的 callback。

示例：查询历史记录（系统/隐藏 API，仅系统环境）
- AOSP 中存在 AppOpsManager.getHistoricalOps 等 API（在不同版本中可能为 @SystemApi 或 @hide）。在非 SDK 接口上，需反射调用并且持有 GET_APP_OPS_STATS 权限。
- 注意：不同 Android 版本签名、参数类型、时间单位和筛选条件可能不同，需做版本分支与容错。

下面给出一个“可能的”反射示例思路（需你根据目标 ROM 的具体 API 调整）：

```java
@SuppressLint({"SoonBlockedPrivateApi", "DiscouragedPrivateApi"})
@WorkerThread
public static Object queryHistoricalOps(Context context,
                                        String packageName,
                                        int uid,
                                        List<String> opNames,
                                        long beginMillis,
                                        long endMillis,
                                        int flags) throws Exception {
    AppOpsManager appOps = (AppOpsManager) context.getSystemService(Context.APP_OPS_SERVICE);

    // 在部分版本中，存在内部类 HistoricalOpsRequest 或 builder 模式
    // 这里尝试直接反射 getHistoricalOps(String pkg, int uid, List<String> opNames, long begin, long end, int flags)
    Method m = AppOpsManager.class.getDeclaredMethod(
            "getHistoricalOps",
            String.class, int.class, List.class, long.class, long.class, int.class
    );
    m.setAccessible(true);

    // flags 示例：可能包含
    // AppOpsManager.HISTORICAL_FLAG_GET_ATTRIBUTIONS
    // AppOpsManager.HISTORICAL_FLAG_GET_OPS
    // 这些常量在隐藏 API 中，需通过反射取值或用整数常量
    Object result = m.invoke(appOps, packageName, uid, opNames, beginMillis, endMillis, flags);

    return result; // 返回类型通常为 HistoricalOps
}
```

解析结果对象（示例）
- 返回类型一般为 android.app.AppOpsManager$HistoricalOps 或相关结构，内部还包含 HistoricalPackageOps、HistoricalAttributionOps、HistoricalOp。
- 你需要通过反射遍历，如：
  - HistoricalOps.getBeginTimeMillis() / getEndTimeMillis()
  - HistoricalOps.getPackageOps()
  - HistoricalPackageOps.getPackageName(), getUid(), getOps()
  - HistoricalOp.getOp(), getAccessCount(), getRejectCount(), getAccessDuration(), getForegroundAccessCount() 等
- 不同版本字段/方法名会有差异，需 try-catch 兼容。

示例：遍历 HistoricalOps（伪代码，反射）
```java
private static void dumpHistoricalOps(Object historicalOps) throws Exception {
    Class<?> clsOps = Class.forName("android.app.AppOpsManager$HistoricalOps");
    Method getPkgs = clsOps.getDeclaredMethod("getPackages");
    getPkgs.setAccessible(true);
    List<?> pkgOpsList = (List<?>) getPkgs.invoke(historicalOps);

    Class<?> clsPkg = Class.forName("android.app.AppOpsManager$HistoricalPackageOps");
    Method getPkgName = clsPkg.getDeclaredMethod("getPackageName");
    Method getOpEntries = clsPkg.getDeclaredMethod("getOps");
    getPkgName.setAccessible(true);
    getOpEntries.setAccessible(true);

    Class<?> clsOp = Class.forName("android.app.AppOpsManager$HistoricalOp");
    Method getOpName = clsOp.getDeclaredMethod("getOp");
    Method getAccessCount = clsOp.getDeclaredMethod("getAccessCount");
    Method getRejectCount = clsOp.getDeclaredMethod("getRejectCount");
    getOpName.setAccessible(true);
    getAccessCount.setAccessible(true);
    getRejectCount.setAccessible(true);

    for (Object pkgOps : pkgOpsList) {
        String pkg = (String) getPkgName.invoke(pkgOps);
        List<?> ops = (List<?>) getOpEntries.invoke(pkgOps);
        for (Object op : ops) {
            String opName = (String) getOpName.invoke(op);
            long access = (long) getAccessCount.invoke(op);
            long reject = (long) getRejectCount.invoke(op);
            Log.d("HistoricalOps", pkg + " op=" + opName + " access=" + access + " reject=" + reject);
        }
    }
}
```

敏感操作名称参考
- AppOps 常见敏感 op：
  - android:camera
  - android:record_audio
  - android:coarse_location
  - android:fine_location
  - android:read_contacts
  - android:read_call_log
  - android:read_sms
  - android:body_sensors
- 你可以用 AppOpsManager.opToName(AppOpsManager.OP_CAMERA) 等转换常量为名称（公共 API）。

权限与授予
- 在系统镜像中，将权限放入清单并由系统预装授予：
  - <uses-permission android:name="android.permission.GET_APP_OPS_STATS" />
  - <uses-permission android:name="android.permission.MANAGE_APP_OPS_MODES" />
  - <uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" />
- 对于 PACKAGE_USAGE_STATS，仍需 Settings > Usage Access 授权，但系统应用可由设备初始化脚本授予或使用 DeviceConfig/adb 授权。

兼容性建议
- 首选用 OnOpNotedCallback 实时记录，稳定可控。
- 如必须读取既有历史，确认目标 Android 版本/ROM 是否实现并开放 HistoricalOps 相关接口；用反射并做好降级。
- 提供开关与采样，避免性能问题；历史查询可能较重。
- 注意分用户/工作资料：传入正确的 uid（UserHandle.getUid(userId, appUid)）。

调试与验证
- 使用 adb shell cmd appops 命令查看/验证：
  - adb shell cmd appops query-op android:camera --mode allow --user 0
  - adb shell cmd appops get <package> [user]
  - 部分 ROM 提供 history/summary 子命令（非标准）。
- 打开开发者选项的“显示应用访问权限的通知”或系统权限访问日志，辅助验证。

如果你能提供具体目标 Android 版本（例如 AOSP 12/13/14）和设备/ROM 信息，我可以给出更精确的反射签名与 flags 取值示例。