*Thinking...*

> 用户想要一个系统应用Demo，用于修改其他应用的AppOps权限授权状态。AppOps是Android的应用操作权限管理系统，可以用来控制应用的各种操作权限。
> 
> 需要实现的功能：
> 1. 列出应用和AppOps权限
> 2. 获取某个应用的AppOps权限状态
> 3. 修改AppOps权限状态（MODE_ALLOWED, MODE_IGNORED, MODE_ERRORED, MODE_DEFAULT等）
> 4. 需要使用系统级权限和AppOpsManager
> 
> 主要用到的API：
> - AppOpsManager
> - 需要通过反射或者AIDL调用一些隐藏API
> - 需要UPDATE_APP_OPS_STATS权限

我来帮你实现一个系统应用Demo，用于修改其他应用的AppOps权限状态。

## 1. AppOps权限管理服务

```java
// AppOpsManagerService.java
package com.example.appopsmanager;

import android.app.AppOpsManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.IBinder;
import android.os.RemoteException;
import android.util.Log;

import com.android.internal.app.IAppOpsService;
import android.os.ServiceManager;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

public class AppOpsManagerService extends Service {
    private static final String TAG = "AppOpsManager";
    
    private AppOpsManager mAppOpsManager;
    private IAppOpsService mAppOpsService;
    private PackageManager mPackageManager;
    
    // AppOps权限模式
    public static final int MODE_ALLOWED = AppOpsManager.MODE_ALLOWED;
    public static final int MODE_IGNORED = AppOpsManager.MODE_IGNORED;
    public static final int MODE_ERRORED = AppOpsManager.MODE_ERRORED;
    public static final int MODE_DEFAULT = AppOpsManager.MODE_DEFAULT;
    public static final int MODE_FOREGROUND = 4; // AppOpsManager.MODE_FOREGROUND
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "AppOps Manager Service created");
        
        mAppOpsManager = (AppOpsManager) getSystemService(Context.APP_OPS_SERVICE);
        mPackageManager = getPackageManager();
        
        // 获取IAppOpsService
        initAppOpsService();
    }
    
    private void initAppOpsService() {
        try {
            IBinder binder = ServiceManager.getService(Context.APP_OPS_SERVICE);
            mAppOpsService = IAppOpsService.Stub.asInterface(binder);
            Log.d(TAG, "IAppOpsService initialized");
        } catch (Exception e) {
            Log.e(TAG, "Failed to get IAppOpsService", e);
        }
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getStringExtra("action");
            
            if ("set_op".equals(action)) {
                String packageName = intent.getStringExtra("package_name");
                int op = intent.getIntExtra("op", -1);
                int mode = intent.getIntExtra("mode", MODE_DEFAULT);
                int uid = intent.getIntExtra("uid", -1);
                
                setAppOp(packageName, op, mode, uid);
                
            } else if ("get_ops".equals(action)) {
                String packageName = intent.getStringExtra("package_name");
                getAppOps(packageName);
                
            } else if ("reset_all".equals(action)) {
                String packageName = intent.getStringExtra("package_name");
                resetAllOps(packageName);
            }
        }
        
        return START_NOT_STICKY;
    }
    
    // 设置AppOp权限
    private void setAppOp(String packageName, int op, int mode, int uid) {
        try {
            if (uid == -1) {
                ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
                uid = appInfo.uid;
            }
            
            // 方法1：使用反射调用setMode
            Method setModeMethod = mAppOpsManager.getClass().getDeclaredMethod(
                    "setMode", int.class, int.class, String.class, int.class);
            setModeMethod.setAccessible(true);
            setModeMethod.invoke(mAppOpsManager, op, uid, packageName, mode);
            
            Log.i(TAG, String.format("Set AppOp: %s[%d] op=%d mode=%d", 
                    packageName, uid, op, mode));
            
            // 发送结果广播
            sendResultBroadcast(true, "set_op", packageName, op, mode, null);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to set AppOp", e);
            sendResultBroadcast(false, "set_op", packageName, op, mode, e.getMessage());
        }
    }
    
    // 获取应用的所有AppOps状态
    private void getAppOps(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            int uid = appInfo.uid;
            
            // 使用反射获取所有ops
            Method getOpsForPackageMethod = mAppOpsManager.getClass().getDeclaredMethod(
                    "getOpsForPackage", int.class, String.class, int[].class);
            getOpsForPackageMethod.setAccessible(true);
            
            List<Object> packageOps = (List<Object>) getOpsForPackageMethod.invoke(
                    mAppOpsManager, uid, packageName, null);
            
            if (packageOps != null && !packageOps.isEmpty()) {
                Object ops = packageOps.get(0);
                Method getOpsMethod = ops.getClass().getDeclaredMethod("getOps");
                getOpsMethod.setAccessible(true);
                
                List<Object> opEntries = (List<Object>) getOpsMethod.invoke(ops);
                
                for (Object opEntry : opEntries) {
                    parseOpEntry(packageName, opEntry);
                }
            }
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to get AppOps", e);
        }
    }
    
    private void parseOpEntry(String packageName, Object opEntry) {
        try {
            Method getOpMethod = opEntry.getClass().getDeclaredMethod("getOp");
            Method getModeMethod = opEntry.getClass().getDeclaredMethod("getMode");
            
            getOpMethod.setAccessible(true);
            getModeMethod.setAccessible(true);
            
            int op = (int) getOpMethod.invoke(opEntry);
            int mode = (int) getModeMethod.invoke(opEntry);
            
            String opName = getOpName(op);
            String modeName = getModeName(mode);
            
            Log.i(TAG, String.format("%s: Op[%d]=%s Mode=%s", 
                    packageName, op, opName, modeName));
            
            // 发送AppOp状态广播
            Intent intent = new Intent("com.example.appopsmanager.OP_STATUS");
            intent.putExtra("package_name", packageName);
            intent.putExtra("op", op);
            intent.putExtra("op_name", opName);
            intent.putExtra("mode", mode);
            intent.putExtra("mode_name", modeName);
            sendBroadcast(intent);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to parse OpEntry", e);
        }
    }
    
    // 重置应用的所有AppOps为默认值
    private void resetAllOps(String packageName) {
        try {
            ApplicationInfo appInfo = mPackageManager.getApplicationInfo(packageName, 0);
            
            // 使用反射调用resetAllModes
            Method resetMethod = mAppOpsManager.getClass().getDeclaredMethod(
                    "resetAllModes", int.class, String.class);
            resetMethod.setAccessible(true);
            resetMethod.invoke(mAppOpsManager, appInfo.uid, packageName);
            
            Log.i(TAG, "Reset all AppOps for " + packageName);
            sendResultBroadcast(true, "reset_all", packageName, -1, -1, null);
            
        } catch (Exception e) {
            Log.e(TAG, "Failed to reset AppOps", e);
            sendResultBroadcast(false, "reset_all", packageName, -1, -1, e.getMessage());
        }
    }
    
    // 获取Op名称
    private String getOpName(int op) {
        try {
            Field[] fields = AppOpsManager.class.getDeclaredFields();
            for (Field field : fields) {
                if (field.getName().startsWith("OP_") && 
                    field.getType() == int.class) {
                    field.setAccessible(true);
                    if (field.getInt(null) == op) {
                        return field.getName();
                    }
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to get op name", e);
        }
        return "OP_" + op;
    }
    
    private String getModeName(int mode) {
        switch (mode) {
            case MODE_ALLOWED: return "ALLOWED";
            case MODE_IGNORED: return "IGNORED";
            case MODE_ERRORED: return "ERRORED";
            case MODE_DEFAULT: return "DEFAULT";
            case MODE_FOREGROUND: return "FOREGROUND";
            default: return "UNKNOWN(" + mode + ")";
        }
    }
    
    private void sendResultBroadcast(boolean success, String action, String packageName,
                                   int op, int mode, String error) {
        Intent intent = new Intent("com.example.appopsmanager.RESULT");
        intent.putExtra("success", success);
        intent.putExtra("action", action);
        intent.putExtra("package_name", packageName);
        intent.putExtra("op", op);
        intent.putExtra("mode", mode);
        if (error != null) {
            intent.putExtra("error", error);
        }
        sendBroadcast(intent);
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
```

## 2. AppOps常量定义类

```java
// AppOpsConstants.java
package com.example.appopsmanager;

import android.app.AppOpsManager;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class AppOpsConstants {
    // 常用的AppOps操作码
    public static final int OP_COARSE_LOCATION = 0;
    public static final int OP_FINE_LOCATION = 1;
    public static final int OP_GPS = 2;
    public static final int OP_VIBRATE = 3;
    public static final int OP_READ_CONTACTS = 4;
    public static final int OP_WRITE_CONTACTS = 5;
    public static final int OP_READ_CALL_LOG = 6;
    public static final int OP_WRITE_CALL_LOG = 7;
    public static final int OP_READ_CALENDAR = 8;
    public static final int OP_WRITE_CALENDAR = 9;
    public static final int OP_WIFI_SCAN = 10;
    public static final int OP_POST_NOTIFICATION = 11;
    public static final int OP_NEIGHBORING_CELLS = 12;
    public static final int OP_CALL_PHONE = 13;
    public static final int OP_READ_SMS = 14;
    public static final int OP_WRITE_SMS = 15;
    public static final int OP_RECEIVE_SMS = 16;
    public static final int OP_RECEIVE_EMERGECY_SMS = 17;
    public static final int OP_RECEIVE_MMS = 18;
    public static final int OP_RECEIVE_WAP_PUSH = 19;
    public static final int OP_SEND_SMS = 20;
    public static final int OP_READ_ICC_SMS = 21;
    public static final int OP_WRITE_ICC_SMS = 22;
    public static final int OP_WRITE_SETTINGS = 23;
    public static final int OP_SYSTEM_ALERT_WINDOW = 24;
    public static final int OP_ACCESS_NOTIFICATIONS = 25;
    public static final int OP_CAMERA = 26;
    public static final int OP_RECORD_AUDIO = 27;
    public static final int OP_PLAY_AUDIO = 28;
    public static final int OP_READ_CLIPBOARD = 29;
    public static final int OP_WRITE_CLIPBOARD = 30;
    public static final int OP_TAKE_MEDIA_BUTTONS = 31;
    public static final int OP_TAKE_AUDIO_FOCUS = 32;
    public static final int OP_AUDIO_MASTER_VOLUME = 33;
    public static final int OP_AUDIO_VOICE_VOLUME = 34;
    public static final int OP_AUDIO_RING_VOLUME = 35;
    public static final int OP_AUDIO_MEDIA_VOLUME = 36;
    public static final int OP_AUDIO_ALARM_VOLUME = 37;
    public static final int OP_AUDIO_NOTIFICATION_VOLUME = 38;
    public static final int OP_AUDIO_BLUETOOTH_VOLUME = 39;
    public static final int OP_WAKE_LOCK = 40;
    public static final int OP_MONITOR_LOCATION = 41;
    public static final int OP_MONITOR_HIGH_POWER_LOCATION = 42;
    public static final int OP_GET_USAGE_STATS = 43;
    
    private static Map<Integer, String> sOpNames = new HashMap<>();
    private static Map<String, Integer> sNameToOp = new HashMap<>();
    
    static {
        initializeOpMaps();
    }
    
    private static void initializeOpMaps() {
        // 通过反射获取所有OP常量
        try {
            Field[] fields = AppOpsManager.class.getDeclaredFields();
            for (Field field : fields) {
                if (field.getName().startsWith("OP_") && 
                    field.getType() == int.class) {
                    field.setAccessible(true);
                    int value = field.getInt(null);
                    String name = field.getName();
                    sOpNames.put(value, name);
                    sNameToOp.put(name, value);
                }
            }
        } catch (Exception e) {
            // 使用默认映射
            sOpNames.put(OP_COARSE_LOCATION, "OP_COARSE_LOCATION");
            sOpNames.put(OP_FINE_LOCATION, "OP_FINE_LOCATION");
            sOpNames.put(OP_CAMERA, "OP_CAMERA");
            sOpNames.put(OP_RECORD_AUDIO, "OP_RECORD_AUDIO");
            // ... 添加更多映射
        }
    }
    
    public static String getOpName(int op) {
        return sOpNames.getOrDefault(op, "OP_" + op);
    }
    
    public static int getOpByName(String name) {
        return sNameToOp.getOrDefault(name, -1);
    }
}
```

## 3. 主界面Activity

```java
// MainActivity.java
package com.example.appopsmanager;

import android.app.Activity;
import android.app.AppOpsManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.view.View;
import android.widget.*;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {
    private static final String TAG = "AppOpsManager";
    
    private Spinner appSpinner;
    private Spinner opSpinner;
    private RadioGroup modeRadioGroup;
    private Button setButton;
    private Button getOpsButton;
    private Button resetButton;
    private TextView statusText;
    private ListView opsListView;
    
    private List<AppInfo> installedApps = new ArrayList<>();
    private List<OpInfo> opsList = new ArrayList<>();
    private ArrayAdapter<OpStatus> opsAdapter;
    private List<OpStatus> currentOps = new ArrayList<>();
    
    private static class AppInfo {
        String packageName;
        String appName;
        int uid;
        
        @Override
        public String toString() {
            return appName + " (" + packageName + ")";
        }
    }
    
    private static class OpInfo {
        int op;
        String name;
        String description;
        
        @Override
        public String toString() {
            return name + " - " + description;
        }
    }
    
    private static class OpStatus {
        int op;
        String opName;
        int mode;
        String modeName;
        
        @Override
        public String toString() {
            return opName + ": " + modeName;
        }
    }
    
    private BroadcastReceiver resultReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if ("com.example.appopsmanager.RESULT".equals(intent.getAction())) {
                boolean success = intent.getBooleanExtra("success", false);
                String action = intent.getStringExtra("action");
                String error = intent.getStringExtra("error");
                
                String status = success ? "SUCCESS" : "FAILED";
                if (error != null) {
                    status += ": " + error;
                }
                statusText.setText(status);
                
            } else if ("com.example.appopsmanager.OP_STATUS".equals(intent.getAction())) {
                int op = intent.getIntExtra("op", -1);
                String opName = intent.getStringExtra("op_name");
                int mode = intent.getIntExtra("mode", -1);
                String modeName = intent.getStringExtra("mode_name");
                
                OpStatus opStatus = new OpStatus();
                opStatus.op = op;
                opStatus.opName = opName;
                opStatus.mode = mode;
                opStatus.modeName = modeName;
                
                currentOps.add(opStatus);
                opsAdapter.notifyDataSetChanged();
            }
        }
    };
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        initViews();
        loadData();
        setupListeners();
    }
    
    private void initViews() {
        appSpinner = findViewById(R.id.app_spinner);
        opSpinner = findViewById(R.id.op_spinner);
        modeRadioGroup = findViewById(R.id.mode_radio_group);
        setButton = findViewById(R.id.set_button);
        getOpsButton = findViewById(R.id.get_ops_button);
        resetButton = findViewById(R.id.reset_button);
        statusText = findViewById(R.id.status_text);
        opsListView = findViewById(R.id.ops_list_view);
        
        opsAdapter = new ArrayAdapter<>(this, 
                android.R.layout.simple_list_item_1, currentOps);
        opsListView.setAdapter(opsAdapter);
    }
    
    private void loadData() {
        // 加载已安装应用
        loadInstalledApps();
        
        // 加载AppOps列表
        loadAppOps();
        
        // 设置适配器
        ArrayAdapter<AppInfo> appAdapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, installedApps);
        appSpinner.setAdapter(appAdapter);
        
        ArrayAdapter<OpInfo> opAdapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, opsList);
        opSpinner.setAdapter(opAdapter);
    }
    
    private void loadInstalledApps() {
        PackageManager pm = getPackageManager();
        List<ApplicationInfo> apps = pm.getInstalledApplications(0);
        
        for (ApplicationInfo app : apps) {
            // 可以选择过滤系统应用
            AppInfo appInfo = new AppInfo();
            appInfo.packageName = app.packageName;
            appInfo.appName = pm.getApplicationLabel(app).toString();
            appInfo.uid = app.uid;
            installedApps.add(appInfo);
        }
    }
    
    private void loadAppOps() {
        // 位置相关
        addOp(AppOpsConstants.OP_COARSE_LOCATION, "粗略位置", "访问粗略位置信息");
        addOp(AppOpsConstants.OP_FINE_LOCATION, "精确位置", "访问精确位置信息");
        addOp(AppOpsConstants.OP_MONITOR_LOCATION, "监控位置", "监控位置信息");
        addOp(AppOpsConstants.OP_MONITOR_HIGH_POWER_LOCATION, "高功耗位置", "使用高功耗位置服务");
        
        // 相机和音频
        addOp(AppOpsConstants.OP_CAMERA, "相机", "使用相机");
        addOp(AppOpsConstants.OP_RECORD_AUDIO, "录音", "录制音频");
        
        // 通讯录和日历
        addOp(AppOpsConstants.OP_READ_CONTACTS, "读取联系人", "读取联系人信息");
        addOp(AppOpsConstants.OP_WRITE_CONTACTS, "写入联系人", "修改联系人信息");
        addOp(AppOpsConstants.OP_READ_CALENDAR, "读取日历", "读取日历事件");
        addOp(AppOpsConstants.OP_WRITE_CALENDAR, "写入日历", "修改日历事件");
        
        // 电话和短信
        addOp(AppOpsConstants.OP_CALL_PHONE, "拨打电话", "直接拨打电话");
        addOp(AppOpsConstants.OP_READ_SMS, "读取短信", "读取短信内容");
        addOp(AppOpsConstants.OP_SEND_SMS, "发送短信", "发送短信");
        
        // 系统设置
        addOp(AppOpsConstants.OP_WRITE_SETTINGS, "修改系统设置", "修改系统设置");
        addOp(AppOpsConstants.OP_SYSTEM_ALERT_WINDOW, "悬浮窗", "显示系统悬浮窗");
        
        // 通知
        addOp(AppOpsConstants.OP_POST_NOTIFICATION, "发送通知", "发送通知");
        addOp(AppOpsConstants.OP_ACCESS_NOTIFICATIONS, "访问通知", "访问通知内容");
        
        // 剪贴板
        addOp(AppOpsConstants.OP_READ_CLIPBOARD, "读取剪贴板", "读取剪贴板内容");
        addOp(AppOpsConstants.OP_WRITE_CLIPBOARD, "写入剪贴板", "修改剪贴板内容");
        
        // 使用统计
        addOp(AppOpsConstants.OP_GET_USAGE_STATS, "使用情况统计", "获取应用使用情况统计");
    }
    
    private void addOp(int op, String name, String description) {
        OpInfo opInfo = new OpInfo();
        opInfo.op = op;
        opInfo.name = name;
        opInfo.description = description;
        opsList.add(opInfo);
    }
    
    private void setupListeners() {
        setButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            OpInfo selectedOp = (OpInfo) opSpinner.getSelectedItem();
            
            if (selectedApp == null || selectedOp == null) {
                return;
            }
            
            int mode = getSelectedMode();
            
            Intent intent = new Intent(this, AppOpsManagerService.class);
            intent.putExtra("action", "set_op");
            intent.putExtra("package_name", selectedApp.packageName);
            intent.putExtra("uid", selectedApp.uid);
            intent.putExtra("op", selectedOp.op);
            intent.putExtra("mode", mode);
            
            startService(intent);
        });
        
        getOpsButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            if (selectedApp == null) {
                return;
            }
            
            currentOps.clear();
            opsAdapter.notifyDataSetChanged();
            
            Intent intent = new Intent(this, AppOpsManagerService.class);
            intent.putExtra("action", "get_ops");
            intent.putExtra("package_name", selectedApp.packageName);
            
            startService(intent);
        });
        
        resetButton.setOnClickListener(v -> {
            AppInfo selectedApp = (AppInfo) appSpinner.getSelectedItem();
            if (selectedApp == null) {
                return;
            }
            
            Intent intent = new Intent(this, AppOpsManagerService.class);
            intent.putExtra("action", "reset_all");
            intent.putExtra("package_name", selectedApp.packageName);
            
            startService(intent);
        });
    }
    
    private int getSelectedMode() {
        int checkedId = modeRadioGroup.getCheckedRadioButtonId();
        
        if (checkedId == R.id.mode_allowed) {
            return AppOpsManagerService.MODE_ALLOWED;
        } else if (checkedId == R.id.mode_ignored) {
            return AppOpsManagerService.MODE_IGNORED;
        } else if (checkedId == R.id.mode_errored) {
            return AppOpsManagerService.MODE_ERRORED;
        } else if (checkedId == R.id.mode_default) {
            return AppOpsManagerService.MODE_DEFAULT;
        } else if (checkedId == R.id.mode_foreground) {
            return AppOpsManagerService.MODE_FOREGROUND;
        }
        
        return AppOpsManagerService.MODE_DEFAULT;
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter();
        filter.addAction("com.example.appopsmanager.RESULT");
        filter.addAction("com.example.appopsmanager.OP_STATUS");
        registerReceiver(resultReceiver, filter);
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(resultReceiver);
    }
}
```

## 4. 布局文件

```xml
<!-- res/layout/activity_main.xml -->
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">
    
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="16dp">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="AppOps Manager"
            android:textSize="20sp"
            android:textStyle="bold"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Select Application:" />

        <Spinner
            android:id="@+id/app_spinner"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Select Operation:" />

        <Spinner
            android:id="@+id/op_spinner"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Select Mode:" />

        <RadioGroup
            android:id="@+id/mode_radio_group"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:layout_marginBottom="16dp">

            <RadioButton
                android:id="@+id/mode_allowed"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="ALLOWED - 允许"
                android:checked="true" />

            <RadioButton
                android:id="@+id/mode_ignored"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="IGNORED - 忽略/拒绝" />

            <RadioButton
                android:id="@+id/mode_errored"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="ERRORED - 错误" />

            <RadioButton
                android:id="@+id/mode_default"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="DEFAULT - 默认" />

            <RadioButton
                android:id="@+id/mode_foreground"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="FOREGROUND - 仅前台" />

        </RadioGroup>

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginBottom="16dp">

            <Button
                android:id="@+id/set_button"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="Set Op"
                android:layout_marginEnd="8dp" />

            <Button
                android:id="@+id/get_ops_button"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="Get Ops"
                android:layout_marginEnd="8dp" />

            <Button
                android:id="@+id/reset_button"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="Reset All" />

        </LinearLayout>

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Status:"
            android:textStyle="bold" />

        <TextView
            android:id="@+id/status_text"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="Ready"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Current AppOps:"
            android:textStyle="bold" />

        <ListView
            android:id="@+id/ops_list_view"
            android:layout_width="match_parent"
            android:layout_height="300dp"
            android:background="#f0f0f0" />

    </LinearLayout>
</ScrollView>
```

## 5. AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.appopsmanager"
    android:sharedUserId="android.uid.system">
    
    <!-- 系统级权限 -->
    <uses-permission android:name="android.permission.UPDATE_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.MANAGE_APP_OPS_MODES" />
    <uses-permission android:name="android.permission.MANAGE_APP_OPS_RESTRICTIONS" />
    <uses-permission android:name="android.permission.GET_APP_OPS_STATS" />
    <uses-permission android:name="android.permission.INTERACT_ACROSS_USERS" />
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
    
    <application
        android:allowBackup="false"
        android:label="AppOps Manager"
        android:theme="@android:style/Theme.Material.Light">
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <service
            android:name=".AppOpsManagerService"
            android:exported="false" />
            
    </application>
</manifest>
```

## 6. 使用示例

### 通过ADB命令使用：

```bash
# 设置应用的相机权限为拒绝
adb shell am startservice \
    -n com.example.appopsmanager/.AppOpsManagerService \
    -e action set_op \
    -e package_name com.target.app \
    -e op 26 \
    -e mode 1

# 获取应用的所有AppOps状态
adb shell am startservice \
    -n com.example.appopsmanager/.AppOpsManagerService \
    -e action get_ops \
    -e package_name com.target.app

# 重置应用的所有AppOps为默认值
adb shell am startservice \
    -n com.example.appopsmanager/.AppOpsManagerService \
    -e action reset_all \
    -e package_name com.target.app
```

## 重要说明

1. **系统签名要求**：此应用需要使用平台密钥签名，并声明`android.uid.system`。

2. **AppOps模式说明**：
   - **MODE_ALLOWED (0)**: 允许操作
   - **MODE_IGNORED (1)**: 忽略操作（相当于拒绝）
   - **MODE_ERRORED (2)**: 操作导致错误
   - **MODE_DEFAULT (3)**: 使用默认设置
   - **MODE_FOREGROUND (4)**: 仅在前台允许

3. **权限与AppOps的关系**：
   - AppOps是比运行时权限更底层的控制机制
   - 即使应用有运行时权限，AppOps仍可以阻止其操作
   - 修改AppOps不会改变权限的授予状态

4. **注意事项**：
   - 修改AppOps可能影响应用的正常运行
   - 某些AppOps操作需要特定的系统权限
   - 不同Android版本的AppOps实现可能有差异

这个Demo提供了完整的AppOps管理功能，可以查看和修改任意应用的AppOps权限状态。