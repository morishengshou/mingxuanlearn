*Thinking...*

> 用户想要避免使用AppOpsManager的隐藏常量，如OP_CAMERA等，因为这些在Android Studio中无法直接访问。我需要提供替代方案来获取这些常量值。
> 
> 几种替代方案：
> 1. 使用反射获取这些常量
> 2. 直接使用硬编码的数值
> 3. 通过AppOpsManager.opToName()和strOpToOp()等公开API
> 4. 创建自己的常量映射
> 
> 我会提供一个完整的解决方案，使用反射动态获取这些值，同时提供硬编码的备选方案。

我来提供一个不使用隐藏常量的实现方案，通过反射和硬编码值来获取AppOps常量。

## 1. AppOps常量管理器

```java
// AppOpsConstants.java
package com.example.appopslistener;

import android.app.AppOpsManager;
import android.util.Log;
import android.util.SparseArray;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class AppOpsConstants {
    private static final String TAG = "AppOpsConstants";
    
    // 硬编码的常用AppOps值（作为备选）
    private static final Map<String, Integer> KNOWN_OPS = new HashMap<>();
    static {
        // 位置相关
        KNOWN_OPS.put("COARSE_LOCATION", 0);
        KNOWN_OPS.put("FINE_LOCATION", 1);
        KNOWN_OPS.put("GPS", 2);
        KNOWN_OPS.put("MONITOR_LOCATION", 41);
        KNOWN_OPS.put("MONITOR_HIGH_POWER_LOCATION", 42);
        
        // 联系人
        KNOWN_OPS.put("READ_CONTACTS", 4);
        KNOWN_OPS.put("WRITE_CONTACTS", 5);
        
        // 通话记录
        KNOWN_OPS.put("READ_CALL_LOG", 6);
        KNOWN_OPS.put("WRITE_CALL_LOG", 7);
        
        // 日历
        KNOWN_OPS.put("READ_CALENDAR", 8);
        KNOWN_OPS.put("WRITE_CALENDAR", 9);
        
        // WiFi扫描
        KNOWN_OPS.put("WIFI_SCAN", 10);
        
        // 通知
        KNOWN_OPS.put("POST_NOTIFICATION", 11);
        KNOWN_OPS.put("ACCESS_NOTIFICATIONS", 25);
        
        // 电话
        KNOWN_OPS.put("CALL_PHONE", 13);
        KNOWN_OPS.put("READ_PHONE_STATE", 51);
        
        // 短信
        KNOWN_OPS.put("READ_SMS", 14);
        KNOWN_OPS.put("WRITE_SMS", 15);
        KNOWN_OPS.put("RECEIVE_SMS", 16);
        KNOWN_OPS.put("SEND_SMS", 20);
        
        // 存储
        KNOWN_OPS.put("READ_EXTERNAL_STORAGE", 59);
        KNOWN_OPS.put("WRITE_EXTERNAL_STORAGE", 60);
        
        // 设置
        KNOWN_OPS.put("WRITE_SETTINGS", 23);
        KNOWN_OPS.put("SYSTEM_ALERT_WINDOW", 24);
        
        // 相机和音频
        KNOWN_OPS.put("CAMERA", 26);
        KNOWN_OPS.put("RECORD_AUDIO", 27);
        KNOWN_OPS.put("PLAY_AUDIO", 28);
        
        // 剪贴板
        KNOWN_OPS.put("READ_CLIPBOARD", 29);
        KNOWN_OPS.put("WRITE_CLIPBOARD", 30);
        
        // 传感器
        KNOWN_OPS.put("BODY_SENSORS", 56);
        
        // 使用情况
        KNOWN_OPS.put("GET_USAGE_STATS", 43);
        
        // 指纹
        KNOWN_OPS.put("USE_FINGERPRINT", 55);
        
        // 唤醒锁
        KNOWN_OPS.put("WAKE_LOCK", 40);
    }
    
    // 动态获取的ops映射
    private static final SparseArray<String> sOpToName = new SparseArray<>();
    private static final Map<String, Integer> sNameToOp = new HashMap<>();
    private static boolean sInitialized = false;
    
    // 初始化所有可用的AppOps
    public static void initialize() {
        if (sInitialized) {
            return;
        }
        
        try {
            // 通过反射获取所有OP_开头的字段
            Field[] fields = AppOpsManager.class.getDeclaredFields();
            for (Field field : fields) {
                if (field.getName().startsWith("OP_") && field.getType() == int.class) {
                    try {
                        field.setAccessible(true);
                        int opValue = field.getInt(null);
                        String opName = field.getName().substring(3); // 去掉"OP_"前缀
                        
                        sOpToName.put(opValue, opName);
                        sNameToOp.put(opName, opValue);
                        
                        Log.d(TAG, "Found Op: " + opName + " = " + opValue);
                    } catch (IllegalAccessException e) {
                        Log.e(TAG, "Failed to access field: " + field.getName());
                    }
                }
            }
            
            Log.i(TAG, "Initialized " + sOpToName.size() + " AppOps through reflection");
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize AppOps through reflection", e);
        }
        
        // 如果反射失败或获取的ops太少，使用硬编码的值
        if (sOpToName.size() < 20) {
            Log.w(TAG, "Using hardcoded AppOps values as fallback");
            for (Map.Entry<String, Integer> entry : KNOWN_OPS.entrySet()) {
                sNameToOp.put(entry.getKey(), entry.getValue());
                sOpToName.put(entry.getValue(), entry.getKey());
            }
        }
        
        sInitialized = true;
    }
    
    // 获取Op值
    public static int getOpValue(String opName) {
        initialize();
        Integer value = sNameToOp.get(opName);
        if (value != null) {
            return value;
        }
        
        // 尝试从硬编码值中获取
        value = KNOWN_OPS.get(opName);
        return value != null ? value : -1;
    }
    
    // 获取Op名称
    public static String getOpName(int op) {
        initialize();
        String name = sOpToName.get(op);
        if (name != null) {
            return name;
        }
        
        // 尝试使用AppOpsManager的公开API
        try {
            return AppOpsManager.opToName(op);
        } catch (Exception e) {
            return "UNKNOWN_OP_" + op;
        }
    }
    
    // 获取所有重要的监控ops
    public static int[] getImportantOps() {
        return new int[] {
            getOpValue("FINE_LOCATION"),
            getOpValue("COARSE_LOCATION"),
            getOpValue("CAMERA"),
            getOpValue("RECORD_AUDIO"),
            getOpValue("READ_CONTACTS"),
            getOpValue("READ_SMS"),
            getOpValue("READ_CALL_LOG"),
            getOpValue("READ_CALENDAR"),
            getOpValue("READ_PHONE_STATE"),
            getOpValue("CALL_PHONE"),
            getOpValue("ACCESS_NOTIFICATIONS"),
            getOpValue("READ_EXTERNAL_STORAGE"),
            getOpValue("WRITE_EXTERNAL_STORAGE")
        };
    }
    
    // 获取所有需要监控的ops
    public static int[] getAllMonitorOps() {
        initialize();
        
        // 如果通过反射成功获取
        if (sOpToName.size() > 0) {
            int[] ops = new int[sOpToName.size()];
            for (int i = 0; i < sOpToName.size(); i++) {
                ops[i] = sOpToName.keyAt(i);
            }
            return ops;
        }
        
        // 否则返回硬编码的值
        int[] ops = new int[KNOWN_OPS.size()];
        int i = 0;
        for (Integer op : KNOWN_OPS.values()) {
            ops[i++] = op;
        }
        return ops;
    }
    
    // 判断是否是位置相关的Op
    public static boolean isLocationOp(int op) {
        String name = getOpName(op);
        return name.contains("LOCATION") || name.equals("GPS");
    }
    
    // 判断是否是隐私敏感的Op
    public static boolean isPrivacyOp(int op) {
        String name = getOpName(op);
        return name.equals("CAMERA") || 
               name.equals("RECORD_AUDIO") ||
               name.contains("CONTACTS") ||
               name.contains("SMS") ||
               name.contains("CALL_LOG") ||
               name.contains("CALENDAR");
    }
    
    // 获取Op的分类
    public static String getOpCategory(int op) {
        String name = getOpName(op);
        
        if (isLocationOp(op)) {
            return "Location";
        } else if (name.equals("CAMERA") || name.equals("RECORD_AUDIO")) {
            return "Media";
        } else if (name.contains("CONTACTS") || name.contains("CALENDAR")) {
            return "Personal Info";
        } else if (name.contains("SMS") || name.contains("CALL") || name.contains("PHONE")) {
            return "Communication";
        } else if (name.contains("STORAGE")) {
            return "Storage";
        } else if (name.contains("NOTIFICATION")) {
            return "Notification";
        } else {
            return "System";
        }
    }
}
```

## 2. 改进的监听服务

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

import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
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
    
    // 缓存每个包的AppOps状态
    private Map<String, SparseArray<Integer>> mOpsCache = new HashMap<>();
    
    // 日期格式化
    private SimpleDateFormat mDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault());
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "AppOps Listener Service created");
        
        mHandler = new Handler(Looper.getMainLooper());
        mPackageManager = getPackageManager();
        mAppOpsManager = (AppOpsManager) getSystemService(Context.APP_OPS_SERVICE);
        
        // 初始化AppOps常量
        AppOpsConstants.initialize();
        
        // 初始化所有AppOps的监听器
        initializeAllOpListeners();
    }
    
    private void initializeAllOpListeners() {
        // 获取所有需要监听的AppOps
        int[] opsToMonitor = AppOpsConstants.getAllMonitorOps();
        
        int successCount = 0;
        for (int op : opsToMonitor) {
            if (op >= 0 && registerOpListener(op)) {
                successCount++;
            }
        }
        
        Log.i(TAG, "Successfully registered " + successCount + " op listeners");
    }
    
    private boolean registerOpListener(final int op) {
        try {
            OnOpChangedListener listener = new OnOpChangedListener() {
                @Override
                public void onOpChanged(String opStr, String packageName) {
                    // 处理op变化
                    handleOpChanged(op, packageName);
                }
            };
            
            // 使用反射调用startWatchingMode
            Method method = AppOpsManager.class.getMethod(
                    "startWatchingMode", int.class, String.class, OnOpChangedListener.class);
            method.invoke(mAppOpsManager, op, null, listener);
            
            // 保存监听器引用
            mOpListeners.put(op, listener);
            
            Log.d(TAG, "Registered listener for op: " + op + " (" + AppOpsConstants.getOpName(op) + ")");
            return true;
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to register listener for op " + op, e);
            return false;
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
                    
                case "get_current_ops":
                    if (packageName != null) {
                        printCurrentOpsForPackage(packageName);
                    }
                    break;
            }
        }
        
        return START_STICKY;
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
                int currentMode = checkOpNoThrow(op, appInfo.uid, packageName);
                
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
    
    private int checkOpNoThrow(int op, int uid, String packageName) {
        try {
            // 使用反射调用checkOpNoThrow方法
            Method method = AppOpsManager.class.getMethod(
                    "checkOpNoThrow", int.class, int.class, String.class);
            return (int) method.invoke(mAppOpsManager, op, uid, packageName);
        } catch (Exception e) {
            Log.e(TAG, "Failed to check op", e);
            return AppOpsManager.MODE_DEFAULT;
        }
    }
    
    private void printOpChange(String packageName, ApplicationInfo appInfo, int op, 
                              int oldMode, int newMode) {
        String timestamp = mDateFormat.format(new Date());
        String opName = AppOpsConstants.getOpName(op);
        String opCategory = AppOpsConstants.getOpCategory(op);
        String appLabel = mPackageManager.getApplicationLabel(appInfo).toString();
        
        StringBuilder sb = new StringBuilder();
        sb.append("\n╔══════════════════════════════════════════════════════════════════╗\n");
        sb.append("║                  🔔 AppOps Permission Changed                    ║\n");
        sb.append("╠══════════════════════════════════════════════════════════════════╣\n");
        sb.append(String.format("║ Time      : %-52s ║\n", timestamp));
        sb.append(String.format("║ App       : %-52s ║\n", appLabel));
        sb.append(String.format("║ Package   : %-52s ║\n", packageName));
        sb.append(String.format("║ Operation : %-52s ║\n", opName + " (" + op + ")"));
        sb.append(String.format("║ Category  : %-52s ║\n", opCategory));
        sb.append(String.format("║ Change    : %-23s → %-23s ║\n", 
                getModeString(oldMode), getModeString(newMode)));
        sb.append("╚══════════════════════════════════════════════════════════════════╝");
        
        Log.i(TAG, sb.toString());
        
        // 如果是重要的权限变化，添加特别提醒
        if (AppOpsConstants.isPrivacyOp(op)) {
            String emoji = newMode == AppOpsManager.MODE_ALLOWED ? "⚠️" : "✅";
            Log.w(TAG, String.format("%s Privacy-sensitive permission '%s' for '%s' changed to %s",
                    emoji, opName, appLabel, getModeString(newMode)));
        }
    }
    
    private void printCurrentOpsForPackage(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            String appLabel = mPackageManager.getApplicationLabel(appInfo).toString();
            
            StringBuilder sb = new StringBuilder();
            sb.append("\n╔══════════════════════════════════════════════════════════════════╗\n");
            sb.append(String.format("║ Current AppOps State                                             ║\n"));
            sb.append(String.format("║ App: %-59s ║\n", appLabel));
            sb.append(String.format("║ Package: %-55s ║\n", packageName));
            sb.append("╠══════════════════════════════════════════════════════════════════╣\n");
            
            int[] ops = AppOpsConstants.getAllMonitorOps();
            Map<String, StringBuilder> categoryOps = new HashMap<>();
            
            // 按类别分组
            for (int op : ops) {
                if (op < 0) continue;
                
                int mode = checkOpNoThrow(op, appInfo.uid, packageName);
                if (mode != AppOpsManager.MODE_DEFAULT) {
                    String category = AppOpsConstants.getOpCategory(op);
                    String opName = AppOpsConstants.getOpName(op);
                    String modeStr = getModeString(mode);
                    
                    StringBuilder catBuilder = categoryOps.get(category);
                    if (catBuilder == null) {
                        catBuilder = new StringBuilder();
                        categoryOps.put(category, catBuilder);
                    }
                    
                    catBuilder.append(String.format("║   %-28s : %-31s ║\n", opName, modeStr));
                }
            }
            
            // 打印各类别
            if (categoryOps.isEmpty()) {
                sb.append("║ All permissions are using default settings                       ║\n");
            } else {
                for (Map.Entry<String, StringBuilder> entry : categoryOps.entrySet()) {
                    sb.append(String.format("║ [%s]%s ║\n", entry.getKey(), 
                            " ".repeat(61 - entry.getKey().length())));
                    sb.append(entry.getValue());
                }
            }
            
            sb.append("╚══════════════════════════════════════════════════════════════════╝");
            
            Log.i(TAG, sb.toString());
            
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "Package not found: " + packageName);
        }
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
    
    private void cachePackageOps(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            SparseArray<Integer> opsMap = new SparseArray<>();
            
            int[] ops = AppOpsConstants.getAllMonitorOps();
            for (int op : ops) {
                if (op >= 0) {
                    int mode = checkOpNoThrow(op, appInfo.uid, packageName);
                    opsMap.put(op, mode);
                }
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
    
    private String getModeString(int mode) {
        switch (mode) {
            case AppOpsManager.MODE_ALLOWED:
                return "✅ ALLOWED";
            case AppOpsManager.MODE_IGNORED:
                return "❌ DENIED";
            case AppOpsManager.MODE_ERRORED:
                return "⚠️ ERRORED";
            case AppOpsManager.MODE_DEFAULT:
                return "⚪ DEFAULT";
            case 4: // MODE_FOREGROUND
                return "📱 FOREGROUND";
            default:
                return "❓ UNKNOWN(" + mode + ")";
        }
    }
    
    private void sendOpChangeBroadcast(String packageName, int uid, int op,
                                     int oldMode, int newMode) {
        Intent intent = new Intent("com.example.appopslistener.OP_CHANGED");
        intent.putExtra("package_name", packageName);
        intent.putExtra("uid", uid);
        intent.putExtra("op", op);
        intent.putExtra("op_name", AppOpsConstants.getOpName(op));
        intent.putExtra("op_category", AppOpsConstants.getOpCategory(op));
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
            OnOpChangedListener listener = mOpListeners.valueAt(i);
            
            try {
                // 使用反射调用stopWatchingMode
                Method method = AppOpsManager.class.getMethod(
                        "stopWatchingMode", OnOpChangedListener.class);
                method.invoke(mAppOpsManager, listener);
            } catch (Exception e) {
                Log.e(TAG, "Failed to stop watching mode", e);
            }
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

## 3. 其他文件保持不变

上面的Activity和布局文件可以继续使用，不需要修改。

## 主要改进

1. **不使用隐藏常量**：通过反射动态获取AppOpsManager中的常量，并提供硬编码的备选值

2. **自动初始化**：在服务启动时自动获取所有可用的AppOps常量

3. **分类管理**：将AppOps按类别（位置、媒体、通信等）进行分组

4. **更好的日志输出**：使用表情符号和更清晰的格式展示权限变化

5. **兼容性**：即使反射失败，也能通过硬编码值继续工作

这个实现完全避免了直接使用AppOpsManager的隐藏常量，通过反射和硬编码值的组合确保在各种环境下都能正常工作。