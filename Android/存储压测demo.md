下面给你一个可直接用于打桩/压测的 Android 命令行 Demo，采用 Java 实现，适配 Android 11+。它可以按参数创建任意数量的子进程，每个进程持续对外接 U 盘上的文件进行读写（顺序/环绕、可选 fsync、可选读后校验），支持限定运行时长与文件大小。

要点与前提
- 运行环境：Android 11+（API 30+）。
- 典型运行方式：adb shell 下通过 app_process 启动（shell 用户通常对挂载的 U 盘目录有读写权限）。
- U 盘路径：通常为 /storage/XXXX-XXXX（公共可见），或 /mnt/media_rw/XXXX-XXXX（可能受权限限制）。示例以 /storage/XXXX-XXXX 为主。
- 权限提示：在普通 App 沙盒内直写可能受限；如需在 App 内运行，请改造为使用 SAF(DocumentFile + ParcelFileDescriptor)。若你需要，我可以提供 SAF 版本。
- 注意：高强度 I/O 会加速 U 盘磨损，请使用测试介质。

功能概览
- 参数化控制：进程数、每进程文件数、块大小、每文件最大大小、持续时长、是否 fsync、是否读后校验、是否追加/环绕写入、文件名前缀、退出清理。
- 多进程：主进程用 ProcessBuilder 拉起 N 个子进程（每个子进程将 --procs 强制为 1）。
- 每进程逻辑：循环对若干文件进行写入（可 fsync），随后可选读取校验；到达大小上限后环绕覆盖。
- 统计日志：周期性输出写入/读取累计量与错误计数。

源码（Java，完整可编译）
文件 1/2：UsbIoWorker.java
```java
package com.example.usbstresstool;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.util.Random;
import java.util.concurrent.atomic.AtomicBoolean;

public class UsbIoWorker implements Runnable {
    private final String mountPath;
    private final int fileCount;
    private final int blockSize;
    private final long maxSizeBytes;
    private final boolean doFsync;
    private final boolean appendMode;
    private final boolean doVerify;
    private final String prefix;

    private final AtomicBoolean stopFlag = new AtomicBoolean(false);
    private final Random rng = new Random(System.nanoTime());

    public UsbIoWorker(String mountPath,
                       int fileCount,
                       int blockSize,
                       long maxSizeBytes,
                       boolean doFsync,
                       boolean appendMode,
                       boolean doVerify,
                       String prefix) {
        this.mountPath = mountPath;
        this.fileCount = fileCount;
        this.blockSize = blockSize;
        this.maxSizeBytes = maxSizeBytes;
        this.doFsync = doFsync;
        this.appendMode = appendMode;
        this.doVerify = doVerify;
        this.prefix = prefix;
    }

    public void requestStop() {
        stopFlag.set(true);
    }

    @Override
    public void run() {
        int code = runLoop();
        System.out.println("Worker exit code=" + code);
    }

    public int runLoop() {
        File baseDir = new File(mountPath);
        if (!baseDir.exists() || !baseDir.isDirectory() || !baseDir.canWrite()) {
            System.err.println("! mountPath not writable or not a dir: " + mountPath);
            return 2;
        }

        File[] files = new File[fileCount];
        FileChannel[] channels = new FileChannel[fileCount];
        try {
            for (int i = 0; i < fileCount; i++) {
                files[i] = new File(baseDir, prefix + "p" + android.os.Process.myPid() + "_" + i + ".dat");
                if (!files[i].exists()) {
                    try {
                        files[i].createNewFile();
                    } catch (IOException e) {
                        System.err.println("! create file failed: " + files[i].getAbsolutePath() + " err=" + e);
                        return 2;
                    }
                }
                RandomAccessFile raf = new RandomAccessFile(files[i], "rw");
                if (appendMode) {
                    raf.seek(raf.length());
                } else {
                    raf.setLength(0L);
                }
                channels[i] = raf.getChannel();
            }

            byte[] template = new byte[blockSize];
            rng.nextBytes(template);

            long totalWrites = 0L;
            long totalReads = 0L;
            long totalErrors = 0L;
            long nextReport = System.currentTimeMillis() + 2000L;

            outer:
            while (!stopFlag.get()) {
                for (int i = 0; i < channels.length; i++) {
                    if (stopFlag.get()) break outer;
                    FileChannel ch = channels[i];
                    File f = files[i];

                    long currentSize = f.length();
                    long nextPos = appendMode ? currentSize : (currentSize % maxSizeBytes);
                    long remaining = maxSizeBytes - (nextPos % maxSizeBytes);
                    int writeLen = (int) Math.min(blockSize, remaining);

                    byte[] buf = template.clone();
                    // 写入头部 16 字节信息：时间戳与计数器，降低缓存伪命中
                    long ts = System.nanoTime();
                    for (int k = 0; k < Math.min(8, buf.length); k++) {
                        buf[k] = (byte) ((ts >>> (k * 8)) & 0xFF);
                    }
                    long wCount = totalWrites;
                    for (int k = 0; k < Math.min(8, Math.max(0, buf.length - 8)); k++) {
                        buf[8 + k] = (byte) ((wCount >>> (k * 8)) & 0xFF);
                    }

                    // 写入
                    try {
                        ch.position(nextPos);
                        ByteBuffer bb = ByteBuffer.wrap(buf, 0, writeLen);
                        while (bb.hasRemaining()) {
                            ch.write(bb);
                        }
                        if (doFsync) ch.force(true);
                        totalWrites++;
                    } catch (IOException e) {
                        System.err.println("! write error file=" + f.getName() + " pos=" + nextPos + " err=" + e);
                        totalErrors++;
                    }

                    // 读回校验
                    if (doVerify) {
                        try {
                            byte[] verifyBuf = new byte[writeLen];
                            ByteBuffer rb = ByteBuffer.wrap(verifyBuf);
                            ch.position(nextPos);
                            int r = 0;
                            while (rb.hasRemaining()) {
                                int once = ch.read(rb);
                                if (once < 0) break;
                                r += once;
                            }
                            boolean ok = r == writeLen;
                            if (ok) {
                                // 与写入时前 writeLen 范围比较
                                byte[] expect = new byte[writeLen];
                                System.arraycopy(buf, 0, expect, 0, writeLen);
                                ok = arrayEquals(verifyBuf, expect);
                            }
                            if (!ok) {
                                totalErrors++;
                                System.err.println("! verify failed file=" + f.getName() + " pos=" + nextPos + " len=" + writeLen);
                            } else {
                                totalReads++;
                            }
                        } catch (IOException e) {
                            totalErrors++;
                            System.err.println("! read error file=" + f.getName() + " pos=" + nextPos + " err=" + e);
                        }
                    }

                    long now = System.currentTimeMillis();
                    if (now >= nextReport) {
                        double mbWrites = (totalWrites * (double) blockSize) / (1024.0 * 1024.0);
                        double mbReads = (totalReads * (double) blockSize) / (1024.0 * 1024.0);
                        System.out.printf("[pid=%d] writes=%d(%.2fMB) reads=%d(%.2fMB) errors=%d file=%s size=%d%n",
                                android.os.Process.myPid(), totalWrites, mbWrites, totalReads, mbReads, totalErrors,
                                f.getName(), f.length());
                        nextReport = now + 2000L;
                    }

                    // 文件大小环绕控制
                    if (appendMode) {
                        if (f.length() >= maxSizeBytes) {
                            try {
                                ch.truncate(0L);
                                ch.position(0L);
                            } catch (IOException e) {
                                System.err.println("! truncate error file=" + f.getName() + " err=" + e);
                            }
                        }
                    }
                }
            }

            return totalErrors == 0L ? 0 : 4;
        } catch (Throwable t) {
            System.err.println("! worker exception: " + t);
            t.printStackTrace();
            return 3;
        } finally {
            if (channels != null) {
                for (FileChannel ch : channels) {
                    if (ch != null) {
                        try { ch.force(true); } catch (Throwable ignored) {}
                        try { ch.close(); } catch (Throwable ignored) {}
                    }
                }
            }
        }
    }

    private static boolean arrayEquals(byte[] a, byte[] b) {
        if (a == b) return true;
        if (a == null || b == null) return false;
        if (a.length != b.length) return false;
        for (int i = 0; i < a.length; i++) {
            if (a[i] != b[i]) return false;
        }
        return true;
    }
}
```

文件 2/2：Main.java
```java
package com.example.usbstresstool;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class Main {

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

    private static void runSingle(Args args) {
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

    private static List<String> buildSelfCommand(String[] argv, Args args) {
        // 使用 app_process 启动当前 Main 类，强制子进程 --procs=1
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

        String className = "com.example.usbstresstool.Main";
        List<String> cmd = new ArrayList<>();
        cmd.add("/system/bin/app_process");
        cmd.add("/system/bin");
        cmd.add(className);
        cmd.addAll(newArgs);
        return cmd;
    }

    private static Args parseArgs(String[] argv) {
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

    private static boolean parseBool(String v, boolean defVal) {
        if (v == null) return defVal;
        if ("true".equalsIgnoreCase(v)) return true;
        if ("false".equalsIgnoreCase(v)) return false;
        return defVal;
    }

    private static String requireValue(String[] argv, int idx, String key) {
        if (idx >= argv.length) throw new IllegalArgumentException("missing value for " + key);
        return argv[idx];
    }

    private static String usage() {
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

编译与运行示例
- 准备：将上述两个类放入同包名目录 com/example/usbstresstool 下，编译为 jar 或 dex。
- 使用 d8 转 dex 并推送到设备：
  1) javac -source 1.8 -target 1.8 -bootclasspath <android-jar> -classpath <android-jar> -d out src/com/example/usbstresstool/*.java
  2) jar cf usbstresstool.jar -C out .
  3) d8 --release usbstresstool.jar --output usbstresstool.dex
  4) adb push usbstresstool.dex /data/local/tmp/
- 在设备上运行（adb shell）：
  - CLASSPATH=/data/local/tmp/usbstresstool.dex app_process /system/bin com.example.usbstresstool.Main --mount-path /storage/XXXX-XXXX --procs 4 --files 2 --block 65536 --max-size 134217728 --dur 300 --sync true --append true --verify true

实用提示
- 挂载点查找：adb shell ls /storage 或 cat /proc/mounts | grep -i vfat。
- 若报权限拒绝：
  - 使用 adb shell 运行更容易；或在工程设备上关闭部分限制。
  - 在 App 内运行请改为 SAF（我可以提供基于 DocumentFile/Uri 的版本）。
- 性能调整：
  - 提升吞吐：增大 --block（256KB~1MB），关闭 --verify 或 --sync。
  - 增加随机性：可在写入时随机选择 position（需要改造），或混合读写比例。
- 风险提示：长期压测会消耗 U 盘寿命；请不要在生产数据卷上测试。

如需我提供一个基于 Storage Access Framework 的“无 root/无 shell 权限”的 Java 版本（通过 Uri 访问 U 盘目录），或要把它封装进 APK 并在 App 内部用 Runtime.exec 拉起子进程，请告诉我你的具体形态需求，我可以给出完整代码。