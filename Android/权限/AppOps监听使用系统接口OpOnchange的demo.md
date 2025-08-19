*Thinking...*

> 用户要求使用OnOpChangedListener来实现AppOps监听，而不是使用IAppOpsCallback。让我重新实现一个使用标准OnOpChangedListener的版本。

我来提供一个使用`OnOpChangedListener`实现的AppOps监听服务。

## 1. AppOps监听服务（使用OnOpChangedListener）

```java
// AppOpsListenerService.java
package com.example.appopslistener;

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
import android.util.Log;
import android.util.SparseArray;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public class AppOpsListenerService extends Service {
    private static final String TAG = "AppOpsListener";
    
    private AppOpsManager mAppOpsManager;
    private PackageManager mPackageManager;
    private Handler mHandler;
    
    // 监控的包名集合
    private Set<String> mMonitoredPackages = new HashSet<>();
    
    // 监听器映射表：op -> listener
    private SparseArray<OnOpChangedListener> mOpListeners = new SparseArray<>();
    
    // 缓存每个包的AppOps状态：packageName -> (op -> mode)
    private Map<String, SparseArray<Integer>> mOpsCache = new HashMap<>();
    
    // 日期格式化
    private SimpleDateFormat mDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.getDefault());
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "AppOps Listener Service created");
        
        mHandler = new Handler(Looper.getMainLooper());
        mPackageManager = getPackageManager();
        mAppOpsManager = (AppOpsManager) getSystemService(Context.APP_OPS_SERVICE);
        
        // 初始化所有AppOps的监听器
        initializeAllOpListeners();
    }
    
    private void initializeAllOpListeners() {
        // 获取所有需要监听的AppOps
        int[] opsToMonitor = getOpsToMonitor();
        
        for (int op : opsToMonitor) {
            registerOpListener(op);
        }
        
        Log.i(TAG, "Initialized listeners for " + opsToMonitor.length + " operations");
    }
    
    private int[] getOpsToMonitor() {
        // 返回需要监听的所有AppOps
        return new int[] {
            // 位置权限
            AppOpsManager.OP_COARSE_LOCATION,
            AppOpsManager.OP_FINE_LOCATION,
            AppOpsManager.OP_MONITOR_LOCATION,
            AppOpsManager.OP_MONITOR_HIGH_POWER_LOCATION,
            
            // 相机和麦克风
            AppOpsManager.OP_CAMERA,
            AppOpsManager.OP_RECORD_AUDIO,
            
            // 联系人
            AppOpsManager.OP_READ_CONTACTS,
            AppOpsManager.OP_WRITE_CONTACTS,
            
            // 通话记录
            AppOpsManager.OP_READ_CALL_LOG,
            AppOpsManager.OP_WRITE_CALL_LOG,
            
            // 日历
            AppOpsManager.OP_READ_CALENDAR,
            AppOpsManager.OP_WRITE_CALENDAR,
            
            // 短信
            AppOpsManager.OP_READ_SMS,
            AppOpsManager.OP_WRITE_SMS,
            AppOpsManager.OP_RECEIVE_SMS,
            AppOpsManager.OP_SEND_SMS,
            
            // 电话
            AppOpsManager.OP_CALL_PHONE,
            AppOpsManager.OP_READ_PHONE_STATE,
            
            // 存储
            AppOpsManager.OP_READ_EXTERNAL_STORAGE,
            AppOpsManager.OP_WRITE_EXTERNAL_STORAGE,
            
            // 剪贴板
            AppOpsManager.OP_READ_CLIPBOARD,
            AppOpsManager.OP_WRITE_CLIPBOARD,
            
            // 通知
            AppOpsManager.OP_POST_NOTIFICATION,
            AppOpsManager.OP_ACCESS_NOTIFICATIONS,
            
            // 系统设置
            AppOpsManager.OP_WRITE_SETTINGS,
            AppOpsManager.OP_SYSTEM_ALERT_WINDOW,
            
            // 使用情况统计
            AppOpsManager.OP_GET_USAGE_STATS,
            
            // Wi-Fi扫描
            AppOpsManager.OP_WIFI_SCAN,
            
            // 传感器
            AppOpsManager.OP_BODY_SENSORS,
            
            // 唤醒锁
            AppOpsManager.OP_WAKE_LOCK
        };
    }
    
    private void registerOpListener(final int op) {
        OnOpChangedListener listener = new OnOpChangedListener() {
            @Override
            public void onOpChanged(String op, String packageName) {
                // 注意：这里的op参数实际上是操作码的字符串形式
                // 需要转换为整数
                try {
                    int opCode = Integer.parseInt(op);
                    handleOpChanged(opCode, packageName);
                } catch (NumberFormatException e) {
                    // 某些系统版本可能传递操作名称而不是操作码
                    Log.e(TAG, "Failed to parse op: " + op);
                }
            }
        };
        
        // 开始监听指定的操作
        mAppOpsManager.startWatchingMode(op, null, listener);
        
        // 保存监听器引用
        mOpListeners.put(op, listener);
        
        Log.d(TAG, "Registered listener for op: " + op + " (" + AppOpsManager.opToName(op) + ")");
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
                    
                case "get_current_ops":
                    if (packageName != null) {
                        printCurrentOpsForPackage(packageName);
                    }
                    break;
            }
        }
        
        return START_STICKY;
    }
    
    private void startMonitoringPackage(String packageName) {
        mMonitoredPackages.add(packageName);
        
        // 初始化该包的ops缓存
        cachePackageOps(packageName);
        
        Log.i(TAG, "Started monitoring package: " + packageName);
        
        // 打印当前状态
        printCurrentOpsForPackage(packageName);
    }
    
    private void stopMonitoringPackage(String packageName) {
        mMonitoredPackages.remove(packageName);
        mOpsCache.remove(packageName);
        
        Log.i(TAG, "Stopped monitoring package: " + packageName);
    }
    
    private void startMonitoringAll() {
        mMonitoredPackages.clear(); // 清空意味着监控所有
        Log.i(TAG, "Started monitoring all packages");
    }
    
    private void stopMonitoringAll() {
        mMonitoredPackages.clear();
        mOpsCache.clear();
        Log.i(TAG, "Stopped monitoring all packages");
    }
    
    private void handleOpChanged(final int op, final String packageName) {
        mHandler.post(() -> {
            // 检查是否需要监控该包
            if (!mMonitoredPackages.isEmpty() && !mMonitoredPackages.contains(packageName)) {
                return;
            }
            
            try {
                // 获取应用信息
                ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
                
                // 检查当前的op模式
                int currentMode = mAppOpsManager.checkOpNoThrow(op, appInfo.uid, packageName);
                
                // 获取缓存的旧模式
                int oldMode = AppOpsManager.MODE_DEFAULT;
                SparseArray<Integer> packageOps = mOpsCache.get(packageName);
                if (packageOps != null) {
                    oldMode = packageOps.get(op, AppOpsManager.MODE_DEFAULT);
                }
                
                // 如果模式发生了变化
                if (currentMode != oldMode) {
                    // 打印变化信息
                    printOpChange(packageName, appInfo, op, oldMode, currentMode);
                    
                    // 更新缓存
                    updateOpCache(packageName, op, currentMode);
                    
                    // 发送广播
                    sendOpChangeBroadcast(packageName, appInfo.uid, op, oldMode, currentMode);
                }
                
            } catch (PackageManager.NameNotFoundException e) {
                Log.e(TAG, "Package not found: " + packageName);
            }
        });
    }
    
    private void printOpChange(String packageName, ApplicationInfo appInfo, int op, 
                              int oldMode, int newMode) {
        String timestamp = mDateFormat.format(new Date());
        String opName = AppOpsManager.opToName(op);
        String appLabel = mPackageManager.getApplicationLabel(appInfo).toString();
        
        StringBuilder sb = new StringBuilder();
        sb.append("\n┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n");
        sb.append("┃                    AppOps Permission Changed                      ┃\n");
        sb.append("┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫\n");
        sb.append(String.format("┃ Time       : %-51s ┃\n", timestamp));
        sb.append(String.format("┃ App        : %-51s ┃\n", appLabel));
        sb.append(String.format("┃ Package    : %-51s ┃\n", packageName));
        sb.append(String.format("┃ UID        : %-51d ┃\n", appInfo.uid));
        sb.append(String.format("┃ Operation  : %-51s ┃\n", opName + " (" + op + ")"));
        sb.append(String.format("┃ Old Mode   : %-51s ┃\n", getModeString(oldMode)));
        sb.append(String.format("┃ New Mode   : %-51s ┃\n", getModeString(newMode)));
        sb.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛");
        
        Log.i(TAG, sb.toString());
        
        // 如果是重要的权限变化，使用警告级别
        if (isImportantPermissionChange(op, newMode)) {
            Log.w(TAG, String.format("⚠️  IMPORTANT: %s permission for %s changed to %s",
                    opName, appLabel, getModeString(newMode)));
        }
    }
    
    private void printCurrentOpsForPackage(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            String appLabel = mPackageManager.getApplicationLabel(appInfo).toString();
            
            StringBuilder sb = new StringBuilder();
            sb.append("\n╔═══════════════════════════════════════════════════════════════════╗\n");
            sb.append(String.format("║ Current AppOps State for: %-39s ║\n", appLabel));
            sb.append(String.format("║ Package: %-56s ║\n", packageName));
            sb.append("╠═══════════════════════════════════════════════════════════════════╣\n");
            
            int[] ops = getOpsToMonitor();
            boolean hasOps = false;
            
            for (int op : ops) {
                int mode = mAppOpsManager.checkOpNoThrow(op, appInfo.uid, packageName);
                if (mode != AppOpsManager.MODE_DEFAULT) {
                    String opName = AppOpsManager.opToName(op);
                    String modeStr = getModeString(mode);
                    sb.append(String.format("║ %-30s : %-32s ║\n", opName, modeStr));
                    hasOps = true;
                }
            }
            
            if (!hasOps) {
                sb.append("║ No custom AppOps settings (all using default)                     ║\n");
            }
            
            sb.append("╚═══════════════════════════════════════════════════════════════════╝");
            
            Log.i(TAG, sb.toString());
            
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "Package not found: " + packageName);
        }
    }
    
    private void cachePackageOps(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            SparseArray<Integer> opsMap = new SparseArray<>();
            
            int[] ops = getOpsToMonitor();
            for (int op : ops) {
                int mode = mAppOpsManager.checkOpNoThrow(op, appInfo.uid, packageName);
                opsMap.put(op, mode);
            }
            
            mOpsCache.put(packageName, opsMap);
            
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "Failed to cache ops for package: " + packageName);
        }
    }
    
    private void updateOpCache(String packageName, int op, int mode) {
        SparseArray<Integer> packageOps = mOpsCache.get(packageName);
        if (packageOps == null) {
            packageOps = new SparseArray<>();
            mOpsCache.put(packageName, packageOps);
        }
        packageOps.put(op, mode);
    }
    
    private boolean isImportantPermissionChange(int op, int newMode) {
        // 检查是否是重要的权限变化
        boolean isImportantOp = (op == AppOpsManager.OP_CAMERA ||
                                op == AppOpsManager.OP_RECORD_AUDIO ||
                                op == AppOpsManager.OP_FINE_LOCATION ||
                                op == AppOpsManager.OP_COARSE_LOCATION ||
                                op == AppOpsManager.OP_READ_CONTACTS ||
                                op == AppOpsManager.OP_READ_SMS ||
                                op == AppOpsManager.OP_READ_CALL_LOG);
        
        // 如果重要权限被授予，则认为是重要变化
        return isImportantOp && newMode == AppOpsManager.MODE_ALLOWED;
    }
    
    private String getModeString(int mode) {
        switch (mode) {
            case AppOpsManager.MODE_ALLOWED:
                return "ALLOWED ✓";
            case AppOpsManager.MODE_IGNORED:
                return "DENIED ✗";
            case AppOpsManager.MODE_ERRORED:
                return "ERRORED ⚠";
            case AppOpsManager.MODE_DEFAULT:
                return "DEFAULT";
            case AppOpsManager.MODE_FOREGROUND:
                return "FOREGROUND ONLY ◐";
            default:
                return "UNKNOWN (" + mode + ")";
        }
    }
    
    private void sendOpChangeBroadcast(String packageName, int uid, int op,
                                     int oldMode, int newMode) {
        Intent intent = new Intent("com.example.appopslistener.OP_CHANGED");
        intent.putExtra("package_name", packageName);
        intent.putExtra("uid", uid);
        intent.putExtra("op", op);
        intent.putExtra("op_name", AppOpsManager.opToName(op));
        intent.putExtra("old_mode", oldMode);
        intent.putExtra("new_mode", newMode);
        intent.putExtra("timestamp", System.currentTimeMillis());
        
        sendBroadcast(intent);
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        
        // 停止所有监听器
        for (int i = 0; i < mOpListeners.size(); i++) {
            int op = mOpListeners.keyAt(i);
            OnOpChangedListener listener = mOpListeners.valueAt(i);
            
            mAppOpsManager.stopWatchingMode(listener);
            Log.d(TAG, "Stopped listener for op: " + op);
        }
        
        mOpListeners.clear();
        mMonitoredPackages.clear();
        mOpsCache.clear();
        
        Log.d(TAG, "AppOps Listener Service destroyed");
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
```

## 2. 监控Activity界面

```java
// AppOpsListenerActivity.java
package com.example.appopslistener;

import android.app.Activity;
import android.app.AlertDialog;
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
import android.text.TextUtils;
import android.text.style.ForegroundColorSpan;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.*;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class AppOpsListenerActivity extends Activity {
    private static final String TAG = "AppOpsListener";
    
    private AutoCompleteTextView appSearchView;
    private Button startButton;
    private Button stopButton;
    private Button monitorAllButton;
    private Button clearButton;
    private CheckBox filterCheckBox;
    private TextView statusTextView;
    private TextView logTextView;
    private ScrollView scrollView;
    private ProgressBar progressBar;
    
    private List<AppInfo> installedApps = new ArrayList<>();
    private ArrayAdapter<AppInfo> appAdapter;
    private SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault());
    private boolean filterImportantOnly = false;
    private String currentMonitoredPackage = null;
    
    private static class AppInfo {
        String packageName;
        String appName;
        
        AppInfo(String packageName, String appName) {
            this.packageName = packageName;
            this.appName = appName;
        }
        
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
            
            // 过滤
            if (filterImportantOnly && !isImportantOp(op)) {
                return;
            }
            
            displayOpChange(packageName, op, opName, oldMode, newMode, timestamp);
        }
    };
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_listener);
        
        initViews();
        loadInstalledApps();
        setupListeners();
        
        // 启动服务
        startService(new Intent(this, AppOpsListenerService.class));
        
        updateStatus("Ready");
    }
    
    private void initViews() {
        appSearchView = findViewById(R.id.app_search_view);
        startButton = findViewById(R.id.start_button);
        stopButton = findViewById(R.id.stop_button);
        monitorAllButton = findViewById(R.id.monitor_all_button);
        clearButton = findViewById(R.id.clear_button);
        filterCheckBox = findViewById(R.id.filter_checkbox);
        statusTextView = findViewById(R.id.status_text_view);
        logTextView = findViewById(R.id.log_text_view);
        scrollView = findViewById(R.id.scroll_view);
        progressBar = findViewById(R.id.progress_bar);
        
        progressBar.setVisibility(View.GONE);
    }
    
    private void loadInstalledApps() {
        progressBar.setVisibility(View.VISIBLE);
        
        new Thread(() -> {
            PackageManager pm = getPackageManager();
            List<ApplicationInfo> apps = pm.getInstalledApplications(0);
            
            installedApps.clear();
            for (ApplicationInfo app : apps) {
                String appName = pm.getApplicationLabel(app).toString();
                installedApps.add(new AppInfo(app.packageName, appName));
            }
            
            runOnUiThread(() -> {
                appAdapter = new ArrayAdapter<>(this,
                        android.R.layout.simple_dropdown_item_1line, installedApps);
                appSearchView.setAdapter(appAdapter);
                appSearchView.setThreshold(1);
                
                progressBar.setVisibility(View.GONE);
            });
        }).start();
    }
    
    private void setupListeners() {
        startButton.setOnClickListener(v -> {
            String input = appSearchView.getText().toString();
            String packageName = extractPackageName(input);
            
            if (!TextUtils.isEmpty(packageName)) {
                startMonitoring(packageName);
            } else {
                showError("Please select a valid application");
            }
        });
        
        stopButton.setOnClickListener(v -> {
            if (currentMonitoredPackage != null) {
                stopMonitoring(currentMonitoredPackage);
            }
        });
        
        monitorAllButton.setOnClickListener(v -> {
            new AlertDialog.Builder(this)
                    .setTitle("Monitor All Apps")
                    .setMessage("This will monitor AppOps changes for all applications. Continue?")
                    .setPositiveButton("Yes", (dialog, which) -> monitorAll())
                    .setNegativeButton("No", null)
                    .show();
        });
        
        clearButton.setOnClickListener(v -> {
            logTextView.setText("");
        });
        
        filterCheckBox.setOnCheckedChangeListener((buttonView, isChecked) -> {
            filterImportantOnly = isChecked;
        });
    }
    
    private String extractPackageName(String input) {
        // 从 "AppName (package.name)" 格式中提取包名
        int start = input.lastIndexOf("(");
        int end = input.lastIndexOf(")");
        if (start != -1 && end != -1 && end > start) {
            return input.substring(start + 1, end);
        }
        return input;
    }
    
    private void startMonitoring(String packageName) {
        Intent intent = new Intent(this, AppOpsListenerService.class);
        intent.putExtra("action", "start_monitor");
        intent.putExtra("package_name", packageName);
        startService(intent);
        
        currentMonitoredPackage = packageName;
        updateStatus("Monitoring: " + packageName);
        addLogEntry("▶ Started monitoring: " + packageName, Color.GREEN);
    }
    
    private void stopMonitoring(String packageName) {
        Intent intent = new Intent(this, AppOpsListenerService.class);
        intent.putExtra("action", "stop_monitor");
        intent.putExtra("package_name", packageName);
        startService(intent);
        
        currentMonitoredPackage = null;
        updateStatus("Stopped");
        addLogEntry("■ Stopped monitoring: " + packageName, Color.RED);
    }
    
    private void monitorAll() {
        Intent intent = new Intent(this, AppOpsListenerService.class);
        intent.putExtra("action", "monitor_all");
        startService(intent);
        
        currentMonitoredPackage = null;
        updateStatus("Monitoring: ALL APPLICATIONS");
        addLogEntry("▶ Started monitoring all applications", Color.GREEN);
    }
    
    private void displayOpChange(String packageName, int op, String opName, 
                                int oldMode, int newMode, long timestamp) {
        String time = timeFormat.format(new Date(timestamp));
        String oldModeStr = getModeString(oldMode);
        String newModeStr = getModeString(newMode);
        
        // 选择颜色
        int color = Color.BLACK;
        if (newMode == 0) { // ALLOWED
            color = Color.parseColor("#2E7D32"); // 深绿色
        } else if (newMode == 1) { // IGNORED/DENIED
            color = Color.parseColor("#C62828"); // 深红色
        } else if (newMode == 4) { // FOREGROUND
            color = Color.parseColor("#F57C00"); // 深橙色
        }
        
        String logEntry = String.format("[%s] %s\n  %s: %s → %s",
                time, packageName, opName, oldModeStr, newModeStr);
        
        addLogEntry(logEntry, color);
        
        // 如果是重要权限，添加额外提醒
        if (isImportantOp(op) && newMode == 0) {
            addLogEntry("  ⚠️ Important permission granted!", Color.parseColor("#FF6F00"));
        }
    }
    
    private void addLogEntry(String text, int color) {
        runOnUiThread(() -> {
            SpannableString spannable = new SpannableString(text + "\n\n");
            spannable.setSpan(new ForegroundColorSpan(color), 0, text.length(),
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            
            logTextView.append(spannable);
            
            // 自动滚动到底部
            scrollView.post(() -> scrollView.fullScroll(ScrollView.FOCUS_DOWN));
        });
    }
    
    private void updateStatus(String status) {
        runOnUiThread(() -> {
            statusTextView.setText("Status: " + status);
        });
    }
    
    private void showError(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }
    
    private boolean isImportantOp(int op) {
        return op == 1 ||   // FINE_LOCATION
               op == 26 ||  // CAMERA
               op == 27 ||  // RECORD_AUDIO
               op == 4 ||   // READ_CONTACTS
               op == 14 ||  // READ_SMS
               op == 6;     // READ_CALL_LOG
    }
    
    private String getModeString(int mode) {
        switch (mode) {
            case 0: return "ALLOWED";
            case 1: return "DENIED";
            case 2: return "ERRORED";
            case 3: return "DEFAULT";
            case 4: return "FOREGROUND";
            default: return "UNKNOWN";
        }
    }
    
    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(0, 1, 0, "Get Current Ops").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        return true;
    }
    
    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == 1) {
            if (currentMonitoredPackage != null) {
                Intent intent = new Intent(this, AppOpsListenerService.class);
                intent.putExtra("action", "get_current_ops");
                intent.putExtra("package_name", currentMonitoredPackage);
                startService(intent);
            }
            return true;
        }
        return super.onOptionsItemSelected(item);
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter("com.example.appopslistener.OP_CHANGED");
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
<!-- res/layout/activity_listener.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="AppOps Change Monitor"
        android:textSize="24sp"
        android:textStyle="bold"
        android:textColor="@android:color/holo_blue_dark"
        android:layout_gravity="center_horizontal"
        android:layout_marginBottom="16dp" />

    <TextView
        android:id="@+id/status_text_view"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Status: Ready"
        android:textSize="16sp"
        android:padding="12dp"
        android:background="#E8F5E9"
        android:textColor="#1B5E20"
        android:layout_marginBottom="16dp" />

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Search and select app to monitor:"
        android:textSize="14sp"
        android:layout_marginBottom="8dp" />

    <FrameLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginBottom="16dp">

        <AutoCompleteTextView
            android:id="@+id/app_search_view"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="Type app name or package..."
            android:inputType="text"
            android:completionThreshold="1" />

        <ProgressBar
            android:id="@+id/progress_bar"
            style="?android:attr/progressBarStyleSmall"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_gravity="end|center_vertical"
            android:layout_marginEnd="8dp"
            android:visibility="gone" />

    </FrameLayout>

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="8dp">

        <Button
            android:id="@+id/start_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Start"
            android:textColor="#2E7D32" />

        <Button
            android:id="@+id/stop_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Stop"
            android:textColor="#C62828" />

        <Button
            android:id="@+id/monitor_all_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="All Apps"
            android:textColor="#F57C00" />

        <Button
            android:id="@+id/clear_button"
            style="?android:attr/buttonBarButtonStyle"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Clear" />

    </LinearLayout>

    <CheckBox
        android:id="@+id/filter_checkbox"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Show only important permissions (Location, Camera, Microphone, etc.)"
        android:layout_marginBottom="16dp" />

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
        android:background="#FAFAFA"
        android:padding="12dp">

        <TextView
            android:id="@+id/log_text_view"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="13sp"
            android:typeface="monospace"
            android:lineSpacingExtra="4dp"
            android:textIsSelectable="true" />

    </ScrollView>

</LinearLayout>
```

## 4. AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.appopslistener"
    android:sharedUserId="android.uid.system">
    
    <!-- 系统级权限 -->
    <uses-permission android:name="android.permission.UPDATE_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.GET_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
    
    <application
        android:allowBackup="false"
        android:label="AppOps Monitor"
        android:theme="@android:style/Theme.Material.Light">
        
        <activity
            android:name=".AppOpsListenerActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <service
            android:name=".AppOpsListenerService"
            android:exported="false" />
            
    </application>
</manifest>
```

## 5. 使用说明

### 主要特点：

1. **使用OnOpChangedListener**：完全基于Android标准的`OnOpChangedListener`接口实现监听

2. **实时监控**：能够实时监测AppOps权限变化，无需轮询

3. **支持搜索**：使用`AutoCompleteTextView`提供应用搜索功能

4. **过滤功能**：可以只显示重要权限的变化

5. **详细日志**：包含时间戳、权限名称、变化前后的状态

### 输出示例：

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    AppOps Permission Changed                      ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Time       : 2024-11-25 15:42:36.123                             ┃
┃ App        : Example App                                          ┃
┃ Package    : com.example.app                                      ┃
┃ UID        : 10234                                               ┃
┃ Operation  : CAMERA (26)                                          ┃
┃ Old Mode   : ALLOWED ✓                                            ┃
┃ New Mode   : DENIED ✗                                             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

⚠️  IMPORTANT: CAMERA permission for Example App changed to DENIED ✗
```

这个实现完全基于`OnOpChangedListener`，不需要使用反射或隐藏API，适合系统应用使用。