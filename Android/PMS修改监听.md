*Thinking...*

> 用户想要一个Android服务来监测应用权限变化，特别强调：
> 1. 不使用轮询方式，要用Observer模式
> 2. 监测PMS（PackageManagerService）上的权限变动
> 3. 服务打包成APK通过ADB安装
> 
> 对于监听权限变化，Android提供了几种方式：
> 1. PackageManager.OnPermissionsChangedListener（API 23+）
> 2. ContentObserver监听Settings数据库
> 3. BroadcastReceiver监听包相关广播
> 
> 最合适的是使用OnPermissionsChangedListener，这是专门为监听权限变化设计的。

我来帮你实现一个使用Observer模式监听权限变化的Android服务，避免轮询以节省性能。

## 1. 核心权限监测服务

```java
// PermissionObserverService.java
package com.example.permissionobserver;

import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.OnPermissionsChangedListener;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

public class PermissionObserverService extends Service {
    private static final String TAG = "PermissionObserver";
    
    private PackageManager packageManager;
    private Handler mainHandler;
    private Map<Integer, String> uidToPackageMap = new HashMap<>();
    private Map<String, String[]> packagePermissionsCache = new HashMap<>();
    
    // 权限变化监听器
    private OnPermissionsChangedListener permissionsListener = new OnPermissionsChangedListener() {
        @Override
        public void onPermissionsChanged(int uid) {
            Log.d(TAG, "Permissions changed for UID: " + uid);
            handlePermissionChange(uid);
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "Service created");
        
        packageManager = getPackageManager();
        mainHandler = new Handler(Looper.getMainLooper());
        
        // 注册权限变化监听器 (需要 API 23+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            packageManager.addOnPermissionsChangeListener(permissionsListener);
            Log.d(TAG, "Permission listener registered");
        }
        
        // 初始化已安装应用的权限状态
        initializeInstalledApps();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "Service started");
        
        // 如果指定了特定包名，只监测该应用
        if (intent != null && intent.hasExtra("package_name")) {
            String packageName = intent.getStringExtra("package_name");
            cacheAppPermissions(packageName);
        }
        
        return START_STICKY;
    }

    private void initializeInstalledApps() {
        // 获取所有已安装应用的权限状态
        new Thread(() -> {
            try {
                for (PackageInfo packageInfo : packageManager.getInstalledPackages(
                        PackageManager.GET_PERMISSIONS)) {
                    if (packageInfo.applicationInfo != null) {
                        int uid = packageInfo.applicationInfo.uid;
                        String packageName = packageInfo.packageName;
                        uidToPackageMap.put(uid, packageName);
                        cacheAppPermissions(packageName);
                    }
                }
                Log.d(TAG, "Initialized " + uidToPackageMap.size() + " apps");
            } catch (Exception e) {
                Log.e(TAG, "Error initializing apps", e);
            }
        }).start();
    }

    private void handlePermissionChange(int uid) {
        mainHandler.post(() -> {
            try {
                String packageName = getPackageNameForUid(uid);
                if (packageName == null) {
                    Log.w(TAG, "Unknown package for UID: " + uid);
                    return;
                }
                
                Log.d(TAG, "Checking permissions for: " + packageName);
                
                // 获取当前权限状态
                PackageInfo packageInfo = packageManager.getPackageInfo(packageName,
                        PackageManager.GET_PERMISSIONS);
                
                if (packageInfo.requestedPermissions == null) {
                    return;
                }
                
                // 比较权限变化
                String[] cachedPermissions = packagePermissionsCache.get(packageName);
                String[] currentPermissions = getCurrentGrantedPermissions(packageInfo);
                
                if (cachedPermissions != null) {
                    reportPermissionChanges(packageName, cachedPermissions, currentPermissions);
                }
                
                // 更新缓存
                packagePermissionsCache.put(packageName, currentPermissions);
                
            } catch (Exception e) {
                Log.e(TAG, "Error handling permission change", e);
            }
        });
    }

    private String getPackageNameForUid(int uid) {
        // 先从缓存查找
        String packageName = uidToPackageMap.get(uid);
        if (packageName != null) {
            return packageName;
        }
        
        // 如果缓存中没有，尝试获取
        String[] packages = packageManager.getPackagesForUid(uid);
        if (packages != null && packages.length > 0) {
            packageName = packages[0];
            uidToPackageMap.put(uid, packageName);
            return packageName;
        }
        
        return null;
    }

    private void cacheAppPermissions(String packageName) {
        try {
            PackageInfo packageInfo = packageManager.getPackageInfo(packageName,
                    PackageManager.GET_PERMISSIONS);
            String[] grantedPermissions = getCurrentGrantedPermissions(packageInfo);
            packagePermissionsCache.put(packageName, grantedPermissions);
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "Package not found: " + packageName);
        }
    }

    private String[] getCurrentGrantedPermissions(PackageInfo packageInfo) {
        if (packageInfo.requestedPermissions == null) {
            return new String[0];
        }
        
        StringBuilder grantedList = new StringBuilder();
        
        for (int i = 0; i < packageInfo.requestedPermissions.length; i++) {
            if ((packageInfo.requestedPermissionsFlags[i] & 
                 PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0) {
                if (grantedList.length() > 0) {
                    grantedList.append(",");
                }
                grantedList.append(packageInfo.requestedPermissions[i]);
            }
        }
        
        return grantedList.toString().split(",");
    }

    private void reportPermissionChanges(String packageName, String[] oldPermissions, 
                                       String[] newPermissions) {
        // 检查新授予的权限
        for (String permission : newPermissions) {
            if (!Arrays.asList(oldPermissions).contains(permission)) {
                String message = String.format("[GRANTED] %s: %s", packageName, permission);
                Log.i(TAG, message);
                sendPermissionChangeBroadcast(packageName, permission, true);
            }
        }
        
        // 检查被撤销的权限
        for (String permission : oldPermissions) {
            if (!Arrays.asList(newPermissions).contains(permission)) {
                String message = String.format("[REVOKED] %s: %s", packageName, permission);
                Log.i(TAG, message);
                sendPermissionChangeBroadcast(packageName, permission, false);
            }
        }
    }

    private void sendPermissionChangeBroadcast(String packageName, String permission, 
                                              boolean granted) {
        Intent intent = new Intent("com.example.permissionobserver.PERMISSION_CHANGED");
        intent.putExtra("package_name", packageName);
        intent.putExtra("permission", permission);
        intent.putExtra("granted", granted);
        intent.putExtra("timestamp", System.currentTimeMillis());
        sendBroadcast(intent);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        
        // 移除权限监听器
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            packageManager.removeOnPermissionsChangeListener(permissionsListener);
            Log.d(TAG, "Permission listener unregistered");
        }
        
        Log.d(TAG, "Service destroyed");
    }
}
```

## 2. 增强版本：使用ContentObserver监听Settings变化

```java
// SettingsPermissionObserver.java
package com.example.permissionobserver;

import android.content.Context;
import android.database.ContentObserver;
import android.net.Uri;
import android.os.Handler;
import android.provider.Settings;
import android.util.Log;

public class SettingsPermissionObserver extends ContentObserver {
    private static final String TAG = "SettingsObserver";
    private Context context;
    private PermissionChangeCallback callback;
    
    public interface PermissionChangeCallback {
        void onPermissionSettingChanged();
    }
    
    public SettingsPermissionObserver(Handler handler, Context context, 
                                    PermissionChangeCallback callback) {
        super(handler);
        this.context = context;
        this.callback = callback;
    }
    
    public void startObserving() {
        // 监听运行时权限相关的Settings变化
        context.getContentResolver().registerContentObserver(
            Settings.Global.getUriFor("runtime_permissions_enabled"),
            false, this);
            
        // 监听应用权限相关的URI
        context.getContentResolver().registerContentObserver(
            Uri.parse("content://settings/global/app_ops_constants"),
            false, this);
    }
    
    public void stopObserving() {
        context.getContentResolver().unregisterContentObserver(this);
    }
    
    @Override
    public void onChange(boolean selfChange, Uri uri) {
        super.onChange(selfChange, uri);
        Log.d(TAG, "Settings changed: " + uri);
        
        if (callback != null) {
            callback.onPermissionSettingChanged();
        }
    }
}
```

## 3. 主界面Activity

```java
// MainActivity.java
package com.example.permissionobserver;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends Activity {
    private TextView logTextView;
    private EditText packageNameEdit;
    private Button startButton;
    private Button stopButton;
    private ScrollView scrollView;
    
    private SimpleDateFormat dateFormat = new SimpleDateFormat(
        "HH:mm:ss", Locale.getDefault());
    
    private BroadcastReceiver permissionChangeReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String packageName = intent.getStringExtra("package_name");
            String permission = intent.getStringExtra("permission");
            boolean granted = intent.getBooleanExtra("granted", false);
            long timestamp = intent.getLongExtra("timestamp", System.currentTimeMillis());
            
            String status = granted ? "[GRANTED]" : "[REVOKED]";
            String time = dateFormat.format(new Date(timestamp));
            String log = String.format("%s %s %s: %s\n", 
                time, status, packageName, permission);
            
            runOnUiThread(() -> {
                logTextView.append(log);
                // 自动滚动到底部
                scrollView.post(() -> scrollView.fullScroll(ScrollView.FOCUS_DOWN));
            });
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        initViews();
        setupListeners();
    }
    
    private void initViews() {
        logTextView = findViewById(R.id.log_text);
        packageNameEdit = findViewById(R.id.package_name_edit);
        startButton = findViewById(R.id.start_button);
        stopButton = findViewById(R.id.stop_button);
        scrollView = findViewById(R.id.scroll_view);
    }
    
    private void setupListeners() {
        startButton.setOnClickListener(v -> {
            Intent serviceIntent = new Intent(this, PermissionObserverService.class);
            String packageName = packageNameEdit.getText().toString().trim();
            if (!packageName.isEmpty()) {
                serviceIntent.putExtra("package_name", packageName);
            }
            startService(serviceIntent);
            logTextView.append("Service started\n");
        });
        
        stopButton.setOnClickListener(v -> {
            stopService(new Intent(this, PermissionObserverService.class));
            logTextView.append("Service stopped\n");
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter(
            "com.example.permissionobserver.PERMISSION_CHANGED");
        registerReceiver(permissionChangeReceiver, filter);
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(permissionChangeReceiver);
    }
}
```

## 4. 配置文件

### AndroidManifest.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.permissionobserver">
    
    <!-- 需要的权限 -->
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />
    <uses-permission android:name="android.permission.GET_TASKS" />
    
    <application
        android:allowBackup="true"
        android:label="Permission Observer"
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
            android:name=".PermissionObserverService"
            android:exported="false" />
            
    </application>
</manifest>
```

### 布局文件 activity_main.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Package Name (optional):"
        android:textSize="16sp" />

    <EditText
        android:id="@+id/package_name_edit"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:hint="com.example.app"
        android:layout_marginBottom="8dp" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal">

        <Button
            android:id="@+id/start_button"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Start Service"
            android:layout_marginEnd="8dp" />

        <Button
            android:id="@+id/stop_button"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Stop Service" />

    </LinearLayout>

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Permission Changes:"
        android:textSize="16sp"
        android:layout_marginTop="16dp"
        android:layout_marginBottom="8dp" />

    <ScrollView
        android:id="@+id/scroll_view"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:background="#f0f0f0">

        <TextView
            android:id="@+id/log_text"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:padding="8dp"
            android:textSize="14sp"
            android:typeface="monospace" />

    </ScrollView>

</LinearLayout>
```

## 5. 构建和安装脚本

### build.gradle (app级别)
```gradle
android {
    compileSdkVersion 33
    
    defaultConfig {
        applicationId "com.example.permissionobserver"
        minSdkVersion 23
        targetSdkVersion 33
        versionCode 1
        versionName "1.0"
    }
    
    buildTypes {
        release {
            minifyEnabled false
        }
    }
}
```

### 安装脚本 install.sh
```bash
#!/bin/bash

# 构建APK
./gradlew assembleDebug

# 安装到设备
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 启动应用
adb shell am start -n com.example.permissionobserver/.MainActivity

# 查看日志
echo "Monitoring logs..."
adb logcat -s PermissionObserver:*
```

## 使用说明

1. **通过ADB安装运行**：
```bash
# 安装APK
adb install -r PermissionObserver.apk

# 启动服务（直接启动服务，不打开UI）
adb shell am startservice com.example.permissionobserver/.PermissionObserverService

# 监测特定应用
adb shell am startservice -e package_name "com.target.app" com.example.permissionobserver/.PermissionObserverService

# 查看日志
adb logcat -s PermissionObserver:*
```

2. **特点**：
   - 使用系统提供的OnPermissionsChangedListener，无需轮询
   - 实时监听权限变化
   - 低功耗，事件驱动
   - 支持监测所有应用或特定应用
   - 通过日志和广播输出权限变化

这个实现避免了轮询，使用Android系统提供的Observer机制，能够高效地监测权限变化。