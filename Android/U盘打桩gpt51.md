下面给出一个完整的 Android 11+ Java Demo「USB 占用打桩工具」项目骨架，满足以下诉求：

* 可配置任意数量的读写进程（通过 `ProcessBuilder` 派生 shell 子进程，持续 `dd`/`cat` 操作目标 U 盘目录）。
* 前台服务保持长时间运行，保障在断链时 vold 需要逐一杀进程。
* 主界面可配置：目标目录、进程数、块大小、写入间隔、是否读回、同步频率等。
* 自动申请 `MANAGE_EXTERNAL_STORAGE` 等必要权限。
* 运行于 Android 11 (API 30) 及以上，使用 Java 开发，基于 ViewBinding。

---

## 1. 工程结构概览

```
app/
├── build.gradle
├── src/main/
│   ├── AndroidManifest.xml
│   ├── java/com/example/usbhammer/
│   │   ├── MainActivity.java
│   │   ├── HammerService.java
│   │   ├── StorageHammerManager.java
│   │   ├── StorageWorker.java
│   │   ├── HammerConfig.java
│   │   ├── PermissionHelper.java
│   │   └── ShellUtils.java
│   └── res/
│       ├── layout/activity_main.xml
│       ├── values/strings.xml
│       ├── values/colors.xml
│       └── values/themes.xml
```

---

## 2. 代码清单

### 2.1 `app/build.gradle`

```gradle
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.example.usbhammer'
    compileSdk 34

    defaultConfig {
        applicationId "com.example.usbhammer"
        minSdk 30
        targetSdk 34
        versionCode 1
        versionName "1.0"

        vectorDrawables {
            useSupportLibrary true
        }
    }

    buildFeatures {
        viewBinding true
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_11
        targetCompatibility JavaVersion.VERSION_11
    }

    packagingOptions {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.13.1'
    implementation 'androidx.appcompat:appcompat:1.7.0'
    implementation 'com.google.android.material:material:1.12.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.2.0'
}
```

### 2.2 `AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools"
    package="com.example.usbhammer">

    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"
        tools:ignore="ScopedStorage" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
        android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
        android:maxSdkVersion="29" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />

    <application
        android:allowBackup="false"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.UsbHammer"
        android:requestLegacyExternalStorage="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:screenOrientation="portrait">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".HammerService"
            android:exported="false"
            android:foregroundServiceType="dataSync"
            android:stopWithTask="false" />
    </application>
</manifest>
```

### 2.3 `res/layout/activity_main.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:padding="16dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:gravity="center_horizontal"
        android:spacing="12dp">

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="U盘根目录（例如 /storage/XXXX-XXXX/test）">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editBasePath"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:text="/storage/XXXX-XXXX/hammer" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="进程数量">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editWorkerCount"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="number"
                android:text="4" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="单次写入块大小 (KB)">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editBlockSize"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="number"
                android:text="1024" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="写入间隔 (ms)">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editSleepMs"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="number"
                android:text="200" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.textfield.TextInputLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="同步频率（每多少次写入触发 sync，0 表示不主动）">

            <com.google.android.material.textfield.TextInputEditText
                android:id="@+id/editSyncEvery"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:inputType="number"
                android:text="10" />
        </com.google.android.material.textfield.TextInputLayout>

        <com.google.android.material.checkbox.MaterialCheckBox
            android:id="@+id/checkReadback"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="开启写后读验证（cat 读回文件）"
            android:checked="true" />

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:gravity="center"
            android:weightSum="2"
            android:layout_marginTop="16dp">

            <com.google.android.material.button.MaterialButton
                android:id="@+id/buttonStart"
                style="@style/Widget.MaterialComponents.Button"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="启动占用" />

            <com.google.android.material.button.MaterialButton
                android:id="@+id/buttonStop"
                style="@style/Widget.MaterialComponents.Button"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:layout_marginStart="12dp"
                android:text="停止" />
        </LinearLayout>

        <TextView
            android:id="@+id/textStatus"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="当前状态：空闲"
            android:layout_marginTop="24dp"
            android:textAppearance="@style/TextAppearance.MaterialComponents.Body1" />
    </LinearLayout>
</ScrollView>
```

### 2.4 `res/values/strings.xml`

```xml
<resources>
    <string name="app_name">UsbHammer</string>
</resources>
```

### 2.5 `res/values/colors.xml`

```xml
<resources>
    <color name="purple_200">#BB86FC</color>
    <color name="purple_500">#6200EE</color>
    <color name="purple_700">#3700B3</color>
    <color name="teal_200">#03DAC5</color>
    <color name="teal_700">#018786</color>
    <color name="black">#000000</color>
    <color name="white">#FFFFFF</color>
</resources>
```

### 2.6 `res/values/themes.xml`

```xml
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="Theme.UsbHammer" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <item name="colorPrimary">@color/purple_500</item>
        <item name="colorPrimaryVariant">@color/purple_700</item>
        <item name="colorOnPrimary">@color/white</item>
        <item name="colorSecondary">@color/teal_200</item>
        <item name="colorSecondaryVariant">@color/teal_700</item>
        <item name="colorOnSecondary">@color/black</item>
        <item name="android:statusBarColor" tools:targetApi="l">@color/purple_700</item>
    </style>
</resources>
```

### 2.7 `HammerConfig.java`

```java
package com.example.usbhammer;

import android.content.Intent;
import android.os.Parcel;
import android.os.Parcelable;

public class HammerConfig implements Parcelable {
    public static final String EXTRA_KEY = "extra_config";

    public final String baseDirPath;
    public final int workerCount;
    public final int blockSizeKB;
    public final int sleepMs;
    public final int syncEvery;
    public final boolean readAfterWrite;

    public HammerConfig(String baseDirPath,
                        int workerCount,
                        int blockSizeKB,
                        int sleepMs,
                        int syncEvery,
                        boolean readAfterWrite) {
        this.baseDirPath = baseDirPath;
        this.workerCount = workerCount;
        this.blockSizeKB = blockSizeKB;
        this.sleepMs = sleepMs;
        this.syncEvery = syncEvery;
        this.readAfterWrite = readAfterWrite;
    }

    protected HammerConfig(Parcel in) {
        baseDirPath = in.readString();
        workerCount = in.readInt();
        blockSizeKB = in.readInt();
        sleepMs = in.readInt();
        syncEvery = in.readInt();
        readAfterWrite = in.readByte() != 0;
    }

    public static final Creator<HammerConfig> CREATOR = new Creator<>() {
        @Override
        public HammerConfig createFromParcel(Parcel in) {
            return new HammerConfig(in);
        }

        @Override
        public HammerConfig[] newArray(int size) {
            return new HammerConfig[size];
        }
    };

    public static HammerConfig fromIntent(Intent intent) {
        return intent.getParcelableExtra(EXTRA_KEY);
    }

    public Intent attachTo(Intent intent) {
        intent.putExtra(EXTRA_KEY, this);
        return intent;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(baseDirPath);
        dest.writeInt(workerCount);
        dest.writeInt(blockSizeKB);
        dest.writeInt(sleepMs);
        dest.writeInt(syncEvery);
        dest.writeByte((byte) (readAfterWrite ? 1 : 0));
    }

    @Override
    public int describeContents() {
        return 0;
    }
}
```

### 2.8 `ShellUtils.java`

```java
package com.example.usbhammer;

public final class ShellUtils {
    private ShellUtils() {}

    /** 将任意路径安全包裹成单引号 shell 字符串。 */
    public static String escape(String input) {
        if (input == null) {
            return "''";
        }
        return "'" + input.replace("'", "'\"'\"'") + "'";
    }
}
```

### 2.9 `StorageWorker.java`

```java
package com.example.usbhammer;

import android.util.Log;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class StorageWorker {
    private static final String TAG = "StorageWorker";

    private final int index;
    private final HammerConfig config;
    private final ExecutorService drainExecutor = Executors.newSingleThreadExecutor();
    private Process process;

    public StorageWorker(int index, HammerConfig config) {
        this.index = index;
        this.config = config;
    }

    public synchronized void start() throws IOException {
        if (process != null) {
            return;
        }
        String script = buildScript();
        ProcessBuilder pb = new ProcessBuilder("/system/bin/sh", "-c", script);
        pb.redirectErrorStream(true);
        process = pb.start();
        drainExecutor.submit(() -> drainStream(process.getInputStream()));
        Log.i(TAG, "Worker " + index + " started.");
    }

    public synchronized void stop() {
        if (process != null) {
            process.destroy();
            try {
                process.waitFor();
            } catch (InterruptedException e) {
                process.destroyForcibly();
                Thread.currentThread().interrupt();
            }
            process = null;
        }
        drainExecutor.shutdownNow();
        Log.i(TAG, "Worker " + index + " stopped.");
    }

    private void drainStream(InputStream stream) {
        byte[] buffer = new byte[1024];
        try {
            while (stream.read(buffer) != -1) {
                // 丢弃输出，防止阻塞
            }
        } catch (IOException ignored) {
        }
    }

    private String buildScript() {
        File outFile = new File(config.baseDirPath,
                "hammer_worker_" + index + ".bin");
        long blockBytes = Math.max(1, config.blockSizeKB) * 1024L;
        String target = ShellUtils.escape(outFile.getAbsolutePath());
        String sleepSeconds = String.format(java.util.Locale.US, "%.3f",
                Math.max(0, config.sleepMs) / 1000.0);

        StringBuilder sb = new StringBuilder();
        sb.append("TARGET=").append(target).append("\n")
          .append("mkdir -p \"$(dirname \"$TARGET\")\"\n")
          .append("i=0\n")
          .append("while true; do\n")
          .append("  dd if=/dev/zero of=\"$TARGET\" bs=").append(blockBytes)
          .append(" count=1 conv=fsync oflag=sync seek=$i >/dev/null 2>&1\n");
        if (config.readAfterWrite) {
            sb.append("  cat \"$TARGET\" >/dev/null 2>&1\n");
        }
        if (config.syncEvery > 0) {
            sb.append("  if [ $((i % ").append(config.syncEvery).append(")) -eq 0 ]; then sync; fi\n");
        }
        if (config.sleepMs > 0) {
            sb.append("  sleep ").append(sleepSeconds).append("\n");
        }
        sb.append("  i=$((i+1))\n")
          .append("done\n");
        return sb.toString();
    }
}
```

### 2.10 `StorageHammerManager.java`

```java
package com.example.usbhammer;

import android.util.Log;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class StorageHammerManager {
    private static final String TAG = "StorageHammerManager";
    private final List<StorageWorker> workers = new ArrayList<>();

    public synchronized void start(HammerConfig config) {
        stop(); // 先清理旧任务
        int count = Math.max(1, config.workerCount);
        for (int i = 0; i < count; i++) {
            StorageWorker worker = new StorageWorker(i, config);
            try {
                worker.start();
                workers.add(worker);
            } catch (IOException e) {
                Log.e(TAG, "Failed to start worker " + i, e);
            }
        }
        Log.i(TAG, "Started " + workers.size() + " workers.");
    }

    public synchronized void stop() {
        for (StorageWorker worker : workers) {
            worker.stop();
        }
        workers.clear();
        Log.i(TAG, "All workers stopped.");
    }

    public synchronized int getActiveWorkerCount() {
        return workers.size();
    }
}
```

### 2.11 `HammerService.java`

```java
package com.example.usbhammer;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

public class HammerService extends Service {

    public static final String ACTION_START = "com.example.usbhammer.action.START";
    public static final String ACTION_STOP = "com.example.usbhammer.action.STOP";
    private static final String CHANNEL_ID = "usb_hammer_channel";
    private static final int NOTIFICATION_ID = 1001;

    private final StorageHammerManager hammerManager = new StorageHammerManager();
    private HammerConfig currentConfig;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            stopSelf();
            return START_NOT_STICKY;
        }
        String action = intent.getAction();
        if (ACTION_STOP.equals(action)) {
            hammerManager.stop();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        } else if (ACTION_START.equals(action)) {
            HammerConfig config = HammerConfig.fromIntent(intent);
            if (config != null) {
                currentConfig = config;
                hammerManager.start(config);
                startForeground(NOTIFICATION_ID, buildNotification());
            }
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        hammerManager.stop();
        super.onDestroy();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private Notification buildNotification() {
        String content = currentConfig == null
                ? "等待配置"
                : "进程数：" + currentConfig.workerCount +
                  " | 目录：" + currentConfig.baseDirPath;
        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("U盘占用运行中")
                .setContentText(content)
                .setSmallIcon(android.R.drawable.stat_sys_download)
                .setOngoing(true)
                .addAction(new NotificationCompat.Action.Builder(
                        android.R.drawable.ic_delete,
                        "停止",
                        PendingIntentFactory.stopIntent(this))
                        .build())
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "USB Hammer",
                    NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("外接存储占用前台服务");
            NotificationManager nm = getSystemService(NotificationManager.class);
            nm.createNotificationChannel(channel);
        }
    }
}
```

> 依赖的 `PendingIntentFactory` 我们还未定义，下面补充。

### 2.12 `PendingIntentFactory.java`

```java
package com.example.usbhammer;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

public final class PendingIntentFactory {
    private PendingIntentFactory() {}

    private static int flags() {
        int flag = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flag |= PendingIntent.FLAG_IMMUTABLE;
        }
        return flag;
    }

    public static PendingIntent stopIntent(Context context) {
        Intent stop = new Intent(context, HammerService.class);
        stop.setAction(HammerService.ACTION_STOP);
        return PendingIntent.getService(context, 0, stop, flags());
    }
}
```

### 2.13 `PermissionHelper.java`

```java
package com.example.usbhammer;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import androidx.activity.result.ActivityResultLauncher;
import androidx.core.content.ContextCompat;

public final class PermissionHelper {
    private PermissionHelper() {}

    public static boolean hasAllFilesAccess(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            return Settings.isExternalStorageManager();
        } else {
            int read = ContextCompat.checkSelfPermission(context, Manifest.permission.READ_EXTERNAL_STORAGE);
            int write = ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE);
            return read == android.content.pm.PackageManager.PERMISSION_GRANTED
                    && write == android.content.pm.PackageManager.PERMISSION_GRANTED;
        }
    }

    public static void requestAllFilesAccess(Activity activity,
                                             ActivityResultLauncher<Intent> launcher) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
            intent.setData(Uri.parse("package:" + activity.getPackageName()));
            launcher.launch(intent);
        } else {
            activity.requestPermissions(
                    new String[] {
                            Manifest.permission.READ_EXTERNAL_STORAGE,
                            Manifest.permission.WRITE_EXTERNAL_STORAGE
                    }, 100);
        }
    }
}
```

### 2.14 `MainActivity.java`

```java
package com.example.usbhammer;

import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import com.example.usbhammer.databinding.ActivityMainBinding;

public class MainActivity extends AppCompatActivity {

    private ActivityMainBinding binding;
    private ActivityResultLauncher<Intent> manageFilesLauncher;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        manageFilesLauncher = registerForActivityResult(
                new ActivityResultContracts.StartActivityForResult(),
                result -> updateStatus());

        binding.buttonStart.setOnClickListener(v -> {
            if (!PermissionHelper.hasAllFilesAccess(this)) {
                PermissionHelper.requestAllFilesAccess(this, manageFilesLauncher);
                return;
            }
            HammerConfig config = collectConfig();
            if (config == null) return;
            Intent intent = new Intent(this, HammerService.class);
            intent.setAction(HammerService.ACTION_START);
            config.attachTo(intent);
            ContextCompat.startForegroundService(this, intent);
            binding.textStatus.setText("当前状态：运行中（进程 " + config.workerCount + "）");
        });

        binding.buttonStop.setOnClickListener(v -> {
            Intent stop = new Intent(this, HammerService.class);
            stop.setAction(HammerService.ACTION_STOP);
            startService(stop);
            binding.textStatus.setText("当前状态：已停止");
        });

        updateStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    private HammerConfig collectConfig() {
        String basePath = binding.editBasePath.getText() == null
                ? ""
                : binding.editBasePath.getText().toString().trim();

        if (TextUtils.isEmpty(basePath)) {
            Toast.makeText(this, "请输入 U 盘目录路径", Toast.LENGTH_SHORT).show();
            return null;
        }

        try {
            int workerCount = Integer.parseInt(
                    binding.editWorkerCount.getText().toString().trim());
            int blockSize = Integer.parseInt(
                    binding.editBlockSize.getText().toString().trim());
            int sleepMs = Integer.parseInt(
                    binding.editSleepMs.getText().toString().trim());
            int syncEvery = Integer.parseInt(
                    binding.editSyncEvery.getText().toString().trim());

            boolean readback = binding.checkReadback.isChecked();

            return new HammerConfig(basePath, workerCount, blockSize, sleepMs, syncEvery, readback);
        } catch (NumberFormatException e) {
            Toast.makeText(this, "请输入合法的数字参数", Toast.LENGTH_SHORT).show();
            return null;
        }
    }

    private void updateStatus() {
        boolean granted = PermissionHelper.hasAllFilesAccess(this);
        binding.textStatus.setText(granted ? "当前状态：权限已授予" : "当前状态：缺少 MANAGE_EXTERNAL_STORAGE 权限");
    }
}
```

---

## 3. 使用步骤

1. **编译安装**：`./gradlew assembleDebug`，将 `app-debug.apk` 安装到 Android 11+ 设备。
2. **授予权限**：首次启动点击“启动占用”会自动跳转「所有文件访问」页面授权。
3. **连接 U 盘**：在界面里填入 U 盘真实挂载路径（如 `/storage/1234-ABCD/test`），设定需要的进程数、块大小等。
4. **点击启动**：应用会进入前台服务状态，派生 N 个 shell 子进程持续 `dd` 写入并可选 `cat` 读回，占用 U 盘 IO。
5. **断链测试**：在 U 盘被拔除后，可观察 vold 杀进程耗时，借助日志或外部工具验证效果。
6. **点击停止**：或从通知栏“停止”动作终止全部子进程，释放资源。

> 注意：大量 `dd`/`sync` 操作会显著磨损闪存，请在测试设备及可丢弃介质上使用，勿对生产数据盘运行。

---

## 4. 进一步扩展建议

- 记录每个子进程 PID 及运行统计，显示在 UI。
- 允许配置写入模式（随机/顺序）、块对齐、文件大小上限等。
- 增加日志导出功能，便于测试报告。
- 使用 `WorkManager` 或自定义守护机制在异常退出后自动重启任务。

如需继续扩展或改写成 Kotlin/Compose 版本，可在此基础上迭代。