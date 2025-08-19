下面给出一个可运行的 Java Demo，演示在“系统应用 + 拥有系统级权限”的前提下，如何查询和修改其他应用的 AppOps 授权状态。内容包括：

- 必要权限与前置条件
- 核心工具类：查询/设置 AppOps 模式
- 示例 Activity：简单 UI 操作目标包与 op
- 常见问题与排错

重要前置条件
- 你的应用必须是系统/priv-app，并被授予以下签名级权限（至少需要 MANAGE_APP_OPS_MODES；查询建议加 GET_APP_OPS_STATS）：
  - android.permission.MANAGE_APP_OPS_MODES
  - android.permission.GET_APP_OPS_STATS
  - 如需跨用户：android.permission.INTERACT_ACROSS_USERS_FULL
- 若不是平台同签，需要在 /system/etc/permissions/privapp-permissions-<oem>.xml 中为你的包名放行上述权限。
- 目标设备 Android 10+。不同版本 AppOps 行为略有差异。

Manifest 示例
将以下权限加入你的 AndroidManifest.xml（系统签名或 privapp 白名单必需）：

```xml
<manifest package="com.example.appopsjdemo" xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.MANAGE_APP_OPS_MODES"/>
    <uses-permission android:name="android.permission.GET_APP_OPS_STATS"/>
    <uses-permission android:name="android.permission.INTERACT_ACROSS_USERS_FULL"/>
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"/>
    <application
        android:label="AppOps J Demo"
        android:allowBackup="false">
        <activity android:name=".MainActivity"
                  android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
```

核心工具类（Java）
提供按包名与 op 名称查询/设置模式的封装。注意：op 是 AppOps 的“操作名”（如 android:camera、android:record_audio）。若你只有权限名，可用 AppOpsManager.permissionToOp 映射。

```java
package com.example.appopsjdemo;

import android.app.AppOpsManager;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;

public class AppOpsUtils {

    public static class OpResult {
        public final boolean success;
        public final String message;
        public final Integer mode; // 可为 null

        public OpResult(boolean success, String message, Integer mode) {
            this.success = success;
            this.message = message;
            this.mode = mode;
        }

        public static OpResult ok(int mode) {
            return new OpResult(true, "OK", mode);
        }

        public static OpResult error(String msg) {
            return new OpResult(false, msg, null);
        }
    }

    // 将权限名映射为 op 名（若返回 null，说明该权限不受 AppOps 管控）
    public static String permissionToOp(String permission) {
        return AppOpsManager.permissionToOp(permission);
    }

    // 获取目标包的 uid
    public static int getUidForPackage(Context context, String packageName) throws PackageManager.NameNotFoundException {
        ApplicationInfo ai = context.getPackageManager().getApplicationInfo(packageName, 0);
        return ai.uid;
    }

    // 查询某个 op 的当前模式
    public static OpResult getOpMode(Context context, String packageName, String op) {
        try {
            AppOpsManager appOps = context.getSystemService(AppOpsManager.class);
            int uid = getUidForPackage(context, packageName);
            int mode = appOps.unsafeCheckOpNoThrow(op, uid, packageName);
            return OpResult.ok(mode);
        } catch (Throwable t) {
            return OpResult.error("getOpMode failed: " + t);
        }
    }

    // 设置某个 op 的模式（per-package）
    // 常用 mode: MODE_ALLOWED, MODE_IGNORED, MODE_ERRORED, MODE_DEFAULT, MODE_FOREGROUND(部分 op 支持)
    public static OpResult setOpMode(Context context, String packageName, String op, int mode) {
        try {
            AppOpsManager appOps = context.getSystemService(AppOpsManager.class);
            int uid = getUidForPackage(context, packageName);
            appOps.setMode(op, uid, packageName, mode);
            // 回读确认
            int newMode = appOps.unsafeCheckOpNoThrow(op, uid, packageName);
            return OpResult.ok(newMode);
        } catch (SecurityException se) {
            return OpResult.error("SecurityException: lack of MANAGE_APP_OPS_MODES or not a trusted system app. " + se);
        } catch (Throwable t) {
            return OpResult.error("setOpMode failed: " + t);
        }
    }

    // 可选：按 UID 维度设置（会影响该 UID 下的所有包）
    public static OpResult setOpModeForUid(Context context, String packageName, String op, int mode, int userId) {
        try {
            AppOpsManager appOps = context.getSystemService(AppOpsManager.class);
            int uid = getUidForPackage(context, packageName);
            // 如果需要特定 userId，可根据多用户把 uid 适配到对应 user（此处简化直接使用应用 uid）
            appOps.setUidMode(op, uid, mode);
            int newMode = appOps.unsafeCheckOpNoThrow(op, uid, packageName);
            return OpResult.ok(newMode);
        } catch (Throwable t) {
            return OpResult.error("setUidMode failed: " + t);
        }
    }
}
```

示例 Activity（Java）
简单 UI 输入目标包名和“权限名或 op 名”，支持一键映射和设置模式。

```java
package com.example.appopsjdemo;

import android.app.AppOpsManager;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.*;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private EditText pkgInput;
    private EditText permOrOpInput;
    private TextView statusText;
    private Spinner modeSpinner;
    private Button btnResolveOp;
    private Button btnQuery;
    private Button btnAllow;
    private Button btnIgnore;
    private Button btnError;
    private Button btnDefault;

    private String resolvedOp; // 解析后的 op 名称（android:xxx）

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, pad);

        pkgInput = new EditText(this);
        pkgInput.setHint("目标包名，例如：com.example.target");
        root.addView(pkgInput, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        permOrOpInput = new EditText(this);
        permOrOpInput.setHint("权限或op，例如：android.permission.CAMERA 或 android:camera");
        root.addView(permOrOpInput, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        btnResolveOp = new Button(this);
        btnResolveOp.setText("解析为 AppOp");
        root.addView(btnResolveOp);

        modeSpinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item,
                new String[]{
                        "MODE_ALLOWED",
                        "MODE_IGNORED",
                        "MODE_ERRORED",
                        "MODE_DEFAULT",
                        "MODE_FOREGROUND"
                });
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        modeSpinner.setAdapter(adapter);
        root.addView(modeSpinner);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);

        btnQuery = new Button(this);
        btnQuery.setText("查询当前模式");
        row.addView(btnQuery, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        btnAllow = new Button(this);
        btnAllow.setText("设为 ALLOWED");
        row.addView(btnAllow, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        root.addView(row);

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);

        btnIgnore = new Button(this);
        btnIgnore.setText("设为 IGNORED");
        row2.addView(btnIgnore, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        btnError = new Button(this);
        btnError.setText("设为 ERRORED");
        row2.addView(btnError, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        root.addView(row2);

        LinearLayout row3 = new LinearLayout(this);
        row3.setOrientation(LinearLayout.HORIZONTAL);

        btnDefault = new Button(this);
        btnDefault.setText("设为 DEFAULT");
        row3.addView(btnDefault, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        Button btnForeground = new Button(this);
        btnForeground.setText("设为 FOREGROUND");
        row3.addView(btnForeground, new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        root.addView(row3);

        statusText = new TextView(this);
        statusText.setTextIsSelectable(true);
        root.addView(statusText, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        setContentView(root);

        btnResolveOp.setOnClickListener(v -> {
            String input = getTextTrim(permOrOpInput);
            if (TextUtils.isEmpty(input)) {
                toast("请输入权限或 op");
                return;
            }
            if (input.startsWith("android:")) {
                resolvedOp = input;
            } else {
                String op = AppOpsUtils.permissionToOp(input);
                if (op == null) {
                    resolvedOp = null;
                    setStatus("该权限没有对应的 AppOp 或系统版本未映射\n输入: " + input);
                    return;
                }
                resolvedOp = op;
            }
            setStatus("解析成功，op = " + resolvedOp);
        });

        btnQuery.setOnClickListener(v -> {
            String pkg = getTextTrim(pkgInput);
            if (!checkInputs(pkg)) return;
            AppOpsUtils.OpResult r = AppOpsUtils.getOpMode(this, pkg, resolvedOp);
            setStatus("query: success=" + r.success + ", mode=" + modeToString(r.mode) + ", msg=" + r.message);
        });

        btnAllow.setOnClickListener(v -> setModeClick(AppOpsManager.MODE_ALLOWED));
        btnIgnore.setOnClickListener(v -> setModeClick(AppOpsManager.MODE_IGNORED));
        btnError.setOnClickListener(v -> setModeClick(AppOpsManager.MODE_ERRORED));
        btnDefault.setOnClickListener(v -> setModeClick(AppOpsManager.MODE_DEFAULT));
        btnForeground.setOnClickListener(v -> setModeClick(AppOpsManager.MODE_FOREGROUND));
    }

    private void setModeClick(int mode) {
        String pkg = getTextTrim(pkgInput);
        if (!checkInputs(pkg)) return;
        AppOpsUtils.OpResult r = AppOpsUtils.setOpMode(this, pkg, resolvedOp, mode);
        setStatus("set: success=" + r.success + ", newMode=" + modeToString(r.mode) + ", msg=" + r.message);
    }

    private boolean checkInputs(String pkg) {
        if (TextUtils.isEmpty(pkg)) {
            toast("请输入目标包名");
            return false;
        }
        String in = getTextTrim(permOrOpInput);
        if (TextUtils.isEmpty(in)) {
            toast("请输入权限或 op");
            return false;
        }
        if (TextUtils.isEmpty(resolvedOp)) {
            toast("请先点击“解析为 AppOp”");
            return false;
        }
        return true;
    }

    private static String getTextTrim(EditText et) {
        return et.getText() == null ? "" : et.getText().toString().trim();
    }

    private void setStatus(String s) {
        statusText.setText(s);
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }

    private String modeToString(Integer mode) {
        if (mode == null) return "null";
        switch (mode) {
            case AppOpsManager.MODE_ALLOWED: return "MODE_ALLOWED";
            case AppOpsManager.MODE_ERRORED: return "MODE_ERRORED";
            case AppOpsManager.MODE_IGNORED: return "MODE_IGNORED";
            case AppOpsManager.MODE_DEFAULT: return "MODE_DEFAULT";
            case AppOpsManager.MODE_FOREGROUND: return "MODE_FOREGROUND";
            default: return "MODE_" + mode;
        }
    }
}
```

使用说明
- 在设备上以系统/priv-app 安装此 Demo。
- 打开应用：
  1) 输入目标包名，如 com.android.camera
  2) 在第二个输入框输入“权限名或 op 名”：
     - 权限名示例：android.permission.CAMERA、android.permission.RECORD_AUDIO、android.permission.ACCESS_FINE_LOCATION
     - 或直接 op：android:camera、android:record_audio、android:fine_location
  3) 点击“解析为 AppOp”得到 op。
  4) 点击“查询当前模式”查看。
  5) 选择对应按钮设置为 ALLOWED/IGNORED/ERRORED/DEFAULT/FOREGROUND。

补充与建议
- 并非所有权限都有 AppOp 映射，permissionToOp 返回 null 则无法通过 AppOps 控制。
- 还有“switch op”的概念：多个具体 op 可能受一个总开关影响；该细节对 setMode/unsafeCheckOpNoThrow 通常透明。
- MODE_FOREGROUND 只对部分 op 有意义（如定位、麦克风等），对不支持的 op 设置后通常等同于 IGNORED 或无效。
- 若 setMode 报 SecurityException：
  - 确认应用在 /system/priv-app 且具备 MANAGE_APP_OPS_MODES 权限；
  - 检查 privapp-permissions 是否授予；
  - 查看 logcat 中 AppOps 输出的拒绝原因。

调试命令
- 你也可以用 adb 验证效果：
  - adb shell appops get <package> <op>
  - adb shell appops set <package> <op> allow|ignore|deny|default|foreground

以上即为 Java 版系统应用修改其他应用 AppOps 授权状态的示例。若你需要改为 Service/后台批量处理或加入监听（OnOpChangedListener），可以在此基础上扩展。