我来帮你创建一个Android工具，用于创建多个进程持续读写外接U盘文件。

```java
// MainActivity.java
package com.example.usbstresstest;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.storage.StorageManager;
import android.os.storage.StorageVolume;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.File;
import java.util.List;

public class MainActivity extends Activity {
    private EditText processCountInput;
    private Button startButton;
    private Button stopButton;
    private TextView logTextView;
    private ScrollView logScrollView;
    private int runningProcesses = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        processCountInput = findViewById(R.id.processCountInput);
        startButton = findViewById(R.id.startButton);
        stopButton = findViewById(R.id.stopButton);
        logTextView = findViewById(R.id.logTextView);
        logScrollView = findViewById(R.id.logScrollView);

        startButton.setOnClickListener(v -> startProcesses());
        stopButton.setOnClickListener(v -> stopProcesses());
        
        updateButtonStates();
    }

    private void startProcesses() {
        String countStr = processCountInput.getText().toString();
        if (countStr.isEmpty()) {
            Toast.makeText(this, "请输入进程数量", Toast.LENGTH_SHORT).show();
            return;
        }

        int count = Integer.parseInt(countStr);
        if (count <= 0 || count > 50) {
            Toast.makeText(this, "进程数量应在1-50之间", Toast.LENGTH_SHORT).show();
            return;
        }

        // 查找U盘路径
        String usbPath = findUsbPath();
        if (usbPath == null) {
            Toast.makeText(this, "未找到外接U盘", Toast.LENGTH_SHORT).show();
            return;
        }

        addLog("找到U盘路径: " + usbPath);
        addLog("启动 " + count + " 个进程...");

        // 启动多个进程
        for (int i = 0; i < count; i++) {
            Intent intent = new Intent(this, WorkerProcessActivity.class);
            intent.putExtra("process_id", i);
            intent.putExtra("usb_path", usbPath);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_MULTIPLE_TASK);
            startActivity(intent);
            runningProcesses++;
        }

        addLog("已启动 " + count + " 个进程");
        updateButtonStates();
    }

    private void stopProcesses() {
        // 发送广播停止所有工作进程
        Intent intent = new Intent("com.example.usbstresstest.STOP_WORKER");
        sendBroadcast(intent);
        
        runningProcesses = 0;
        addLog("已发送停止信号");
        updateButtonStates();
    }

    private String findUsbPath() {
        StorageManager storageManager = (StorageManager) getSystemService(STORAGE_SERVICE);
        List<StorageVolume> volumes = storageManager.getStorageVolumes();

        for (StorageVolume volume : volumes) {
            if (volume.isRemovable() && !volume.isPrimary()) {
                // Android 11+ 获取U盘路径
                File volumeDir = volume.getDirectory();
                if (volumeDir != null && volumeDir.exists()) {
                    return volumeDir.getAbsolutePath();
                }
            }
        }

        // 备用方法：扫描常见U盘挂载点
        String[] possiblePaths = {
            "/storage/usbotg",
            "/mnt/usb_storage",
            "/mnt/usbhost",
            "/mnt/media_rw"
        };

        for (String path : possiblePaths) {
            File dir = new File(path);
            if (dir.exists() && dir.isDirectory()) {
                File[] files = dir.listFiles();
                if (files != null && files.length > 0) {
                    return files[0].getAbsolutePath();
                }
            }
        }

        return null;
    }

    private void addLog(String message) {
        runOnUiThread(() -> {
            logTextView.append(message + "\n");
            logScrollView.post(() -> logScrollView.fullScroll(View.FOCUS_DOWN));
        });
    }

    private void updateButtonStates() {
        startButton.setEnabled(runningProcesses == 0);
        stopButton.setEnabled(runningProcesses > 0);
    }
}
```

```java
// WorkerProcessActivity.java
package com.example.usbstresstest;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.Process;
import android.widget.TextView;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Random;

public class WorkerProcessActivity extends Activity {
    private int processId;
    private String usbPath;
    private volatile boolean running = true;
    private TextView statusTextView;
    private TextView statsTextView;
    private long readCount = 0;
    private long writeCount = 0;
    private Thread workerThread;

    private BroadcastReceiver stopReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            stopWork();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_worker);

        statusTextView = findViewById(R.id.statusTextView);
        statsTextView = findViewById(R.id.statsTextView);

        processId = getIntent().getIntExtra("process_id", 0);
        usbPath = getIntent().getStringExtra("usb_path");

        setTitle("进程 " + processId);
        statusTextView.setText("进程ID: " + processId + "\nPID: " + Process.myPid());

        // 注册广播接收器
        IntentFilter filter = new IntentFilter("com.example.usbstresstest.STOP_WORKER");
        registerReceiver(stopReceiver, filter);

        // 启动工作线程
        startWork();
    }

    private void startWork() {
        workerThread = new Thread(() -> {
            File workDir = new File(usbPath, "stress_test");
            if (!workDir.exists()) {
                workDir.mkdirs();
            }

            File testFile = new File(workDir, "process_" + processId + ".dat");
            Random random = new Random();
            byte[] buffer = new byte[1024 * 1024]; // 1MB 缓冲区

            while (running) {
                try {
                    // 写入文件
                    random.nextBytes(buffer);
                    try (FileOutputStream fos = new FileOutputStream(testFile)) {
                        fos.write(buffer);
                        fos.flush();
                    }
                    writeCount++;
                    updateStats();

                    // 读取文件
                    try (FileInputStream fis = new FileInputStream(testFile)) {
                        int bytesRead = 0;
                        while (bytesRead < buffer.length) {
                            int read = fis.read(buffer, bytesRead, buffer.length - bytesRead);
                            if (read == -1) break;
                            bytesRead += read;
                        }
                    }
                    readCount++;
                    updateStats();

                    // 短暂延迟避免过度占用资源
                    Thread.sleep(100);

                } catch (IOException | InterruptedException e) {
                    updateStatus("错误: " + e.getMessage());
                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException ie) {
                        break;
                    }
                }
            }

            // 清理测试文件
            if (testFile.exists()) {
                testFile.delete();
            }
        });

        workerThread.start();
    }

    private void updateStats() {
        runOnUiThread(() -> {
            statsTextView.setText(String.format(
                "读取次数: %d\n写入次数: %d\n总操作: %d",
                readCount, writeCount, readCount + writeCount
            ));
        });
    }

    private void updateStatus(String message) {
        runOnUiThread(() -> {
            statusTextView.setText(statusTextView.getText() + "\n" + message);
        });
    }

    private void stopWork() {
        running = false;
        if (workerThread != null) {
            workerThread.interrupt();
        }
        finish();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        running = false;
        unregisterReceiver(stopReceiver);
    }
}
```

```xml
<!-- res/layout/activity_main.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="USB压力测试工具"
        android:textSize="24sp"
        android:textStyle="bold"
        android:layout_marginBottom="16dp"/>

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="16dp">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="进程数量: "
            android:textSize="16sp"
            android:layout_gravity="center_vertical"/>

        <EditText
            android:id="@+id/processCountInput"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:inputType="number"
            android:hint="输入1-50"
            android:text="5"/>

    </LinearLayout>

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="16dp">

        <Button
            android:id="@+id/startButton"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="启动"
            android:layout_marginEnd="8dp"/>

        <Button
            android:id="@+id/stopButton"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="停止"
            android:layout_marginStart="8dp"/>

    </LinearLayout>

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="运行日志:"
        android:textSize="16sp"
        android:textStyle="bold"
        android:layout_marginBottom="8dp"/>

    <ScrollView
        android:id="@+id/logScrollView"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:background="#F0F0F0"
        android:padding="8dp">

        <TextView
            android:id="@+id/logTextView"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="12sp"
            android:fontFamily="monospace"/>

    </ScrollView>

</LinearLayout>
```

```xml
<!-- res/layout/activity_worker.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <TextView
        android:id="@+id/statusTextView"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textSize="14sp"
        android:layout_marginBottom="16dp"/>

    <TextView
        android:id="@+id/statsTextView"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textSize="18sp"
        android:textStyle="bold"/>

</LinearLayout>
```

```xml
<!-- AndroidManifest.xml -->
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.usbstresstest">

    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"/>

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="USB压力测试"
        android:requestLegacyExternalStorage="true"
        android:theme="@android:style/Theme.Material.Light">
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <activity
            android:name=".WorkerProcessActivity"
            android:process=":worker"
            android:exported="false"/>

    </application>

</manifest>
```

```gradle
// build.gradle (Module: app)
android {
    compileSdkVersion 33
    
    defaultConfig {
        applicationId "com.example.usbstresstest"
        minSdkVersion 30  // Android 11
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

dependencies {
    // 无需额外依赖
}
```

## 使用说明：

1. **权限申请**：首次运行需要在系统设置中手动授予"所有文件访问权限"（MANAGE_EXTERNAL_STORAGE）

2. **功能特点**：
   - 支持创建1-50个独立进程
   - 每个进程持续读写1MB大小的文件
   - 实时显示每个进程的读写次数
   - 自动检测U盘路径

3. **注意事项**：
   - 确保U盘已正确挂载
   - 测试文件会创建在U盘的`stress_test`目录下
   - 停止测试时会自动清理测试文件

这个工具可以有效测试Android设备在多进程场景下对外接U盘的读写性能和稳定性。