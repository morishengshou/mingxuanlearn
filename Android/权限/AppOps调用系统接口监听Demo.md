*Thinking...*

> 用户要求基于系统应用的特权，不使用反射，直接调用系统接口来实现AppOps监测。这意味着我们可以：
> 
> 1. 直接使用隐藏的系统API
> 2. 使用系统服务的内部接口
> 3. 不需要通过反射来访问私有方法
> 
> 作为系统应用，我们可以：
> - 直接导入并使用internal API
> - 使用IAppOpsService等AIDL接口
> - 访问系统级的监听器接口
> 
> 我需要提供一个更清晰、更直接的实现方式。

既然你的应用是系统应用并拥有系统权限，我来提供一个直接使用系统接口的实现，不需要反射。

## 1. AppOps监测服务（使用系统接口）

```java
// SystemAppOpsMonitorService.java
package com.example.systemappopsmonitor;

import android.app.AppOpsManager;
import android.app.AppOpsManager.OnOpChangedListener;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.RemoteException;
import android.os.ServiceManager;
import android.util.Log;
import android.util.SparseArray;

import com.android.internal.app.IAppOpsCallback;
import com.android.internal.app.IAppOpsService;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public class SystemAppOpsMonitorService extends Service {
    private static final String TAG = "SystemAppOpsMonitor";
    
    private IAppOpsService mAppOpsService;
    private AppOpsManager mAppOpsManager;
    private PackageManager mPackageManager;
    private Handler mHandler;
    
    // 监控的包名集合
    private Set<String> mMonitoredPackages = new HashSet<>();
    
    // 缓存每个包的AppOps状态
    private Map<String, SparseArray<OpState>> mOpsCache = new HashMap<>();
    
    // 日期格式化
    private SimpleDateFormat mDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault());
    
    // AppOps状态类
    private static class OpState {
        int mode;
        long time;
        int duration;
        
        OpState(int mode, long time, int duration) {
            this.mode = mode;
            this.time = time;
            this.duration = duration;
        }
    }
    
    // AppOps回调实现
    private final IAppOpsCallback.Stub mOpCallback = new IAppOpsCallback.Stub() {
        @Override
        public void opChanged(int op, int uid, String packageName) {
            handleOpChanged(op, uid, packageName);
        }
    };
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "System AppOps Monitor Service created");
        
        mHandler = new Handler(Looper.getMainLooper());
        mPackageManager = getPackageManager();
        mAppOpsManager = (AppOpsManager) getSystemService(Context.APP_OPS_SERVICE);
        
        // 获取IAppOpsService
        IBinder binder = ServiceManager.getService(Context.APP_OPS_SERVICE);
        mAppOpsService = IAppOpsService.Stub.asInterface(binder);
        
        if (mAppOpsService == null) {
            Log.e(TAG, "Failed to get IAppOpsService");
        }
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getStringExtra("action");
            String packageName = intent.getStringExtra("package_name");
            
            switch (action) {
                case "start_monitor":
                    if (packageName != null) {
                        startMonitoringPackage(packageName);
                    }
                    break;
                    
                case "stop_monitor":
                    if (packageName != null) {
                        stopMonitoringPackage(packageName);
                    }
                    break;
                    
                case "monitor_all":
                    startMonitoringAll();
                    break;
                    
                case "stop_all":
                    stopMonitoringAll();
                    break;
            }
        }
        
        return START_STICKY;
    }
    
    private void startMonitoringPackage(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            
            // 添加到监控列表
            mMonitoredPackages.add(packageName);
            
            // 初始化该包的ops状态
            cachePackageOps(packageName, appInfo.uid);
            
            // 开始监听
            if (mMonitoredPackages.size() == 1) {
                // 第一次添加监控时注册回调
                mAppOpsService.startWatchingMode(AppOpsManager.OP_NONE, null, mOpCallback);
            }
            
            Log.i(TAG, "Started monitoring package: " + packageName);
            printCurrentOpsState(packageName, appInfo.uid);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to start monitoring package: " + packageName, e);
        }
    }
    
    private void stopMonitoringPackage(String packageName) {
        mMonitoredPackages.remove(packageName);
        mOpsCache.remove(packageName);
        
        if (mMonitoredPackages.isEmpty()) {
            try {
                // 没有监控的包时停止回调
                mAppOpsService.stopWatchingMode(mOpCallback);
            } catch (RemoteException e) {
                Log.e(TAG, "Failed to stop watching mode", e);
            }
        }
        
        Log.i(TAG, "Stopped monitoring package: " + packageName);
    }
    
    private void startMonitoringAll() {
        try {
            mMonitoredPackages.clear();
            
            // 开始监听所有包
            mAppOpsService.startWatchingMode(AppOpsManager.OP_NONE, null, mOpCallback);
            
            Log.i(TAG, "Started monitoring all packages");
            
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to start monitoring all", e);
        }
    }
    
    private void stopMonitoringAll() {
        try {
            mMonitoredPackages.clear();
            mOpsCache.clear();
            
            mAppOpsService.stopWatchingMode(mOpCallback);
            
            Log.i(TAG, "Stopped monitoring all packages");
            
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to stop monitoring", e);
        }
    }
    
    private void handleOpChanged(final int op, final int uid, final String packageName) {
        mHandler.post(() -> {
            // 检查是否需要监控该包
            if (!mMonitoredPackages.isEmpty() && !mMonitoredPackages.contains(packageName)) {
                return;
            }
            
            try {
                // 获取当前的op状态
                int currentMode = mAppOpsService.checkOperation(op, uid, packageName);
                
                // 获取之前缓存的状态
                SparseArray<OpState> packageOps = mOpsCache.get(packageName);
                OpState cachedState = null;
                if (packageOps != null) {
                    cachedState = packageOps.get(op);
                }
                
                // 打印变化信息
                printOpChange(packageName, uid, op, cachedState, currentMode);
                
                // 更新缓存
                updateOpCache(packageName, op, currentMode);
                
                // 打印该应用当前所有的ops状态
                printCurrentOpsState(packageName, uid);
                
                // 发送广播通知
                sendOpChangeBroadcast(packageName, uid, op, cachedState, currentMode);
                
            } catch (RemoteException e) {
                Log.e(TAG, "Failed to handle op change", e);
            }
        });
    }
    
    private void printOpChange(String packageName, int uid, int op, OpState oldState, int newMode) {
        String timestamp = mDateFormat.format(new Date());
        String opName = AppOpsManager.opToName(op);
        String oldModeName = oldState != null ? getModeString(oldState.mode) : "UNKNOWN";
        String newModeName = getModeString(newMode);
        
        StringBuilder sb = new StringBuilder();
        sb.append("\n╔══════════════════════════════════════════════════════════════════╗\n");
        sb.append("║                     AppOps Permission Changed                     ║\n");
        sb.append("╠══════════════════════════════════════════════════════════════════╣\n");
        sb.append(String.format("║ Time     : %-53s ║\n", timestamp));
        sb.append(String.format("║ Package  : %-53s ║\n", packageName));
        sb.append(String.format("║ UID      : %-53d ║\n", uid));
        sb.append(String.format("║ Operation: %-53s ║\n", opName + " (" + op + ")"));
        sb.append(String.format("║ Change   : %-25s → %-25s ║\n", oldModeName, newModeName));
        sb.append("╚══════════════════════════════════════════════════════════════════╝");
        
        Log.i(TAG, sb.toString());
    }
    
    private void printCurrentOpsState(String packageName, int uid) {
        try {
            List<AppOpsManager.PackageOps> pkgOpsList = mAppOpsService.getOpsForPackage(
                    uid, packageName, null);
            
            if (pkgOpsList == null || pkgOpsList.isEmpty()) {
                return;
            }
            
            StringBuilder sb = new StringBuilder();
            sb.append("\n┌─────────────────────────────────────────────────────────────────┐\n");
            sb.append(String.format("│ Current AppOps State for: %-37s │\n", packageName));
            sb.append("├─────────────────────────────────────────────────────────────────┤\n");
            
            for (AppOpsManager.PackageOps pkgOps : pkgOpsList) {
                List<AppOpsManager.OpEntry> ops = pkgOps.getOps();
                for (AppOpsManager.OpEntry op : ops) {
                    String opName = AppOpsManager.opToName(op.getOp());
                    String mode = getModeString(op.getMode());
                    String lastAccess = op.getLastAccessTime() > 0 ? 
                            mDateFormat.format(new Date(op.getLastAccessTime())) : "Never";
                    
                    sb.append(String.format("│ %-20s : %-15s (Last: %s) │\n", 
                            opName, mode, lastAccess));
                }
            }
            
            sb.append("└─────────────────────────────────────────────────────────────────┘");
            
            Log.i(TAG, sb.toString());
            
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to get current ops state", e);
        }
    }
    
    private void cachePackageOps(String packageName, int uid) {
        try {
            List<AppOpsManager.PackageOps> pkgOpsList = mAppOpsService.getOpsForPackage(
                    uid, packageName, null);
            
            if (pkgOpsList == null || pkgOpsList.isEmpty()) {
                return;
            }
            
            SparseArray<OpState> opsMap = new SparseArray<>();
            
            for (AppOpsManager.PackageOps pkgOps : pkgOpsList) {
                List<AppOpsManager.OpEntry> ops = pkgOps.getOps();
                for (AppOpsManager.OpEntry op : ops) {
                    opsMap.put(op.getOp(), new OpState(
                            op.getMode(), 
                            op.getLastAccessTime(),
                            op.getDuration()
                    ));
                }
            }
            
            mOpsCache.put(packageName, opsMap);
            
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to cache package ops", e);
        }
    }
    
    private void updateOpCache(String packageName, int op, int mode) {
        SparseArray<OpState> packageOps = mOpsCache.get(packageName);
        if (packageOps == null) {
            packageOps = new SparseArray<>();
            mOpsCache.put(packageName, packageOps);
        }
        
        packageOps.put(op, new OpState(mode, System.currentTimeMillis(), 0));
    }
    
    private String getModeString(int mode) {
        switch (mode) {
            case AppOpsManager.MODE_ALLOWED:
                return "ALLOWED";
            case AppOpsManager.MODE_IGNORED:
                return "IGNORED";
            case AppOpsManager.MODE_ERRORED:
                return "ERRORED";
            case AppOpsManager.MODE_DEFAULT:
                return "DEFAULT";
            case AppOpsManager.MODE_FOREGROUND:
                return "FOREGROUND";
            default:
                return "UNKNOWN(" + mode + ")";
        }
    }
    
    private void sendOpChangeBroadcast(String packageName, int uid, int op, 
                                     OpState oldState, int newMode) {
        Intent intent = new Intent("com.example.systemappopsmonitor.OP_CHANGED");
        intent.putExtra("package_name", packageName);
        intent.putExtra("uid", uid);
        intent.putExtra("op", op);
        intent.putExtra("op_name", AppOpsManager.opToName(op));
        intent.putExtra("old_mode", oldState != null ? oldState.mode : -1);
        intent.putExtra("new_mode", newMode);
        intent.putExtra("timestamp", System.currentTimeMillis());
        
        sendBroadcast(intent);
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        
        try {
            if (mAppOpsService != null) {
                mAppOpsService.stopWatchingMode(mOpCallback);
            }
        } catch (RemoteException e) {
            Log.e(TAG, "Failed to stop watching mode", e);
        }
        
        Log.d(TAG, "System AppOps Monitor Service destroyed");
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
```

## 2. 重要AppOps过滤器

```java
// ImportantOpsFilter.java
package com.example.systemappopsmonitor;

import android.app.AppOpsManager;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public class ImportantOpsFilter {
    
    // 位置相关
    private static final Set<Integer> LOCATION_OPS = new HashSet<>(Arrays.asList(
        AppOpsManager.OP_COARSE_LOCATION,
        AppOpsManager.OP_FINE_LOCATION,
        AppOpsManager.OP_MONITOR_LOCATION,
        AppOpsManager.OP_MONITOR_HIGH_POWER_LOCATION
    ));
    
    // 隐私敏感
    private static final Set<Integer> PRIVACY_OPS = new HashSet<>(Arrays.asList(
        AppOpsManager.OP_CAMERA,
        AppOpsManager.OP_RECORD_AUDIO,
        AppOpsManager.OP_READ_CONTACTS,
        AppOpsManager.OP_WRITE_CONTACTS,
        AppOpsManager.OP_READ_CALL_LOG,
        AppOpsManager.OP_WRITE_CALL_LOG,
        AppOpsManager.OP_READ_CALENDAR,
        AppOpsManager.OP_WRITE_CALENDAR
    ));
    
    // 通信相关
    private static final Set<Integer> COMMUNICATION_OPS = new HashSet<>(Arrays.asList(
        AppOpsManager.OP_READ_SMS,
        AppOpsManager.OP_WRITE_SMS,
        AppOpsManager.OP_SEND_SMS,
        AppOpsManager.OP_RECEIVE_SMS,
        AppOpsManager.OP_CALL_PHONE,
        AppOpsManager.OP_READ_PHONE_STATE
    ));
    
    // 存储相关
    private static final Set<Integer> STORAGE_OPS = new HashSet<>(Arrays.asList(
        AppOpsManager.OP_READ_EXTERNAL_STORAGE,
        AppOpsManager.OP_WRITE_EXTERNAL_STORAGE
    ));
    
    // 系统级操作
    private static final Set<Integer> SYSTEM_OPS = new HashSet<>(Arrays.asList(
        AppOpsManager.OP_WRITE_SETTINGS,
        AppOpsManager.OP_SYSTEM_ALERT_WINDOW,
        AppOpsManager.OP_ACCESS_NOTIFICATIONS,
        AppOpsManager.OP_GET_USAGE_STATS
    ));
    
    public static boolean isImportantOp(int op) {
        return LOCATION_OPS.contains(op) ||
               PRIVACY_OPS.contains(op) ||
               COMMUNICATION_OPS.contains(op) ||
               STORAGE_OPS.contains(op) ||
               SYSTEM_OPS.contains(op);
    }
    
    public static String getOpCategory(int op) {
        if (LOCATION_OPS.contains(op)) return "LOCATION";
        if (PRIVACY_OPS.contains(op)) return "PRIVACY";
        if (COMMUNICATION_OPS.contains(op)) return "COMMUNICATION";
        if (STORAGE_OPS.contains(op)) return "STORAGE";
        if (SYSTEM_OPS.contains(op)) return "SYSTEM";
        return "OTHER";
    }
}
```

## 3. 监控界面Activity

```java
// SystemAppOpsMonitorActivity.java
package com.example.systemappopsmonitor;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;
import android.view.View;
import android.widget.*;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class SystemAppOpsMonitorActivity extends Activity {
    private static final String TAG = "SystemAppOpsMonitor";
    
    private Spinner appSpinner;
    private CheckBox filterImportantCheckBox;
    private Button startButton;
    private Button stopButton;
    private Button monitorAllButton;
    private Button clearButton;
    private TextView monitorStatusText;
    private TextView logTextView;
    private ScrollView scrollView;
    
    private List<AppInfo> installedApps = new ArrayList<>();
    private SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());
    private boolean filterImportantOps = false;
    
    private static class AppInfo {
        String packageName;
        String appName;
        int uid;
        
        @Override
        public String toString() {
            return appName + " (" + packageName + ")";
        }
    }
    
    private BroadcastReceiver opChangeReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String packageName = intent.getStringExtra("package_name");
            int op = intent.getIntExtra("op", -1);
            String opName = intent.getStringExtra("op_name");
            int oldMode = intent.getIntExtra("old_mode", -1);
            int newMode = intent.getIntExtra("new_mode", -1);
            long timestamp = intent.getLongExtra("timestamp", System.currentTimeMillis());
            
            // 过滤非重要ops
            if (filterImportantOps && !ImportantOpsFilter.isImportantOp(op)) {
                return;
            }
            
            displayOpChange(packageName, opName, oldMode, newMode, timestamp);
        }
    };
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_system_monitor);
        
        initViews();
        loadInstalledApps();
        setupListeners();
        
        // 启动服务
        startService(new Intent(this, SystemAppOpsMonitorService.class));
    }
    
    private void initViews() {
        appSpinner = findViewById(R.id.app_spinner);
        filterImportantCheckBox = findViewById(R.id.filter_important_checkbox);
        startButton = findViewById(R.id.start_button);
        stopButton = findViewById(R.id.stop_button);
        monitorAllButton = findViewById(R.id.monitor_all_button);
        clearButton = findViewById(R.id.clear_button);
        monitorStatusText = findViewById(R.id.monitor_status_text);
        logTextView = findViewById(R.id.log_text_view);
        scrollView = findViewById(R.id.scroll_view);
        
        monitorStatusText.setText("Status: Ready");
    }
    
    private void loadInstalledApps() {
        PackageManager pm = getPackageManager();
        List<ApplicationInfo> apps = pm.getInstalledApplications(0);
        
        for (ApplicationInfo app : apps) {
            AppInfo appInfo = new AppInfo();
            appInfo.packageName = app.packageName;
            appInfo.appName = pm.getApplicationLabel(app).toString();
            appInfo.uid = app.uid;
            installedApps.add(appInfo);
        }
        
        ArrayAdapter<AppInfo> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, installedApps);
        appSpinner.setAdapter(adapter);
    }
    
    private void setupListeners() {
        filterImportantCheckBox.setOnCheckedChangeListener((buttonView, isChecked) -> {
            filterImportantOps = isChecked;
        });
        
        startButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            if (selectedApp != null) {
                Intent intent = new Intent(this, SystemAppOpsMonitorService.class);
                intent.putExtra("action", "start_monitor");
                intent.putExtra("package_name", selectedApp.packageName);
                startService(intent);
                
                monitorStatusText.setText("Monitoring: " + selectedApp.packageName);
                addLogEntry("Started monitoring: " + selectedApp.appName, Color.GREEN);
            }
        });
        
        stopButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            if (selectedApp != null) {
                Intent intent = new Intent(this, SystemAppOpsMonitorService.class);
                intent.putExtra("action", "stop_monitor");
                intent.putExtra("package_name", selectedApp.packageName);
                startService(intent);
                
                monitorStatusText.setText("Status: Ready");
                addLogEntry("Stopped monitoring: " + selectedApp.appName, Color.RED);
            }
        });
        
        monitorAllButton.setOnClickListener(v -> {
            Intent intent = new Intent(this, SystemAppOpsMonitorService.class);
            intent.putExtra("action", "monitor_all");
            startService(intent);
            
            monitorStatusText.setText("Monitoring: ALL PACKAGES");
            addLogEntry("Started monitoring all packages", Color.GREEN);
        });
        
        clearButton.setOnClickListener(v -> {
            logTextView.setText("");
        });
    }
    
    private void displayOpChange(String packageName, String opName, int oldMode, int newMode, long timestamp) {
        String time = timeFormat.format(new Date(timestamp));
        String oldModeStr = getModeString(oldMode);
        String newModeStr = getModeString(newMode);
        
        String logEntry = String.format("[%s] %s\n  %s: %s → %s\n",
                time, packageName, opName, oldModeStr, newModeStr);
        
        // 根据权限变化类型设置颜色
        int color = Color.BLACK;
        if (newMode == 0) { // ALLOWED
            color = Color.parseColor("#4CAF50"); // 绿色
        } else if (newMode == 1) { // IGNORED
            color = Color.parseColor("#F44336"); // 红色
        } else if (newMode == 4) { // FOREGROUND
            color = Color.parseColor("#FF9800"); // 橙色
        }
        
        addLogEntry(logEntry, color);
    }
    
    private void addLogEntry(String text, int color) {
        runOnUiThread(() -> {
            SpannableString spannable = new SpannableString(text + "\n");
            spannable.setSpan(new ForegroundColorSpan(color), 0, text.length(), 
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            
            logTextView.append(spannable);
            scrollView.post(() -> scrollView.fullScroll(ScrollView.FOCUS_DOWN));
        });
    }
    
    private String getModeString(int mode) {
        switch (mode) {
            case 0: return "ALLOWED";
            case 1: return "IGNORED";
            case 2: return "ERRORED";
            case 3: return "DEFAULT";
            case 4: return "FOREGROUND";
            default: return "UNKNOWN(" + mode + ")";
        }
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter("com.example.systemappopsmonitor.OP_CHANGED");
        registerReceiver(opChangeReceiver, filter);
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(opChangeReceiver);
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        
        // 停止所有监控
        Intent intent = new Intent(this, SystemAppOpsMonitorService.class);
        intent.putExtra("action", "stop_all");
        startService(intent);
    }
}
```

## 4. 布局文件

```xml
<!-- res/layout/activity_system_monitor.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="System AppOps Monitor"
        android:textSize="22sp"
        android:textStyle="bold"
        android:textColor="@android:color/holo_blue_dark"
        android:layout_marginBottom="16dp" />

    <TextView
        android:id="@+id/monitor_status_text"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Status: Ready"
        android:textSize="16sp"
        android:padding="8dp"
        android:background="#E3F2FD"
        android:layout_marginBottom="16dp" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Select Application:"
        android:textSize="14sp" />

    <Spinner
        android:id="@+id/app_spinner"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginBottom="8dp" />

    <CheckBox
        android:id="@+id/filter_important_checkbox"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Show only important operations"
        android:layout_marginBottom="16dp" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="16dp">

        <Button
            android:id="@+id/start_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Start"
            android:textColor="@android:color/holo_green_dark" />

        <Button
            android:id="@+id/stop_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Stop"
            android:textColor="@android:color/holo_red_dark" />

        <Button
            android:id="@+id/monitor_all_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="All Apps"
            android:textColor="@android:color/holo_orange_dark" />

        <Button
            android:id="@+id/clear_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Clear" />

    </LinearLayout>

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="AppOps Change Log:"
        android:textStyle="bold"
        android:textSize="14sp"
        android:layout_marginBottom="8dp" />

    <ScrollView
        android:id="@+id/scroll_view"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:background="#F5F5F5"
        android:padding="8dp">

        <TextView
            android:id="@+id/log_text_view"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="12sp"
            android:typeface="monospace"
            android:lineSpacingExtra="4dp" />

    </ScrollView>

</LinearLayout>
```

## 5. AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.systemappopsmonitor"
    android:sharedUserId="android.uid.system">
    
    <!-- 系统级权限 -->
    <uses-permission android:name="android.permission.UPDATE_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.GET_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.MANAGE_APP_OPS_MODES" />
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
    
    <application
        android:allowBackup="false"
        android:label="System AppOps Monitor"
        android:theme="@android:style/Theme.Material.Light"
        android:persistent="true">
        
        <activity
            android:name=".SystemAppOpsMonitorActivity"
            android:exported="true"
            android:launchMode="singleTop">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <service
            android:name=".SystemAppOpsMonitorService"
            android:exported="false" />
            
    </application>
</manifest>
```

## 6. 使用说明

### ADB命令使用：
```bash
# 启动对特定应用的监控
adb shell am startservice \
    -n com.example.systemappopsmonitor/.SystemAppOpsMonitorService \
    -e action start_monitor \
    -e package_name com.target.app

# 监控所有应用
adb shell am startservice \
    -n com.example.systemappopsmonitor/.SystemAppOpsMonitorService \
    -e action monitor_all

# 查看日志输出
adb logcat -s SystemAppOpsMonitor:*
```

### 输出示例：
```
╔══════════════════════════════════════════════════════════════════╗
║                     AppOps Permission Changed                     ║
╠══════════════════════════════════════════════════════════════════╣
║ Time     : 2024-11-25 14:30:45                                   ║
║ Package  : com.example.targetapp                                  ║
║ UID      : 10234                                                  ║
║ Operation: CAMERA (26)                                            ║
║ Change   : ALLOWED                  → IGNORED                     ║
╚══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────┐
│ Current AppOps State for: com.example.targetapp                 │
├─────────────────────────────────────────────────────────────────┤
│ FINE_LOCATION       : ALLOWED         (Last: 2024-11-25 14:28:12) │
│ CAMERA              : IGNORED         (Last: 2024-11-25 14:30:45) │
│ RECORD_AUDIO        : FOREGROUND      (Last: 2024-11-25 14:25:33) │
│ READ_CONTACTS       : DEFAULT         (Last: Never)              │
└─────────────────────────────────────────────────────────────────┘
```

这个实现直接使用系统API，无需反射，功能更加稳定和高效。主要特点：

1. **直接使用系统接口**：通过IAppOpsService直接调用系统服务
2. **实时监控**：使用IAppOpsCallback实现实时回调
3. **详细的状态信息**：包括操作时间、持续时间等
4. **美观的日志输出**：使用表格形式展示变化信息
5. **过滤功能**：可以只显示重要的权限变化
6. **多种监控模式**：支持单个应用或所有应用的监控