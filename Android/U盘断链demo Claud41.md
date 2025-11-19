我来帮您创建一个Android测试工具应用，用于U盘占用测试。这个应用将包含完整的项目结构和必要的文件。

## 1. MainActivity.java

```java
package com.example.usbstresstest;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {
    
    private static final int PERMISSION_REQUEST_CODE = 100;
    private EditText etProcessCount;
    private EditText etFileSize;
    private EditText etWriteInterval;
    private EditText etUsbPath;
    private Button btnStart;
    private Button btnStop;
    private TextView tvStatus;
    private TextView tvActiveProcesses;
    
    private List<Intent> runningServices = new ArrayList<>();
    private int activeProcessCount = 0;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        initViews();
        checkPermissions();
        setupListeners();
        updateStatus("准备就绪");
    }
    
    private void initViews() {
        etProcessCount = findViewById(R.id.et_process_count);
        etFileSize = findViewById(R.id.et_file_size);
        etWriteInterval = findViewById(R.id.et_write_interval);
        etUsbPath = findViewById(R.id.et_usb_path);
        btnStart = findViewById(R.id.btn_start);
        btnStop = findViewById(R.id.btn_stop);
        tvStatus = findViewById(R.id.tv_status);
        tvActiveProcesses = findViewById(R.id.tv_active_processes);
        
        // 设置默认值
        etProcessCount.setText("5");
        etFileSize.setText("10");
        etWriteInterval.setText("100");
        etUsbPath.setText("/storage/");
        
        btnStop.setEnabled(false);
    }
    
    private void setupListeners() {
        btnStart.setOnClickListener(v -> startStressTest());
        btnStop.setOnClickListener(v -> stopStressTest());
    }
    
    private void checkPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                Uri uri = Uri.fromParts("package", getPackageName(), null);
                intent.setData(uri);
                startActivity(intent);
            }
        } else {
            String[] permissions = {
                Manifest.permission.READ_EXTERNAL_STORAGE,
                Manifest.permission.WRITE_EXTERNAL_STORAGE
            };
            
            boolean allGranted = true;
            for (String permission : permissions) {
                if (ContextCompat.checkSelfPermission(this, permission) 
                    != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            
            if (!allGranted) {
                ActivityCompat.requestPermissions(this, permissions, PERMISSION_REQUEST_CODE);
            }
        }
    }
    
    private void startStressTest() {
        try {
            int processCount = Integer.parseInt(etProcessCount.getText().toString());
            int fileSize = Integer.parseInt(etFileSize.getText().toString());
            int writeInterval = Integer.parseInt(etWriteInterval.getText().toString());
            String usbPath = etUsbPath.getText().toString();
            
            if (processCount <= 0 || fileSize <= 0) {
                Toast.makeText(this, "参数必须大于0", Toast.LENGTH_SHORT).show();
                return;
            }
            
            // 验证USB路径
            File usbDir = new File(usbPath);
            if (!usbDir.exists() || !usbDir.canWrite()) {
                Toast.makeText(this, "USB路径无效或不可写", Toast.LENGTH_SHORT).show();
                return;
            }
            
            runningServices.clear();
            activeProcessCount = 0;
            
            for (int i = 0; i < processCount; i++) {
                Intent serviceIntent = new Intent(this, USBWriterService.class);
                serviceIntent.putExtra("PROCESS_ID", i);
                serviceIntent.putExtra("FILE_SIZE", fileSize);
                serviceIntent.putExtra("WRITE_INTERVAL", writeInterval);
                serviceIntent.putExtra("USB_PATH", usbPath);
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent);
                } else {
                    startService(serviceIntent);
                }
                
                runningServices.add(serviceIntent);
                activeProcessCount++;
            }
            
            btnStart.setEnabled(false);
            btnStop.setEnabled(true);
            updateStatus("正在运行压力测试...");
            updateProcessCount();
            
        } catch (NumberFormatException e) {
            Toast.makeText(this, "请输入有效的数字", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "启动失败: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }
    
    private void stopStressTest() {
        for (Intent serviceIntent : runningServices) {
            stopService(serviceIntent);
        }
        
        runningServices.clear();
        activeProcessCount = 0;
        
        btnStart.setEnabled(true);
        btnStop.setEnabled(false);
        updateStatus("测试已停止");
        updateProcessCount();
    }
    
    private void updateStatus(String status) {
        tvStatus.setText("状态: " + status);
    }
    
    private void updateProcessCount() {
        tvActiveProcesses.setText("活动进程数: " + activeProcessCount);
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_CODE) {
            boolean allGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            
            if (!allGranted) {
                Toast.makeText(this, "需要存储权限才能运行测试", Toast.LENGTH_LONG).show();
            }
        }
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopStressTest();
    }
}
```

## 2. USBWriterService.java

```java
package com.example.usbstresstest;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.Process;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.util.Random;
import java.util.concurrent.atomic.AtomicBoolean;

public class USBWriterService extends Service {
    
    private static final String TAG = "USBWriterService";
    private static final String CHANNEL_ID = "USB_WRITER_CHANNEL";
    private static final int NOTIFICATION_ID = 1001;
    
    private AtomicBoolean isRunning = new AtomicBoolean(false);
    private Thread workerThread;
    private int processId;
    private int fileSize;
    private int writeInterval;
    private String usbPath;
    
    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            processId = intent.getIntExtra("PROCESS_ID", 0);
            fileSize = intent.getIntExtra("FILE_SIZE", 10);
            writeInterval = intent.getIntExtra("WRITE_INTERVAL", 100);
            usbPath = intent.getStringExtra("USB_PATH");
            
            if (usbPath == null) {
                usbPath = "/storage/";
            }
            
            startForeground(NOTIFICATION_ID + processId, createNotification());
            startWorker();
        }
        
        return START_STICKY;
    }
    
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "USB写入服务",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("USB压力测试服务");
            
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }
    
    private Notification createNotification() {
        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("USB压力测试")
            .setContentText("进程 " + processId + " 正在运行")
            .setSmallIcon(android.R.drawable.ic_menu_save)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build();
    }
    
    private void startWorker() {
        if (isRunning.get()) {
            return;
        }
        
        isRunning.set(true);
        workerThread = new Thread(() -> {
            // 设置线程为独立进程组
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            
            String fileName = "stress_test_" + processId + "_" + System.currentTimeMillis() + ".dat";
            File testFile = new File(usbPath, fileName);
            
            Log.d(TAG, "Process " + processId + " starting, file: " + testFile.getAbsolutePath());
            
            Random random = new Random();
            byte[] buffer = new byte[1024 * 1024]; // 1MB缓冲区
            
            while (isRunning.get()) {
                try {
                    // 写入操作
                    writeToFile(testFile, buffer, random);
                    
                    // 读取操作
                    readFromFile(testFile, buffer);
                    
                    // 随机访问操作
                    randomAccessFile(testFile, random);
                    
                    // 间隔
                    if (writeInterval > 0) {
                        Thread.sleep(writeInterval);
                    }
                    
                } catch (InterruptedException e) {
                    Log.d(TAG, "Process " + processId + " interrupted");
                    break;
                } catch (IOException e) {
                    Log.e(TAG, "Process " + processId + " IO error: " + e.getMessage());
                    // USB可能已断开，继续尝试
                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException ie) {
                        break;
                    }
                }
            }
            
            // 清理文件
            try {
                if (testFile.exists()) {
                    testFile.delete();
                }
            } catch (Exception e) {
                Log.e(TAG, "Failed to delete test file: " + e.getMessage());
            }
            
            Log.d(TAG, "Process " + processId + " stopped");
        });
        
        workerThread.start();
    }
    
    private void writeToFile(File file, byte[] buffer, Random random) throws IOException {
        FileOutputStream fos = null;
        FileChannel channel = null;
        
        try {
            // 生成随机数据
            random.nextBytes(buffer);
            
            fos = new FileOutputStream(file, true);
            channel = fos.getChannel();
            
            // 写入数据多次以达到指定文件大小
            int totalSize = fileSize * 1024 * 1024; // MB转字节
            int written = 0;
            
            while (written < totalSize && isRunning.get()) {
                int toWrite = Math.min(buffer.length, totalSize - written);
                ByteBuffer byteBuffer = ByteBuffer.wrap(buffer, 0, toWrite);
                channel.write(byteBuffer);
                written += toWrite;
                
                // 强制刷新到磁盘
                channel.force(true);
            }
            
        } finally {
            if (channel != null) {
                try { channel.close(); } catch (Exception e) {}
            }
            if (fos != null) {
                try { fos.close(); } catch (Exception e) {}
            }
        }
    }
    
    private void readFromFile(File file, byte[] buffer) throws IOException {
        if (!file.exists()) {
            return;
        }
        
        FileInputStream fis = null;
        FileChannel channel = null;
        
        try {
            fis = new FileInputStream(file);
            channel = fis.getChannel();
            
            ByteBuffer byteBuffer = ByteBuffer.allocate(buffer.length);
            
            while (channel.read(byteBuffer) > 0 && isRunning.get()) {
                byteBuffer.flip();
                byteBuffer.clear();
            }
            
        } finally {
            if (channel != null) {
                try { channel.close(); } catch (Exception e) {}
            }
            if (fis != null) {
                try { fis.close(); } catch (Exception e) {}
            }
        }
    }
    
    private void randomAccessFile(File file, Random random) throws IOException {
        if (!file.exists() || file.length() == 0) {
            return;
        }
        
        RandomAccessFile raf = null;
        
        try {
            raf = new RandomAccessFile(file, "rw");
            long fileLength = raf.length();
            
            // 随机读写10次
            for (int i = 0; i < 10 && isRunning.get(); i++) {
                long position = Math.abs(random.nextLong()) % fileLength;
                raf.seek(position);
                
                // 随机读或写
                if (random.nextBoolean()) {
                    // 读操作
                    byte[] smallBuffer = new byte[1024];
                    raf.read(smallBuffer);
                } else {
                    // 写操作
                    byte[] data = new byte[1024];
                    random.nextBytes(data);
                    raf.write(data);
                }
            }
            
        } finally {
            if (raf != null) {
                try { raf.close(); } catch (Exception e) {}
            }
        }
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        isRunning.set(false);
        
        if (workerThread != null) {
            workerThread.interrupt();
            try {
                workerThread.join(2000);
            } catch (InterruptedException e) {
                Log.e(TAG, "Failed to stop worker thread");
            }
        }
    }
    
    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
```

## 3. activity_main.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:padding="16dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical">

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="USB压力测试工具"
            android:textSize="24sp"
            android:textStyle="bold"
            android:gravity="center"
            android:layout_marginBottom="24dp" />

        <TextView
            android:id="@+id/tv_status"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="状态: 准备就绪"
            android:textSize="16sp"
            android:textColor="@android:color/holo_blue_dark"
            android:layout_marginBottom="8dp" />

        <TextView
            android:id="@+id/tv_active_processes"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="活动进程数: 0"
            android:textSize="16sp"
            android:textColor="@android:color/holo_green_dark"
            android:layout_marginBottom="24dp" />

        <View
            android:layout_width="match_parent"
            android:layout_height="1dp"
            android:background="@android:color/darker_gray"
            android:layout_marginBottom="16dp" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="测试参数设置"
            android:textSize="18sp"
            android:textStyle="bold"
            android:layout_marginBottom="16dp" />

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginBottom="12dp">

            <TextView
                android:layout_width="120dp"
                android:layout_height="wrap_content"
                android:text="进程数量:"
                android:textSize="16sp"
                android:layout_gravity="center_vertical" />

            <EditText
                android:id="@+id/et_process_count"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:inputType="number"
                android:hint="输入进程数量"
                android:text="5" />
        </LinearLayout>

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginBottom="12dp">

            <TextView
                android:layout_width="120dp"
                android:layout_height="wrap_content"
                android:text="文件大小(MB):"
                android:textSize="16sp"
                android:layout_gravity="center_vertical" />

            <EditText
                android:id="@+id/et_file_size"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:inputType="number"
                android:hint="输入文件大小"
                android:text="10" />
        </LinearLayout>

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginBottom="12dp">

            <TextView
                android:layout_width="120dp"
                android:layout_height="wrap_content"
                android:text="写入间隔(ms):"
                android:textSize="16sp"
                android:layout_gravity="center_vertical" />

            <EditText
                android:id="@+id/et_write_interval"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:inputType="number"
                android:hint="输入写入间隔"
                android:text="100" />
        </LinearLayout>

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginBottom="24dp">

            <TextView
                android:layout_width="120dp"
                android:layout_height="wrap_content"
                android:text="USB路径:"
                android:textSize="16sp"
                android:layout_gravity="center_vertical" />

            <EditText
                android:id="@+id/et_usb_path"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:inputType="text"
                android:hint="输入USB挂载路径"
                android:text="/storage/" />
        </LinearLayout>

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:layout_marginTop="16dp">

            <Button
                android:id="@+id/btn_start"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="开始测试"
                android:textSize="16sp"
                android:layout_marginEnd="8dp" />

            <Button
                android:id="@+id/btn_stop"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:text="停止测试"
                android:textSize="16sp"
                android:layout_marginStart="8dp" />
        </LinearLayout>

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="使用说明："
            android:textSize="16sp"
            android:textStyle="bold"
            android:layout_marginTop="24dp"
            android:layout_marginBottom="8dp" />

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="1. 确保已插入U盘并正确挂载\n2. 输入正确的U盘挂载路径（通常在/storage/下）\n3. 设置测试参数\n4. 点击开始测试启动压力测试\n5. 测试过程中可以拔出U盘观察vold处理时间\n6. 点击停止测试结束所有进程"
            android:textSize="14sp"
            android:lineSpacingExtra="4dp" />

    </LinearLayout>
</ScrollView>
```

## 4. AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools"
    package="com.example.usbstresstest">

    <!-- 存储权限 -->
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
        android:maxSdkVersion="29"
        tools:ignore="ScopedStorage" />
    
    <!-- Android 11及以上需要的所有文件访问权限 -->
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE"
        tools:ignore="ScopedStorage" />
    
    <!-- 前台服务权限 -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    
    <!-- USB相关权限 -->
    <uses-permission android:name="android.permission.USB_PERMISSION" />
    
    <!-- 唤醒锁权限，保持服务运行 -->
    <uses-permission android:name="android.permission.WAKE_LOCK" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="USB压力测试"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.DarkActionBar"
        android:requestLegacyExternalStorage="true"
        android:preserveLegacyExternalStorage="true"
        tools:targetApi="30">
        
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
            android:name=".USBWriterService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="dataSync"
            android:process=":remote" />
        
    </application>

</manifest>
```

## 5. build.gradle (app级别)

```gradle
plugins {
    id 'com.android.application'
}

android {
    compileSdk 33
    
    defaultConfig {
        applicationId "com.example.usbstresstest"
        minSdk 30
        targetSdk 33
        versionCode 1
        versionName "1.0"
        
        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }
    
    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.9.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    
    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.1.5'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
}
```

## 使用说明

这个应用的主要特点：

1. **多进程支持**：每个Service运行在独立进程中（通过`android:process=":remote"`配置），可以创建任意数量的进程。

2. **持续读写操作**：每个进程会持续进行文件写入、读取和随机访问操作，确保对U盘的持续占用。

3. **参数可配置**：
   - 进程数量：控制并发进程数
   - 文件大小：每个进程创建的文件大小（MB）
   - 写入间隔：控制读写操作的频率（毫秒）
   - USB路径：指定U盘挂载路径

4. **前台服务**：使用前台服务确保进程不被系统轻易杀死。

5. **权限处理**：正确处理Android 11及以上版本的存储权限。

测试步骤：
1. 安装APK到Android设备
2. 插入U盘并确认挂载路径（通常在`/storage/`下有对应的UUID目录）
3. 在应用中设置参数
4. 点击"开始测试"
5. 拔出U盘，观察vold杀死进程所需的时间

这个工具可以有效地模拟多个进程占用U盘的场景，用于测试系统在U盘断链时的处理性能。