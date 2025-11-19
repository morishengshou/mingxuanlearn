下面给出一个可直接构建成 APK 的 Android Demo 工具（Java，Android 11+），带简单界面，可设置与查看运行参数，并能在界面上启动/停止压测。它通过 Runtime.exec 启动子进程，在外接 U 盘路径上进行持续读写（与之前命令行版本功能一致）。包含：

- Activity 界面（可设置进程数、文件数、块大小、单文件最大大小、持续时长、fsync、追加/环绕、读后校验、文件名前缀、退出清理、U 盘路径）。
- 后台 Service 承载运行与日志收集（前台服务，避免后台被杀）。
- 使用 Storage Access Framework 选择 U 盘目录（建议；也允许直接手输路径）。
- AndroidManifest.xml 所需权限与前台服务声明。
- 保留命令行核心逻辑 UsbIoWorker/Main（小幅改造以便复用）。

目录结构建议
- app/src/main/java/com/example/usbstresstool/
  - MainActivity.java
  - StressService.java
  - UsbIoWorker.java
  - CliMain.java     （原 Main 重命名为 CliMain 以免与 Activity 冲突）
  - ProcUtils.java
- app/src/main/res/layout/activity_main.xml
- app/src/main/res/values/strings.xml
- app/src/main/res/xml/file_paths.xml（如需 FileProvider，可选）
- app/src/main/AndroidManifest.xml

1) UsbIoWorker.java
保持与上一版一致，无需改动（拷贝即可）。

2) CliMain.java（原命令行 Main.java，类名改为 CliMain）
仅将 class 名改为 CliMain，其他保持一致，方便复用 app_process 启动子进程时的入口。

```java
package com.example.usbstresstool;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class CliMain {

    static class Args {
        String mountPath = "";
        int files = 1;
        int procs = 1;
        int block = 4096;
        long maxSize = 16L * 1024 * 1024;
        long durSec = 0L;
        boolean sync = true;
        boolean append = true;
        boolean verify = true;
        String prefix = "stress_";
        boolean clean = true;
    }

    public static void main(String[] argv) {
        Args args;
        try {
            args = parseArgs(argv);
        } catch (IllegalArgumentException e) {
            System.err.println("Arg error: " + e.getMessage());
            System.out.println(usage());
            return;
        }

        if (args.procs <= 1) {
            runSingle(args);
            return;
        }

        List<Process> children = new ArrayList<>();
        try {
            List<String> selfCmd = buildSelfCommand(argv, args);
            for (int i = 0; i < args.procs; i++) {
                ProcessBuilder pb = new ProcessBuilder(selfCmd);
                pb.redirectErrorStream(true);
                Process p = pb.start();
                children.add(p);

                final int idx = i;
                Thread t = new Thread(() -> {
                    try (java.io.BufferedReader br = new java.io.BufferedReader(
                            new java.io.InputStreamReader(p.getInputStream()))) {
                        String line;
                        while ((line = br.readLine()) != null) {
                            System.out.println("[child-" + idx + "] " + line);
                        }
                    } catch (Exception ignored) {}
                });
                t.setDaemon(true);
                t.start();
            }

            long start = System.currentTimeMillis();
            long durMs = args.durSec > 0 ? args.durSec * 1000L : Long.MAX_VALUE;
            while (System.currentTimeMillis() - start < durMs) {
                Thread.sleep(1000L);
            }
        } catch (Throwable t) {
            System.err.println("Launcher error: " + t);
            t.printStackTrace();
        } finally {
            for (Process c : children) {
                try { c.destroy(); } catch (Throwable ignored) {}
            }
            for (Process c : children) {
                try { c.waitFor(3, TimeUnit.SECONDS); } catch (Throwable ignored) {}
                if (c.isAlive()) {
                    try { c.destroyForcibly(); } catch (Throwable ignored) {}
                }
            }
        }
    }

    static void runSingle(Args args) {
        File root = new File(args.mountPath);
        if (!root.exists() || !root.isDirectory()) {
            System.err.println("Mount path not found: " + args.mountPath);
            return;
        }
        System.out.println("Starting worker: mount=" + args.mountPath +
                " files=" + args.files +
                " block=" + args.block +
                " max=" + args.maxSize +
                " append=" + args.append +
                " sync=" + args.sync +
                " verify=" + args.verify);

        UsbIoWorker worker = new UsbIoWorker(
                args.mountPath,
                args.files,
                args.block,
                args.maxSize,
                args.sync,
                args.append,
                args.verify,
                args.prefix
        );

        Thread t = new Thread(worker);
        t.setDaemon(false);
        t.start();

        long durMs = args.durSec > 0 ? args.durSec * 1000L : Long.MAX_VALUE;
        try {
            if (durMs == Long.MAX_VALUE) {
                t.join();
            } else {
                t.join(durMs);
                worker.requestStop();
                t.join(5000L);
            }
        } catch (InterruptedException e) {
            worker.requestStop();
        } finally {
            if (args.clean) {
                File[] toDelete = root.listFiles(f -> f.isFile() && f.getName().startsWith(args.prefix));
                if (toDelete != null) {
                    for (File f : toDelete) {
                        try { f.delete(); } catch (Throwable ignored) {}
                    }
                }
            }
        }
    }

    static List<String> buildSelfCommand(String[] argv, Args args) {
        List<String> newArgs = new ArrayList<>();
        for (String s : argv) newArgs.add(s);

        int pIndex = -1;
        for (int i = 0; i < newArgs.size(); i++) {
            if ("--procs".equals(newArgs.get(i))) { pIndex = i; break; }
        }
        if (pIndex >= 0 && pIndex + 1 < newArgs.size()) {
            newArgs.set(pIndex + 1, "1");
        } else {
            newArgs.add("--procs");
            newArgs.add("1");
        }

        String className = "com.example.usbstresstool.CliMain";
        List<String> cmd = new ArrayList<>();
        cmd.add("/system/bin/app_process");
        cmd.add("/system/bin");
        cmd.add(className);
        cmd.addAll(newArgs);
        return cmd;
    }

    static Args parseArgs(String[] argv) {
        Args a = new Args();
        for (int i = 0; i < argv.length; i++) {
            String k = argv[i];
            switch (k) {
                case "--mount-path":
                    a.mountPath = requireValue(argv, ++i, k);
                    break;
                case "--files":
                    a.files = Integer.parseInt(requireValue(argv, ++i, k));
                    break;
                case "--procs":
                    a.procs = Integer.parseInt(requireValue(argv, ++i, k));
                    break;
                case "--block":
                    a.block = Integer.parseInt(requireValue(argv, ++i, k));
                    break;
                case "--max-size":
                    a.maxSize = Long.parseLong(requireValue(argv, ++i, k));
                    break;
                case "--dur":
                    a.durSec = Long.parseLong(requireValue(argv, ++i, k));
                    break;
                case "--sync":
                    a.sync = parseBool(requireValue(argv, ++i, k), true);
                    break;
                case "--append":
                    a.append = parseBool(requireValue(argv, ++i, k), true);
                    break;
                case "--verify":
                    a.verify = parseBool(requireValue(argv, ++i, k), true);
                    break;
                case "--prefix":
                    a.prefix = requireValue(argv, ++i, k);
                    break;
                case "--clean":
                    a.clean = parseBool(requireValue(argv, ++i, k), true);
                    break;
                case "--help":
                case "-h":
                    System.out.println(usage());
                    System.exit(0);
                default:
                    throw new IllegalArgumentException("unknown arg: " + k);
            }
        }
        if (a.mountPath == null || a.mountPath.trim().isEmpty()) {
            throw new IllegalArgumentException("--mount-path is required");
        }
        if (a.block <= 0) throw new IllegalArgumentException("--block must be > 0");
        if (a.files <= 0) throw new IllegalArgumentException("--files must be > 0");
        if (a.procs <= 0) throw new IllegalArgumentException("--procs must be > 0");
        return a;
    }

    static boolean parseBool(String v, boolean defVal) {
        if (v == null) return defVal;
        if ("true".equalsIgnoreCase(v)) return true;
        if ("false".equalsIgnoreCase(v)) return false;
        return defVal;
    }

    static String requireValue(String[] argv, int idx, String key) {
        if (idx >= argv.length) throw new IllegalArgumentException("missing value for " + key);
        return argv[idx];
    }

    static String usage() {
        return "UsbStressTool (Android, Java)\n" +
                "  --mount-path <dir>   U disk mount path, e.g. /storage/XXXX-XXXX\n" +
                "  --procs <n>          number of processes (default 1)\n" +
                "  --files <n>          files per process (default 1)\n" +
                "  --block <bytes>      write block size (default 4096)\n" +
                "  --max-size <bytes>   per-file max size (default 16777216)\n" +
                "  --dur <sec>          duration seconds (0=unlimited)\n" +
                "  --sync <true|false>  fsync after each write (default true)\n" +
                "  --append <true|false>append write then wrap (default true)\n" +
                "  --verify <true|false>read-after-write verify (default true)\n" +
                "  --prefix <name>      file name prefix (default stress_)\n" +
                "  --clean <true|false> delete test files on exit (default true)\n";
    }
}
```

3) ProcUtils.java
封装把当前 APK 的 dex 路径作为 CLASSPATH，通过 app_process 拉起 CliMain 的命令构造。注意：app_process 在非 root 设备上可执行，但权限与访问路径受限；我们尽量复用 shell 类似的方式。

```java
package com.example.usbstresstool;

import android.content.Context;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

public class ProcUtils {

    public interface LineCallback {
        void onLine(String line);
    }

    public static Process startCliProcess(Context ctx, String[] args, LineCallback cb) throws Exception {
        // 选用 base.apk 路径作为 CLASSPATH
        String apkPath = ctx.getPackageCodePath();
        String entry = "com.example.usbstresstool.CliMain";

        List<String> cmd = new ArrayList<>();
        cmd.add("sh");
        cmd.add("-c");

        // 拼接参数为单行命令，便于设置 CLASSPATH 环境变量
        StringBuilder sb = new StringBuilder();
        sb.append("CLASSPATH=").append(escape(apkPath))
          .append(" /system/bin/app_process /system/bin ").append(entry);
        for (String a : args) {
            sb.append(" ").append(escape(a));
        }

        cmd.add(sb.toString());

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        Process p = pb.start();

        Thread t = new Thread(() -> {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line;
                while ((line = br.readLine()) != null) {
                    if (cb != null) cb.onLine(line);
                }
            } catch (Exception ignored) {}
        });
        t.setDaemon(true);
        t.start();

        return p;
    }

    private static String escape(String s) {
        if (s == null) return "";
        // 简单转义空格与通配
        if (s.indexOf(' ') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\'') >= 0) {
            return "'" + s.replace("'", "'\\''") + "'";
        }
        return s;
    }
}
```

4) StressService.java
前台服务：启动/停止进程群，采集日志，发送通知。

```java
package com.example.usbstresstool;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;

import androidx.core.app.NotificationCompat;

import java.util.ArrayList;
import java.util.List;

public class StressService extends Service {

    public static final String CHANNEL_ID = "usb_stress_channel";
    private final IBinder binder = new LocalBinder();

    private final List<Process> children = new ArrayList<>();
    private boolean running = false;
    private final StringBuilder logBuf = new StringBuilder();
    private StressParams currentParams;

    public class LocalBinder extends Binder {
        public StressService getService() { return StressService.this; }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        startForeground(1, buildNotif("Idle"));
    }

    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    public boolean isRunning() { return running; }
    public String getLogs() { return logBuf.toString(); }
    public StressParams getCurrentParams() { return currentParams; }

    public void startStress(StressParams p, ProcUtils.LineCallback uiCb) {
        if (running) return;
        running = true;
        currentParams = p;
        logBuf.setLength(0);
        appendLog("Starting stress with params: " + p);

        // 组装 CLI 参数
        List<String> argv = new ArrayList<>();
        argv.add("--mount-path"); argv.add(p.mountPath);
        argv.add("--procs"); argv.add(String.valueOf(p.procs));
        argv.add("--files"); argv.add(String.valueOf(p.files));
        argv.add("--block"); argv.add(String.valueOf(p.block));
        argv.add("--max-size"); argv.add(String.valueOf(p.maxSize));
        argv.add("--dur"); argv.add(String.valueOf(p.durSec));
        argv.add("--sync"); argv.add(String.valueOf(p.sync));
        argv.add("--append"); argv.add(String.valueOf(p.append));
        argv.add("--verify"); argv.add(String.valueOf(p.verify));
        argv.add("--prefix"); argv.add(p.prefix);
        argv.add("--clean"); argv.add(String.valueOf(p.clean));

        String[] arr = argv.toArray(new String[0]);

        try {
            Process pMain = ProcUtils.startCliProcess(this, arr, line -> {
                appendLog(line);
                if (uiCb != null) uiCb.onLine(line);
                updateNotificationBrief(line);
            });
            children.add(pMain);

            // 监控线程：等待主进程退出
            new Thread(() -> {
                try {
                    int code = pMain.waitFor();
                    appendLog("Main process exit code=" + code);
                } catch (InterruptedException ignored) {
                } finally {
                    stopStress();
                }
            }).start();

            updateNotificationState(true, "Running...");
        } catch (Exception e) {
            appendLog("Start error: " + e);
            running = false;
            updateNotificationState(false, "Error start");
        }
    }

    public void stopStress() {
        if (!running) return;
        for (Process p : children) {
            try { p.destroy(); } catch (Throwable ignored) {}
        }
        for (Process p : children) {
            try {
                p.waitFor();
            } catch (Throwable ignored) {}
        }
        children.clear();
        running = false;
        updateNotificationState(false, "Stopped");
        appendLog("Stopped.");
    }

    private void appendLog(String s) {
        synchronized (logBuf) {
            logBuf.append(s).append('\n');
        }
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL_ID, "USB Stress", NotificationManager.IMPORTANCE_LOW);
            NotificationManager nm = getSystemService(NotificationManager.class);
            nm.createNotificationChannel(ch);
        }
    }

    private Notification buildNotif(String text) {
        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("USB IO Stress")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_sys_upload)
                .setOngoing(true)
                .build();
    }

    private void updateNotificationState(boolean running, String text) {
        Notification n = buildNotif(text);
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        nm.notify(1, n);
    }

    private void updateNotificationBrief(String line) {
        // 可按需截断
        if (line == null) return;
        if (line.length() > 60) line = line.substring(0, 60);
        updateNotificationState(true, line);
    }

    public static class StressParams {
        public String mountPath;
        public int procs = 1;
        public int files = 1;
        public int block = 4096;
        public long maxSize = 16L * 1024 * 1024;
        public long durSec = 0L;
        public boolean sync = true;
        public boolean append = true;
        public boolean verify = true;
        public String prefix = "stress_";
        public boolean clean = true;

        @Override
        public String toString() {
            return "mount=" + mountPath + " procs=" + procs + " files=" + files + " block=" + block +
                    " maxSize=" + maxSize + " dur=" + durSec + " sync=" + sync + " append=" + append +
                    " verify=" + verify + " prefix=" + prefix + " clean=" + clean;
        }
    }
}
```

5) MainActivity.java
一个简单的表单页面，支持选择目录（SAF）或手输路径，启动/停止，并实时显示日志。

```java
package com.example.usbstresstool;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.provider.DocumentsContract;
import android.text.method.ScrollingMovementMethod;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.documentfile.provider.DocumentFile;

public class MainActivity extends AppCompatActivity {

    private EditText etMount, etProcs, etFiles, etBlock, etMaxSize, etDur, etPrefix;
    private CheckBox cbSync, cbAppend, cbVerify, cbClean;
    private Button btnChoose, btnStart, btnStop, btnClear;
    private TextView tvLog;

    private StressService svc;
    private boolean bound = false;

    private final ActivityResultLauncher<Uri> openDirLauncher =
            registerForActivityResult(new ActivityResultContracts.OpenDocumentTree(),
                    new ActivityResultCallback<Uri>() {
                        @Override
                        public void onActivityResult(Uri uri) {
                            if (uri != null) {
                                // 保留权限
                                final int flags = Intent.FLAG_GRANT_READ_URI_PERMISSION |
                                        Intent.FLAG_GRANT_WRITE_URI_PERMISSION |
                                        Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION;
                                try {
                                    getContentResolver().takePersistableUriPermission(uri, flags);
                                } catch (Exception ignored) {}
                                // 尝试解析物理路径（仅显示用途），真正访问仍走进程的文件路径
                                String display = uri.toString();
                                etMount.setText(display);
                                Toast.makeText(MainActivity.this, "已选择目录: " + display, Toast.LENGTH_SHORT).show();
                            }
                        }
                    });

    private final ServiceConnection conn = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            StressService.LocalBinder b = (StressService.LocalBinder) service;
            svc = b.getService();
            bound = true;
            tvLog.setText(svc.getLogs());
            updateButtons();
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            bound = false;
            svc = null;
            updateButtons();
        }
    };

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        etMount = findViewById(R.id.et_mount);
        etProcs = findViewById(R.id.et_procs);
        etFiles = findViewById(R.id.et_files);
        etBlock = findViewById(R.id.et_block);
        etMaxSize = findViewById(R.id.et_max_size);
        etDur = findViewById(R.id.et_dur);
        etPrefix = findViewById(R.id.et_prefix);

        cbSync = findViewById(R.id.cb_sync);
        cbAppend = findViewById(R.id.cb_append);
        cbVerify = findViewById(R.id.cb_verify);
        cbClean = findViewById(R.id.cb_clean);

        btnChoose = findViewById(R.id.btn_choose);
        btnStart = findViewById(R.id.btn_start);
        btnStop = findViewById(R.id.btn_stop);
        btnClear = findViewById(R.id.btn_clear);
        tvLog = findViewById(R.id.tv_log);
        tvLog.setMovementMethod(ScrollingMovementMethod.getInstance());

        // 默认值
        etProcs.setText("4");
        etFiles.setText("2");
        etBlock.setText("65536");
        etMaxSize.setText(String.valueOf(128 * 1024 * 1024));
        etDur.setText("0");
        etPrefix.setText("stress_");
        cbSync.setChecked(true);
        cbAppend.setChecked(true);
        cbVerify.setChecked(true);
        cbClean.setChecked(true);

        btnChoose.setOnClickListener(v -> {
            openDirLauncher.launch(null);
        });

        btnStart.setOnClickListener(v -> {
            if (!bound || svc == null) return;
            StressService.StressParams p = collectParams();
            if (p == null) return;

            // 如果用户通过 SAF 选择了 Uri（以 content://），则一般 App 自己无法用文件路径写。
            // 这里有两个选项：
            // 1) 推荐：让用户填写真实挂载路径（/storage/XXXX-XXXX）。我们直接用路径。
            // 2) 或者：实现基于 SAF 的写入逻辑（我可以提供 UsbIoWorker 的 SAF 版）。
            if (p.mountPath.startsWith("content://")) {
                Toast.makeText(this, "当前 demo 使用文件路径访问，请填写 /storage/XXXX-XXXX 实际路径；如需 SAF 版请告知。", Toast.LENGTH_LONG).show();
                return;
            }

            svc.startStress(p, line -> runOnUiThread(() -> {
                appendLog(line);
            }));
            updateButtons();
        });

        btnStop.setOnClickListener(v -> {
            if (bound && svc != null) svc.stopStress();
            updateButtons();
        });

        btnClear.setOnClickListener(v -> {
            tvLog.setText("");
        });

        // 绑定并启动前台服务
        Intent it = new Intent(this, StressService.class);
        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(it);
        } else {
            startService(it);
        }
        bindService(it, conn, Context.BIND_AUTO_CREATE);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (bound) {
            unbindService(conn);
            bound = false;
        }
    }

    private void appendLog(String s) {
        tvLog.append(s + "\n");
        // 滚动到底部
        final int scrollAmount = tvLog.getLayout() == null ? 0 :
                tvLog.getLayout().getLineTop(tvLog.getLineCount()) - tvLog.getHeight();
        if (scrollAmount > 0) tvLog.scrollTo(0, scrollAmount);
        else tvLog.scrollTo(0, 0);
    }

    private StressService.StressParams collectParams() {
        StressService.StressParams p = new StressService.StressParams();
        p.mountPath = etMount.getText().toString().trim();
        if (p.mountPath.isEmpty()) {
            Toast.makeText(this, "请输入或选择 U 盘路径（例如 /storage/XXXX-XXXX）", Toast.LENGTH_SHORT).show();
            return null;
        }
        try {
            p.procs = Integer.parseInt(etProcs.getText().toString().trim());
            p.files = Integer.parseInt(etFiles.getText().toString().trim());
            p.block = Integer.parseInt(etBlock.getText().toString().trim());
            p.maxSize = Long.parseLong(etMaxSize.getText().toString().trim());
            p.durSec = Long.parseLong(etDur.getText().toString().trim());
        } catch (NumberFormatException e) {
            Toast.makeText(this, "数字参数格式错误", Toast.LENGTH_SHORT).show();
            return null;
        }
        p.sync = cbSync.isChecked();
        p.append = cbAppend.isChecked();
        p.verify = cbVerify.isChecked();
        p.clean = cbClean.isChecked();
        p.prefix = etPrefix.getText().toString().trim();
        if (p.procs <= 0 || p.files <= 0 || p.block <= 0) {
            Toast.makeText(this, "procs/files/block 必须 > 0", Toast.LENGTH_SHORT).show();
            return null;
        }
        return p;
    }

    private void updateButtons() {
        boolean running = bound && svc != null && svc.isRunning();
        btnStart.setEnabled(!running);
        btnStop.setEnabled(running);
    }
}
```

6) activity_main.xml
一个紧凑表单布局。

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <LinearLayout
        android:padding="16dp"
        android:orientation="vertical"
        android:layout_width="match_parent"
        android:layout_height="wrap_content">

        <LinearLayout
            android:orientation="horizontal"
            android:layout_width="match_parent"
            android:layout_height="wrap_content">
            <EditText
                android:id="@+id/et_mount"
                android:hint="/storage/XXXX-XXXX"
                android:inputType="text"
                android:layout_width="0dp"
                android:layout_weight="1"
                android:layout_height="wrap_content"/>
            <Button
                android:id="@+id/btn_choose"
                android:text="选择目录"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"/>
        </LinearLayout>

        <EditText
            android:id="@+id/et_procs"
            android:hint="进程数"
            android:inputType="number"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <EditText
            android:id="@+id/et_files"
            android:hint="每进程文件数"
            android:inputType="number"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <EditText
            android:id="@+id/et_block"
            android:hint="块大小(字节)"
            android:inputType="number"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <EditText
            android:id="@+id/et_max_size"
            android:hint="单文件最大大小(字节)"
            android:inputType="number"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <EditText
            android:id="@+id/et_dur"
            android:hint="持续时长(秒, 0=不限)"
            android:inputType="number"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <EditText
            android:id="@+id/et_prefix"
            android:hint="文件名前缀"
            android:inputType="text"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <LinearLayout
            android:orientation="horizontal"
            android:layout_width="match_parent"
            android:layout_height="wrap_content">
            <CheckBox
                android:id="@+id/cb_sync"
                android:text="fsync"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"/>
            <CheckBox
                android:id="@+id/cb_append"
                android:text="追加/环绕"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"/>
            <CheckBox
                android:id="@+id/cb_verify"
                android:text="读后校验"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"/>
            <CheckBox
                android:id="@+id/cb_clean"
                android:text="退出清理"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"/>
        </LinearLayout>

        <LinearLayout
            android:orientation="horizontal"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp">
            <Button
                android:id="@+id/btn_start"
                android:text="开始"
                android:layout_width="0dp"
                android:layout_weight="1"
                android:layout_height="wrap_content"/>
            <Button
                android:id="@+id/btn_stop"
                android:text="停止"
                android:layout_width="0dp"
                android:layout_weight="1"
                android:layout_height="wrap_content"/>
            <Button
                android:id="@+id/btn_clear"
                android:text="清空日志"
                android:layout_width="0dp"
                android:layout_weight="1"
                android:layout_height="wrap_content"/>
        </LinearLayout>

        <TextView
            android:id="@+id/tv_log"
            android:textIsSelectable="true"
            android:paddingTop="8dp"
            android:background="#111111"
            android:textColor="#ffffff"
            android:minHeight="200dp"
            android:scrollbars="vertical"
            android:textSize="12sp"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>
    </LinearLayout>
</ScrollView>
```

7) strings.xml
```xml
<resources>
    <string name="app_name">USB IO Stress</string>
</resources>
```

8) AndroidManifest.xml
- 前台服务声明
- 必需权限：READ_EXTERNAL_STORAGE/WRITE_EXTERNAL_STORAGE 在 Android 11 上对分区存储不再通用；我们仍然声明，主要用于老设备。实际推荐通过真实挂载路径访问（/storage/XXXX-XXXX）并在目标设备上允许 App 有该目录权限；或通过 SAF Uri 访问（需要在代码中改造 Worker）。
- 查询 SAF 需要 REQUEST_INSTALL_PACKAGES 吗？不需要。
- 添加 android:requestLegacyExternalStorage="true" 仅对 Android 10 有效；Android 11+ 无效。

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.usbstresstool"
    xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- 旧版外部存储权限（Android 11+ 基本无效，仅兼容性） -->
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29"/>

    <!-- 前台服务 -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" tools:ignore="MissingPrefix"/>
    <!-- 若需持久通知中的小图标 -->
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" android:required="false" />

    <application
        android:label="@string/app_name"
        android:allowBackup="false"
        android:supportsRtl="true"
        android:theme="@style/Theme.MaterialComponents.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

        <service
            android:name=".StressService"
            android:exported="false"
            android:foregroundServiceType="dataSync|mediaPlayback">
        </service>
    </application>
</manifest>
```

注意：
- 如果使用 Android Gradle Plugin 8/targetSdkVersion 34，POST_NOTIFICATIONS 需要动态请求（Android 13+）。这里可在首次启动提示授权，但即使不授权也不影响前台服务运行，只是通知提示可能受限。
- FOREGROUND_SERVICE_SPECIAL_USE 在普通应用不需要，去掉即可；保留 FOREGROUND_SERVICE 即可。上面仅示例。

9) 运行与限制说明
- 非 root 环境下，app_process 子进程继承应用权限，直接对 /storage/XXXX-XXXX 写入，是否可行取决于设备 ROM 的存储策略。很多原生设备对公开外部存储卷在 /storage/XXXX-XXXX 允许普通应用进行文件读写（无需 MANAGE_EXTERNAL_STORAGE）。若受限：
  - 方案 A：把 UsbIoWorker 改为基于 SAF 的 DocumentFile + ParcelFileDescriptor 版本，在 Activity 中用户选择到 USB 根目录后，将 Uri 传入，子进程无需 app_process，直接在应用内多线程模拟 I/O。
  - 方案 B：目标设备是工程机/系统签名应用，可授予 MANAGE_EXTERNAL_STORAGE 或直接运行于 shell/adb 用户。
- 如果你更偏好“在一个进程内使用多线程”而不是多进程，我可以给出同 UI 的纯线程版本，避免 app_process 与路径权限问题。

10) 构建与测试步骤（简要）
- 将上述文件放入 Android 项目，minSdk 21，targetSdk 33/34。
- 编译安装到设备。
- 插入 U 盘，确认挂载路径，例如 /storage/1234-ABCD。
- 在界面填入该路径与参数，点击开始，观察日志滚动。

需要我：
- 提供基于 SAF 的 UsbIoWorker 实现（可运行在普通应用权限下，不依赖 /storage 直写）？
- 提供纯线程版（不启动子进程，用线程池模拟 N 进程负载）？
- 或者适配特定品牌 ROM 的存储策略（例如必须走 StorageManager/VolumeInfo 枚举 U 盘路径）？

# 包名更改

如果你改了应用的包名（例如从 com.example.usbstresstool 改为 com.acme.usbstress），需要同步改两处，确保命令行能正确找到入口类：

1) 修改 CliMain.java 的 package 声明与类的完全限定名
- 文件头部的 package 必须与新包名一致。
- 例如原来：
  package com.example.usbstresstool;
  改为：
  package com.acme.usbstress;

- 文件中引用到入口类名的字符串常量（如果有）也要改。上面示例工程里有两处地方内含全限定类名：
  - CliMain.buildSelfCommand(...) 里：
    String className = "com.example.usbstresstool.CliMain";
    改为：
    String className = "com.acme.usbstress.CliMain";

2) 修改 ProcUtils 中的入口类名
- ProcUtils.startCliProcess(...) 里同样写死了入口类名：
  String entry = "com.example.usbstresstool.CliMain";
  改为：
  String entry = "com.acme.usbstress.CliMain";

命令行调用方式不变，但要确保 CLASSPATH 指向你 APK 的路径，并使用新的类名。示例：

- 设备上通过 app_process 调用（在应用沙箱内或 adb shell）：
  CLASSPATH=/data/app/你的包名-xxxx/base.apk app_process /system/bin com.acme.usbstress.CliMain --mount-path /storage/XXXX-XXXX --procs 4 --files 2 ...

注意事项与排错要点
- apk 路径：在应用内启动时，代码使用 Context.getPackageCodePath() 自动获取 base.apk 路径；若你在 adb shell 手工调用，需要先找到实际 apk 路径（不同设备路径可能略有差异）。可以用 pm path com.acme.usbstress 获取：
  adb shell pm path com.acme.usbstress
  输出如：package:/data/app/~~abcd1234==/com.acme.usbstress-xyz/base.apk
  然后取冒号后面的路径作为 CLASSPATH。

- 权限与用户：
  - 在应用内调用 ProcUtils 会以应用 uid 运行，权限与 App 相同。
  - 在 adb shell 下直调时，进程以 shell 用户运行，可能没有对 /storage/XXXX-XXXX 的写权限；如需测试，建议在应用内发起，或使用适合的存储路径策略（SAF 版本）。

- 进程自举：
  - CliMain.buildSelfCommand 会把 --procs 强制改为 1，并用 app_process 再次拉起自身类。这串 className 必须与当前包名一致，否则子进程会报 ClassNotFoundException。

- 混淆/压缩：
  - 若开启 R8/ProGuard，请把入口类保留不被裁剪：
    -keep class com.acme.usbstress.CliMain { public static void main(...); }

- 目标 SDK 和 POST_NOTIFICATIONS：
  - 与命令行入口无关，但前台服务通知在 Android 13+ 可能需要动态授权。

快速清单（你需要做的改动）
- CliMain.java 顶部 package 改为新包名。
- CliMain.buildSelfCommand 内 className 改为 新包名.CliMain。
- ProcUtils.java 内 entry 改为 新包名.CliMain。
-（可选）proguard-rules.pro 增加 keep 规则，防止 main 被移除。

# 寻找base.apk路径 

简短回答：
- 是的，base.apk 是应用在设备端安装后的“主 split”APK 文件名。
- 用 adb install 安装普通（非分包）的 APK 后，设备端通常会把它展开为 base.apk（以及可能的其他 split，如 config-xx.apk）。命令行里用的 CLASSPATH 就指向这个 base.apk。
- 正确做法是不要自己猜路径，始终用 pm path 包名 去拿实际路径。

详细说明：
- 从 Android 5.0 起，系统支持 split APK。安装后，每个应用目录下会有一个或多个 split 文件，主 split 统一命名为 base.apk，其他按 split 名称命名（如 split_config.armeabi_v7a.apk、split_config.xxhdpi.apk 等）。
- 无论你是通过 adb install app-release.apk 还是通过应用商店安装，设备端最终都会把应用文件放到 /data/app/.../ 下，并把主 split 命名为 base.apk。
- 这个路径包含随机后缀，不能硬编码。例如：
  adb shell pm path com.acme.usbstress
  可能输出多行：
  package:/data/app/~~abcd123.../com.acme.usbstress-xyz==/base.apk
  package:/data/app/~~abcd123.../com.acme.usbstress-xyz==/split_config.arm64_v8a.apk
  package:/data/app/~~abcd123.../com.acme.usbstress-xyz==/split_config.zh.apk
- 你在命令行用 app_process 启动 Java 主类时，CLASSPATH 只需要包含主 dex 的 APK，一般就是 base.apk；如果你的代码或依赖被放到了其他 split（很少见，通常代码都在 base），也可以把多个 split 通过冒号拼接到 CLASSPATH。

推荐调用步骤（adb shell 下）：
1) 查路径
   adb shell pm path com.acme.usbstress
2) 取出 base.apk 路径（去掉前缀 package:）
3) 调用
   adb shell 'CLASSPATH=/data/app/~~.../base.apk app_process /system/bin com.acme.usbstress.CliMain --args...'

在应用内启动子进程的情况：
- 代码里通常用 Context.getPackageCodePath() 获取当前应用主 APK 的完整路径，它返回的就是 base.apk 的实际路径，无需你关心分包和随机目录。

常见坑：
- 不同 Android 版本、厂商路径格式略不同，务必依赖 pm path。
- 权限差异：adb shell 进程是 shell 用户，不一定能写外部存储的某些挂载点；应用内拉起子进程则拥有应用的同等权限。
- ProGuard/R8 可能裁剪 main 方法，记得 keep 入口类。