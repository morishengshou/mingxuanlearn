*Thinking...*

> 用户需要一个Android服务来监测AppOps权限的修改。这需要：
> 
> 1. 创建一个服务来监听AppOps的变化
> 2. 使用AppOpsManager的相关监听机制
> 3. 当检测到变化时，获取并打印新的权限状态
> 
> AppOps的监听可以通过以下方式：
> - 使用AppOpsManager.OnOpChangedListener（需要系统权限）
> - 使用ContentObserver监听Settings中的appops相关变化
> - 定期检查（不推荐，但作为备选方案）
> 
> 我将实现一个使用OnOpChangedListener的方案，这是最直接和高效的方式。

我来帮你实现一个监测AppOps权限变化的Android服务。

## 1. AppOps监测服务核心实现

```java
// AppOpsMonitorService.java
package com.example.appopsmonitor;

import android.app.AppOpsManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import android.util.SparseArray;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class AppOpsMonitorService extends Service {
    private static final String TAG = "AppOpsMonitor";
    
    private AppOpsManager mAppOpsManager;
    private PackageManager mPackageManager;
    private Handler mHandler;
    
    // 存储每个包的AppOps状态
    private Map<String, SparseArray<Integer>> mPackageOpsCache = new HashMap<>();
    
    // 要监测的包名列表
    private List<String> mMonitoredPackages = new ArrayList<>();
    
    // AppOps监听器列表
    private List<OpListener> mOpListeners = new ArrayList<>();
    
    // 内部监听器类
    private class OpListener {
        int op;
        Object listener;
        
        OpListener(int op, Object listener) {
            this.op = op;
            this.listener = listener;
        }
    }
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "AppOps Monitor Service created");
        
        mAppOpsManager = (AppOpsManager) getSystemService(Context.APP_OPS_SERVICE);
        mPackageManager = getPackageManager();
        mHandler = new Handler(Looper.getMainLooper());
        
        // 初始化AppOps监听
        initializeAppOpsListeners();
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getStringExtra("action");
            String packageName = intent.getStringExtra("package_name");
            
            if ("start_monitor".equals(action) && packageName != null) {
                startMonitoringPackage(packageName);
            } else if ("stop_monitor".equals(action) && packageName != null) {
                stopMonitoringPackage(packageName);
            } else if ("monitor_all".equals(action)) {
                monitorAllPackages();
            }
        }
        
        return START_STICKY;
    }
    
    private void initializeAppOpsListeners() {
        try {
            // 获取所有的AppOps操作码
            int[] ops = getAllOps();
            
            // 为每个Op注册监听器
            for (int op : ops) {
                registerOpListener(op);
            }
            
            Log.d(TAG, "Registered listeners for " + ops.length + " ops");
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize AppOps listeners", e);
        }
    }
    
    private int[] getAllOps() {
        List<Integer> opsList = new ArrayList<>();
        
        try {
            // 通过反射获取所有OP_开头的常量
            Field[] fields = AppOpsManager.class.getDeclaredFields();
            for (Field field : fields) {
                if (field.getName().startsWith("OP_") && 
                    field.getType() == int.class) {
                    field.setAccessible(true);
                    int op = field.getInt(null);
                    opsList.add(op);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get all ops", e);
            // 返回常用的ops作为备选
            return new int[] {0, 1, 2, 4, 5, 8, 9, 13, 14, 20, 26, 27};
        }
        
        // 转换为数组
        int[] ops = new int[opsList.size()];
        for (int i = 0; i < opsList.size(); i++) {
            ops[i] = opsList.get(i);
        }
        
        return ops;
    }
    
    private void registerOpListener(final int op) {
        try {
            // 使用反射调用startWatchingMode方法
            Method startWatchingMethod = mAppOpsManager.getClass().getDeclaredMethod(
                "startWatchingMode", int.class, String.class, 
                AppOpsManager.OnOpChangedListener.class);
            startWatchingMethod.setAccessible(true);
            
            // 创建监听器
            AppOpsManager.OnOpChangedListener listener = new AppOpsManager.OnOpChangedListener() {
                @Override
                public void onOpChanged(String op, String packageName) {
                    // 处理Op变化
                    handleOpChanged(Integer.parseInt(op), packageName);
                }
            };
            
            // 注册监听器，监听所有包的该Op变化
            startWatchingMethod.invoke(mAppOpsManager, op, null, listener);
            
            // 保存监听器引用
            mOpListeners.add(new OpListener(op, listener));
            
        } catch (Exception e) {
            // 如果上面的方法失败，尝试新版本的API
            try {
                registerOpListenerNewApi(op);
            } catch (Exception ex) {
                Log.e(TAG, "Failed to register listener for op " + op, ex);
            }
        }
    }
    
    private void registerOpListenerNewApi(final int op) throws Exception {
        // Android新版本的监听方式
        Method startWatchingMethod = mAppOpsManager.getClass().getDeclaredMethod(
            "startWatchingMode", int.class, String.class, int.class,
            AppOpsManager.class.getClassLoader().loadClass(
                "android.app.AppOpsManager$OnOpChangedInternalListener"));
        startWatchingMethod.setAccessible(true);
        
        // 创建内部监听器
        Class<?> listenerClass = Class.forName(
            "android.app.AppOpsManager$OnOpChangedInternalListener");
        Object listener = java.lang.reflect.Proxy.newProxyInstance(
            listenerClass.getClassLoader(),
            new Class[]{listenerClass},
            (proxy, method, args) -> {
                if ("onOpChanged".equals(method.getName())) {
                    int changedOp = (int) args[0];
                    String packageName = (String) args[1];
                    handleOpChanged(changedOp, packageName);
                }
                return null;
            }
        );
        
        // 注册监听器
        startWatchingMethod.invoke(mAppOpsManager, op, null, 
            android.app.AppOpsManager.WATCH_FOREGROUND_CHANGES, listener);
        
        mOpListeners.add(new OpListener(op, listener));
    }
    
    private void handleOpChanged(final int op, final String packageName) {
        mHandler.post(() -> {
            // 检查是否是我们监测的包
            if (!mMonitoredPackages.isEmpty() && !mMonitoredPackages.contains(packageName)) {
                return;
            }
            
            Log.i(TAG, String.format("AppOp changed - Package: %s, Op: %d (%s)", 
                packageName, op, getOpName(op)));
            
            try {
                // 获取新的Op状态
                int newMode = getOpMode(packageName, op);
                
                // 获取缓存的旧状态
                SparseArray<Integer> packageOps = mPackageOpsCache.get(packageName);
                int oldMode = -1;
                if (packageOps != null) {
                    oldMode = packageOps.get(op, -1);
                }
                
                // 打印变化详情
                printOpChange(packageName, op, oldMode, newMode);
                
                // 更新缓存
                updateCache(packageName, op, newMode);
                
                // 发送广播通知
                sendOpChangeBroadcast(packageName, op, oldMode, newMode);
                
            } catch (Exception e) {
                Log.e(TAG, "Error handling op change", e);
            }
        });
    }
    
    private int getOpMode(String packageName, int op) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            
            // 使用反射调用checkOpNoThrow
            Method checkOpMethod = mAppOpsManager.getClass().getDeclaredMethod(
                "checkOpNoThrow", int.class, int.class, String.class);
            checkOpMethod.setAccessible(true);
            
            return (int) checkOpMethod.invoke(mAppOpsManager, op, appInfo.uid, packageName);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to get op mode", e);
            return AppOpsManager.MODE_DEFAULT;
        }
    }
    
    private void printOpChange(String packageName, int op, int oldMode, int newMode) {
        String opName = getOpName(op);
        String oldModeName = getModeName(oldMode);
        String newModeName = getModeName(newMode);
        
        String message = String.format(
            "════════════════════════════════════════\n" +
            "AppOps Permission Changed:\n" +
            "Package: %s\n" +
            "Operation: %s (Op %d)\n" +
            "Old Mode: %s\n" +
            "New Mode: %s\n" +
            "Time: %s\n" +
            "════════════════════════════════════════",
            packageName, opName, op, oldModeName, newModeName, 
            new java.util.Date().toString()
        );
        
        Log.i(TAG, message);
        
        // 同时获取并打印该应用的所有AppOps状态
        printAllOpsForPackage(packageName);
    }
    
    private void printAllOpsForPackage(String packageName) {
        Log.i(TAG, "Current AppOps status for " + packageName + ":");
        
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            
            // 获取所有ops
            Method getOpsForPackageMethod = mAppOpsManager.getClass().getDeclaredMethod(
                "getOpsForPackage", int.class, String.class, int[].class);
            getOpsForPackageMethod.setAccessible(true);
            
            List<?> packageOps = (List<?>) getOpsForPackageMethod.invoke(
                mAppOpsManager, appInfo.uid, packageName, null);
            
            if (packageOps != null && !packageOps.isEmpty()) {
                Object ops = packageOps.get(0);
                Method getOpsMethod = ops.getClass().getDeclaredMethod("getOps");
                getOpsMethod.setAccessible(true);
                
                List<?> opEntries = (List<?>) getOpsMethod.invoke(ops);
                
                for (Object opEntry : opEntries) {
                    printOpEntry(opEntry);
                }
            }
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to get all ops for package", e);
        }
    }
    
    private void printOpEntry(Object opEntry) {
        try {
            Method getOpMethod = opEntry.getClass().getDeclaredMethod("getOp");
            Method getModeMethod = opEntry.getClass().getDeclaredMethod("getMode");
            
            getOpMethod.setAccessible(true);
            getModeMethod.setAccessible(true);
            
            int op = (int) getOpMethod.invoke(opEntry);
            int mode = (int) getModeMethod.invoke(opEntry);
            
            Log.i(TAG, String.format("  - %s (Op %d): %s", 
                getOpName(op), op, getModeName(mode)));
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to print op entry", e);
        }
    }
    
    private void updateCache(String packageName, int op, int mode) {
        SparseArray<Integer> packageOps = mPackageOpsCache.get(packageName);
        if (packageOps == null) {
            packageOps = new SparseArray<>();
            mPackageOpsCache.put(packageName, packageOps);
        }
        packageOps.put(op, mode);
    }
    
    private void startMonitoringPackage(String packageName) {
        if (!mMonitoredPackages.contains(packageName)) {
            mMonitoredPackages.add(packageName);
            Log.i(TAG, "Started monitoring: " + packageName);
            
            // 初始化该包的AppOps状态
            cachePackageOps(packageName);
        }
    }
    
    private void stopMonitoringPackage(String packageName) {
        mMonitoredPackages.remove(packageName);
        mPackageOpsCache.remove(packageName);
        Log.i(TAG, "Stopped monitoring: " + packageName);
    }
    
    private void monitorAllPackages() {
        mMonitoredPackages.clear();
        Log.i(TAG, "Monitoring all packages");
    }
    
    private void cachePackageOps(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            int[] ops = getAllOps();
            
            SparseArray<Integer> packageOps = new SparseArray<>();
            
            for (int op : ops) {
                int mode = getOpMode(packageName, op);
                packageOps.put(op, mode);
            }
            
            mPackageOpsCache.put(packageName, packageOps);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to cache package ops", e);
        }
    }
    
    private String getOpName(int op) {
        try {
            Field[] fields = AppOpsManager.class.getDeclaredFields();
            for (Field field : fields) {
                if (field.getName().startsWith("OP_") && 
                    field.getType() == int.class) {
                    field.setAccessible(true);
                    if (field.getInt(null) == op) {
                        return field.getName().substring(3); // 去掉"OP_"前缀
                    }
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get op name", e);
        }
        return "UNKNOWN_OP_" + op;
    }
    
    private String getModeName(int mode) {
        switch (mode) {
            case AppOpsManager.MODE_ALLOWED:
                return "ALLOWED";
            case AppOpsManager.MODE_IGNORED:
                return "IGNORED (DENIED)";
            case AppOpsManager.MODE_ERRORED:
                return "ERRORED";
            case AppOpsManager.MODE_DEFAULT:
                return "DEFAULT";
            case 4: // MODE_FOREGROUND
                return "FOREGROUND_ONLY";
            default:
                return "UNKNOWN(" + mode + ")";
        }
    }
    
    private void sendOpChangeBroadcast(String packageName, int op, int oldMode, int newMode) {
        Intent intent = new Intent("com.example.appopsmonitor.OP_CHANGED");
        intent.putExtra("package_name", packageName);
        intent.putExtra("op", op);
        intent.putExtra("op_name", getOpName(op));
        intent.putExtra("old_mode", oldMode);
        intent.putExtra("new_mode", newMode);
        intent.putExtra("old_mode_name", getModeName(oldMode));
        intent.putExtra("new_mode_name", getModeName(newMode));
        intent.putExtra("timestamp", System.currentTimeMillis());
        
        sendBroadcast(intent);
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        
        // 注销所有监听器
        unregisterAllListeners();
        
        Log.d(TAG, "AppOps Monitor Service destroyed");
    }
    
    private void unregisterAllListeners() {
        try {
            Method stopWatchingMethod = mAppOpsManager.getClass().getDeclaredMethod(
                "stopWatchingMode", AppOpsManager.OnOpChangedListener.class);
            stopWatchingMethod.setAccessible(true);
            
            for (OpListener opListener : mOpListeners) {
                try {
                    stopWatchingMethod.invoke(mAppOpsManager, opListener.listener);
                } catch (Exception e) {
                    Log.e(TAG, "Failed to unregister listener for op " + opListener.op, e);
                }
            }
            
            mOpListeners.clear();
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to unregister listeners", e);
        }
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
```

## 2. 监控界面Activity

```java
// AppOpsMonitorActivity.java
package com.example.appopsmonitor;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.text.method.ScrollingMovementMethod;
import android.view.View;
import android.widget.*;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class AppOpsMonitorActivity extends Activity {
    private static final String TAG = "AppOpsMonitor";
    
    private Spinner appSpinner;
    private Button startMonitorButton;
    private Button stopMonitorButton;
    private Button monitorAllButton;
    private Button clearLogButton;
    private TextView logTextView;
    private ScrollView scrollView;
    
    private List<AppInfo> installedApps = new ArrayList<>();
    private SimpleDateFormat dateFormat = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());
    
    private static class AppInfo {
        String packageName;
        String appName;
        
        @Override
        public String toString() {
            return appName + " (" + packageName + ")";
        }
    }
    
    private BroadcastReceiver opChangeReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String packageName = intent.getStringExtra("package_name");
            String opName = intent.getStringExtra("op_name");
            String oldModeName = intent.getStringExtra("old_mode_name");
            String newModeName = intent.getStringExtra("new_mode_name");
            long timestamp = intent.getLongExtra("timestamp", System.currentTimeMillis());
            
            String time = dateFormat.format(new Date(timestamp));
            String logEntry = String.format("[%s] %s\n  %s: %s → %s\n\n",
                time, packageName, opName, oldModeName, newModeName);
            
            runOnUiThread(() -> {
                logTextView.append(logEntry);
                scrollView.post(() -> scrollView.fullScroll(ScrollView.FOCUS_DOWN));
            });
        }
    };
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_monitor);
        
        initViews();
        loadInstalledApps();
        setupListeners();
        
        // 启动监控服务
        startService(new Intent(this, AppOpsMonitorService.class));
    }
    
    private void initViews() {
        appSpinner = findViewById(R.id.app_spinner);
        startMonitorButton = findViewById(R.id.start_monitor_button);
        stopMonitorButton = findViewById(R.id.stop_monitor_button);
        monitorAllButton = findViewById(R.id.monitor_all_button);
        clearLogButton = findViewById(R.id.clear_log_button);
        logTextView = findViewById(R.id.log_text_view);
        scrollView = findViewById(R.id.scroll_view);
        
        logTextView.setMovementMethod(new ScrollingMovementMethod());
    }
    
    private void loadInstalledApps() {
        PackageManager pm = getPackageManager();
        List<ApplicationInfo> apps = pm.getInstalledApplications(0);
        
        for (ApplicationInfo app : apps) {
            AppInfo appInfo = new AppInfo();
            appInfo.packageName = app.packageName;
            appInfo.appName = pm.getApplicationLabel(app).toString();
            installedApps.add(appInfo);
        }
        
        ArrayAdapter<AppInfo> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, installedApps);
        appSpinner.setAdapter(adapter);
    }
    
    private void setupListeners() {
        startMonitorButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            if (selectedApp != null) {
                Intent intent = new Intent(this, AppOpsMonitorService.class);
                intent.putExtra("action", "start_monitor");
                intent.putExtra("package_name", selectedApp.packageName);
                startService(intent);
                
                logTextView.append("Started monitoring: " + selectedApp.packageName + "\n\n");
            }
        });
        
        stopMonitorButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            if (selectedApp != null) {
                Intent intent = new Intent(this, AppOpsMonitorService.class);
                intent.putExtra("action", "stop_monitor");
                intent.putExtra("package_name", selectedApp.packageName);
                startService(intent);
                
                logTextView.append("Stopped monitoring: " + selectedApp.packageName + "\n\n");
            }
        });
        
        monitorAllButton.setOnClickListener(v -> {
            Intent intent = new Intent(this, AppOpsMonitorService.class);
            intent.putExtra("action", "monitor_all");
            startService(intent);
            
            logTextView.append("Started monitoring all packages\n\n");
        });
        
        clearLogButton.setOnClickListener(v -> {
            logTextView.setText("");
        });
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter("com.example.appopsmonitor.OP_CHANGED");
        registerReceiver(opChangeReceiver, filter);
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(opChangeReceiver);
    }
}
```

## 3. 布局文件

```xml
<!-- res/layout/activity_monitor.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="AppOps Monitor"
        android:textSize="20sp"
        android:textStyle="bold"
        android:layout_marginBottom="16dp" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Select App to Monitor:" />

    <Spinner
        android:id="@+id/app_spinner"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginBottom="16dp" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="8dp">

        <Button
            android:id="@+id/start_monitor_button"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Start"
            android:layout_marginEnd="4dp" />

        <Button
            android:id="@+id/stop_monitor_button"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Stop"
            android:layout_marginEnd="4dp" />

        <Button
            android:id="@+id/monitor_all_button"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Monitor All" />

    </LinearLayout>

    <Button
        android:id="@+id/clear_log_button"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Clear Log"
        android:layout_marginBottom="16dp" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="AppOps Change Log:"
        android:textStyle="bold"
        android:layout_marginBottom="8dp" />

    <ScrollView
        android:id="@+id/scroll_view"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:background="#f5f5f5">

        <TextView
            android:id="@+id/log_text_view"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:padding="12dp"
            android:textSize="13sp"
            android:typeface="monospace"
            android:textColor="#333333" />

    </ScrollView>

</LinearLayout>
```

## 4. AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.appopsmonitor"
    android:sharedUserId="android.uid.system">
    
    <!-- 系统级权限 -->
    <uses-permission android:name="android.permission.UPDATE_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.GET_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.MANAGE_APP_OPS_MODES" />
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
    
    <application
        android:allowBackup="false"
        android:label="AppOps Monitor"
        android:theme="@android:style/Theme.Material.Light">
        
        <activity
            android:name=".AppOpsMonitorActivity"
            android:exported="true"
            android:launchMode="singleTop">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <service
            android:name=".AppOpsMonitorService"
            android:exported="false" />
            
    </application>
</manifest>
```

## 5. 命令行使用方式

### start_monitor.sh
```bash
#!/bin/bash

# 启动AppOps监控服务

# 监控特定应用
monitor_app() {
    local package_name=$1
    adb shell am startservice \
        -n com.example.appopsmonitor/.AppOpsMonitorService \
        -e action start_monitor \
        -e package_name "$package_name"
}

# 监控所有应用
monitor_all() {
    adb shell am startservice \
        -n com.example.appopsmonitor/.AppOpsMonitorService \
        -e action monitor_all
}

# 查看日志
view_logs() {
    adb logcat -s AppOpsMonitor:*
}

# 主菜单
case "$1" in
    app)
        monitor_app "$2"
        ;;
    all)
        monitor_all
        ;;
    logs)
        view_logs
        ;;
    *)
        echo "Usage: $0 {app <package_name>|all|logs}"
        exit 1
        ;;
esac
```

## 6. 增强版：带过滤功能的监控服务

```java
// AppOpsFilter.java
package com.example.appopsmonitor;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public class AppOpsFilter {
    // 位置相关的Ops
    public static final Set<Integer> LOCATION_OPS = new HashSet<>(Arrays.asList(
        0,  // OP_COARSE_LOCATION
        1,  // OP_FINE_LOCATION
        41, // OP_MONITOR_LOCATION
        42  // OP_MONITOR_HIGH_POWER_LOCATION
    ));
    
    // 隐私相关的Ops
    public static final Set<Integer> PRIVACY_OPS = new HashSet<>(Arrays.asList(
        4,  // OP_READ_CONTACTS
        5,  // OP_WRITE_CONTACTS
        6,  // OP_READ_CALL_LOG
        7,  // OP_WRITE_CALL_LOG
        14, // OP_READ_SMS
        15, // OP_WRITE_SMS
        26, // OP_CAMERA
        27  // OP_RECORD_AUDIO
    ));
    
    // 存储相关的Ops
    public static final Set<Integer> STORAGE_OPS = new HashSet<>(Arrays.asList(
        59, // OP_READ_EXTERNAL_STORAGE
        60  // OP_WRITE_EXTERNAL_STORAGE
    ));
    
    public static boolean isImportantOp(int op) {
        return LOCATION_OPS.contains(op) || 
               PRIVACY_OPS.contains(op) || 
               STORAGE_OPS.contains(op);
    }
}
```

## 使用说明

1. **功能特点**：
   - 实时监听AppOps权限变化，无需轮询
   - 支持监控特定应用或所有应用
   - 详细记录权限变化前后的状态
   - 自动打印应用的所有AppOps状态

2. **监控输出示例**：
```
════════════════════════════════════════
AppOps Permission Changed:
Package: com.example.app
Operation: CAMERA (Op 26)
Old Mode: ALLOWED
New Mode: IGNORED (DENIED)
Time: Mon Nov 25 10:30:45 CST 2024
════════════════════════════════════════

Current AppOps status for com.example.app:
  - FINE_LOCATION (Op 1): ALLOWED
  - READ_CONTACTS (Op 4): DEFAULT
  - CAMERA (Op 26): IGNORED (DENIED)
  - RECORD_AUDIO (Op 27): ALLOWED
```

3. **注意事项**：
   - 需要系统签名和相应权限
   - 监听器会持续运行直到服务停止
   - 建议在实际使用中添加过滤功能，只监控重要的Ops

这个监控服务能够实时检测并报告AppOps权限的所有变化，非常适合用于系统级的权限审计和监控。