下面给出一个可运行的系统应用 Demo，用 onOpChanged 监听 AppOps 模式变化，并在变化时打印日志，显示“哪个应用的哪个 op 发生了怎样的变化”。说明与代码基于公开 API，要求你的 App 具备系统级权限并作为系统/priv-app 部署。

要点与限制
- AppOps 的监听是按 op 注册的。想监听“所有 op”，需要对每个已知的 op 注册一次监听，或注册针对某个包名的通配监听。
- 从 Android 10 起，AppOpsManager 提供 startWatchingMode(String op, String packageName, OnOpChangedListener listener, int flags)（不同版本签名略有差异）。我们使用公开重载：
  - startWatchingMode(String op, String packageName, AppOpsManager.OnOpChangedListener listener)
- 仅当系统或特权应用，并且具备 GET_APP_OPS_STATS 权限时，才能稳定接收到回调。
- 回调只告诉你“哪个包、哪个 op 变了”。要知道“变更前/后”的 mode，需要在回调里主动查询当前 mode，并可维护本地快照做差异对比。

所需权限（系统/priv-app）
- android.permission.GET_APP_OPS_STATS
- android.permission.QUERY_ALL_PACKAGES（用于枚举已安装应用以初始化快照，按需）
- 可选：INTERACT_ACROSS_USERS_FULL（若跨用户监听/查询）
- 如需后续调用 setMode 等再加 MANAGE_APP_OPS_MODES（本 Demo 仅监听不需要）

AndroidManifest.xml
```xml
<manifest package="com.example.appopswatcher" xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.GET_APP_OPS_STATS"/>
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"/>
    <!-- 如需跨用户请添加：
    <uses-permission android:name="android.permission.INTERACT_ACROSS_USERS_FULL"/>
    -->
    <application
        android:label="AppOps Watcher"
        android:allowBackup="false">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
```

核心思路
- 维护一份“已知 op 字符串列表”。建议至少覆盖常见敏感项；也可以用反射枚举，但这涉及 @hide，不推荐。我们内置一组 AOSP 常见 op 名称（字符串形式，如 "android:camera"）。
- 为每个 op 调用 startWatchingMode(op, null, listener)；packageName 传 null 表示监听所有包该 op 的变化。
- 在 onOpChanged(op, packageName) 里：
  - 获取该包对应 uid；
  - 使用 unsafeCheckOpNoThrow(op, uid, packageName) 查询当前 mode；
  - 打印日志；
  - 可将“旧值 -> 新值”记录到内存 Map 中，打印差异。

Java 代码（完整 Demo）
MainActivity.java
```java
package com.example.appopswatcher;

import android.app.AppOpsManager;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.ArrayMap;
import android.util.Log;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

public class MainActivity extends AppCompatActivity {

    private static final String TAG = "AppOpsWatcher";

    private AppOpsManager appOps;
    private TextView logView;

    // 维护一个快照：key = packageName + "|" + op，value = mode
    private final Map<String, Integer> modeSnapshot = new ArrayMap<>();

    // 常见 op 列表（字符串），仅示例，实际可按需要增减
    // 注：使用字符串是公开方式；不要依赖 @hide 的整型常量
    private static final List<String> OPS = Arrays.asList(
            // 摄像头/麦克风/传感器
            "android:camera",
            "android:record_audio",
            "android:body_sensors",
            "android:phone_call_microphone",
            "android:phone_call_camera",
            // 位置
            "android:fine_location",
            "android:coarse_location",
            "android:background_location",
            // 存储
            "android:read_external_storage",
            "android:write_external_storage",
            // 通讯录/日志
            "android:read_contacts",
            "android:write_contacts",
            "android:read_call_log",
            "android:write_call_log",
            "android:read_sms",
            "android:write_sms",
            "android:receive_sms",
            "android:send_sms",
            // 通知/悬浮窗
            "android:post_notification",
            "android:system_alert_window",
            // 网络/标识符
            "android:read_phone_state",
            "android:request_install_packages",
            // 媒体
            "android:audio_playback",
            "android:audio_capture",
            // 近似完整列表很多，这里只列常见敏感 op
            // 你可以根据设备版本补充更多 op 字符串
            "android:access_media_location"
    );

    private final AppOpsManager.OnOpChangedListener listener = new AppOpsManager.OnOpChangedListener() {
        @Override
        public void onOpChanged(String op, String packageName) {
            if (TextUtils.isEmpty(op) || TextUtils.isEmpty(packageName)) {
                appendLog("onOpChanged: op or package is empty");
                return;
            }
            try {
                int uid = getUidForPackage(MainActivity.this, packageName);
                int mode = appOps.unsafeCheckOpNoThrow(op, uid, packageName);
                String key = key(packageName, op);
                Integer old = modeSnapshot.put(key, mode);
                String msg = "AppOps changed: pkg=" + packageName
                        + ", op=" + op
                        + ", mode=" + modeToString(mode)
                        + (old != null ? (" (was " + modeToString(old) + ")") : " (first seen)");
                Log.i(TAG, msg);
                appendLog(msg);
            } catch (Exception e) {
                String err = "onOpChanged error for pkg=" + packageName + ", op=" + op + " -> " + e;
                Log.w(TAG, err);
                appendLog(err);
            }
        }
    };

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        appOps = getSystemService(AppOpsManager.class);

        // 简单的日志视图
        ScrollView sv = new ScrollView(this);
        logView = new TextView(this);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        logView.setPadding(pad, pad, pad, pad);
        logView.setText("AppOps Watcher started...\n");
        sv.addView(logView);
        setContentView(sv);

        // 注册监听
        registerAllOpWatchers();

        // 可选：初始化快照（扫描当前已安装应用）
        initializeSnapshot();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        unregisterAllOpWatchers();
    }

    private void registerAllOpWatchers() {
        for (String op : OPS) {
            try {
                // packageName 传 null 代表监听所有包该 op 的变更
                appOps.startWatchingMode(op, null, listener);
                appendLog("startWatchingMode OK for op=" + op);
            } catch (Throwable t) {
                appendLog("startWatchingMode FAILED for op=" + op + " -> " + t);
                Log.w(TAG, "startWatchingMode fail: " + op, t);
            }
        }
    }

    private void unregisterAllOpWatchers() {
        try {
            appOps.stopWatchingMode(listener);
            appendLog("stopWatchingMode called");
        } catch (Throwable t) {
            Log.w(TAG, "stopWatchingMode fail", t);
        }
    }

    // 初始化快照，遍历设备应用并记录当前 mode（仅做参考，可能较慢，可放后台线程）
    private void initializeSnapshot() {
        new Thread(() -> {
            try {
                PackageManager pm = getPackageManager();
                for (android.content.pm.PackageInfo pi :
                        pm.getInstalledPackages(PackageManager.GET_PERMISSIONS)) {

                    String pkg = pi.packageName;
                    int uid;
                    try {
                        uid = getUidForPackage(MainActivity.this, pkg);
                    } catch (Exception e) {
                        continue;
                    }
                    for (String op : OPS) {
                        try {
                            int mode = appOps.unsafeCheckOpNoThrow(op, uid, pkg);
                            modeSnapshot.put(key(pkg, op), mode);
                        } catch (Throwable ignored) {
                        }
                    }
                }
                appendLog("Snapshot initialized. tracked entries=" + modeSnapshot.size());
            } catch (Throwable t) {
                appendLog("Snapshot init error: " + t);
                Log.w(TAG, "Snapshot init error", t);
            }
        }, "snapshot-init").start();
    }

    private static int getUidForPackage(Context ctx, String packageName) throws PackageManager.NameNotFoundException {
        ApplicationInfo ai = ctx.getPackageManager().getApplicationInfo(packageName, 0);
        return ai.uid;
    }

    private static String key(String pkg, String op) {
        return pkg + "|" + op;
    }

    private void appendLog(String s) {
        runOnUiThread(() -> {
            CharSequence old = logView.getText();
            logView.setText(old + s + "\n");
        });
    }

    private static String modeToString(int mode) {
        switch (mode) {
            case AppOpsManager.MODE_ALLOWED: return "MODE_ALLOWED";
            case AppOpsManager.MODE_IGNORED: return "MODE_IGNORED";
            case AppOpsManager.MODE_ERRORED: return "MODE_ERRORED";
            case AppOpsManager.MODE_DEFAULT: return "MODE_DEFAULT";
            case 4: /* AppOpsManager.MODE_FOREGROUND (公开常量) */ return "MODE_FOREGROUND";
            default: return "MODE_" + mode;
        }
    }
}
```

说明与扩展
- 监听范围：
  - 以上实现为每个 op 注册一次监听，覆盖 OPS 列表中的项目。你可以补充更多 op 字符串，或根据业务只监听重点 op。
- 兼容性：
  - 不同 Android 版本存在新增/删除 op 的情况。对不存在的 op 调用 startWatchingMode 通常会抛异常或无回调，已在 try-catch 兜底。
- 性能考量：
  - 初始化快照遍历全量应用可能耗时，已放入子线程。你也可以按需延迟或跳过。
- 多用户支持：
  - 回调来自当前 user 的上下文。若需要监听其他用户，请结合 createContextAsUser 并在相应用户环境中注册；需要 INTERACT_ACROSS_USERS_FULL 权限。
- 更丰富的回调：
  - 新版本 AppOps 还有 onOpNoted 等统计维度 API，多为 @SystemApi 或受限，不在本 Demo 范畴。
- 日志与可视化：
  - 目前打印到 Logcat 与简单 TextView。你可以将变更记录存入本地数据库，或者用 RecyclerView 展示。

部署与验证
- 将 APK 放置为系统/priv-app，并确保授予 GET_APP_OPS_STATS（若非同签需 privapp-permissions 配置）。
- 启动 App 后，尝试在设备上变更权限/隐私设置（例如关闭/开启相机、麦克风、位置权限或前后台定位开关）。
- 观察 Logcat（tag: AppOpsWatcher）与界面日志，应该能看到：AppOps changed: pkg=..., op=android:..., mode=MODE_...

如果你需要基于 @SystemApi 的更细粒度监听或拉取历史（note/usage），我可以再给出 system SDK/hidden stubs 的配置与示例。