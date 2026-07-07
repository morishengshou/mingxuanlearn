# Android 12 热更新 Java SDK 读取接口 —— 设计方案

> 面向 Android 12 SDK，提供 `getHotUpdateFiles()`、`getHotUpdateProps()`、`getHotUpdateFile()` 三接口的 Java 实现。
> 与 C++ 底层方案配合，本方案聚焦 Java 框架层的 API 设计、解析逻辑和健壮性保障。

---

## 一、设计总览

### 1.1 定位

| 层 | C++ 方案 | Java 方案 |
|---|---|---|
| 写接口 | `libhotupdate_writer.a`（链入 init） | 不暴露给 Java |
| 读接口（底层） | `libhotupdate_client.so`（C++ 动态库） | — |
| 读接口（SDK） | — | `android.app.HotUpdateManager`（纯 Java，在 framework 中实现） |

Java 方案**不依赖 JNI**，直接以纯 Java 读取 `/data/hotupdate/filelist` 和 `/data/hotupdate/proplist` 两个 TSV 文件。理由：

- 文件格式是简单两列 TSV 文本，Java 标准库即可胜任
- 框架层 Java 代码（`android.app.*`）具备读取 `/data` 下文件的 SELinux 权限
- 省去 JNI 边界的字符串拷贝和 native 崩溃风险
- 便于 App 开发者直接理解、调试、扩展

### 1.2 文件格式（回顾）

> 与 C++ 方案一致，采用**无类型前缀**的两列 TSV 格式。

`/data/hotupdate/filelist`：
```
# hotupdate file list v1
# filename<TAB>filepath
lib/libfoo.so	/system/lib64/libfoo.so
framework/framework.jar	/system/framework/framework.jar
app/MyApp/MyApp.apk	/system/app/MyApp/MyApp.apk
```

`/data/hotupdate/proplist`：
```
# hotupdate prop list v1
# propname<TAB>proppath
persist.sys.hotupdate.enable	/data/local.prop
ro.vendor.build.fingerprint	/vendor/build.prop
```

---

## 二、API 设计

### 2.1 类定义

```java
package android.app;

import android.annotation.IntDef;
import android.annotation.NonNull;
import android.annotation.Nullable;

import java.io.File;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 热更新文件记录读取接口。
 *
 * <p>读取 /data/hotupdate/ 下的 filelist 和 proplist，为 App 提供
 * 热更新文件列表和文件定位能力。
 *
 * <p>使用方式：
 * <pre>{@code
 * HotUpdateManager hu = HotUpdateManager.getInstance();
 *
 * // 获取所有热更新文件名
 * ArrayList<String> files = hu.getHotUpdateFiles();
 *
 * // 查找特定热更新文件
 * File f = hu.getHotUpdateFile("lib/libfoo.so", HotUpdateManager.TYPE_FILE);
 * if (f != null) {
 *     // f 指向 /data/hotupdate/para/lib/libfoo.so
 * }
 * }</pre>
 *
 * <p>线程安全：本类内部无共享可变状态，所有方法均线程安全。
 * <p>权限要求：调用方需具备 SELinux hotupdate_reader_domain 权限
 *     （系统默认对 platform_app / system_server 等开放）。
 */
public final class HotUpdateManager {

    private static final String TAG = "HotUpdateManager";

    // === 路径常量 ===
    private static final String HOTUPDATE_DIR   = "/data/hotupdate";
    private static final String FILE_LIST_PATH  = "/data/hotupdate/filelist";
    private static final String PROP_LIST_PATH  = "/data/hotupdate/proplist";
    private static final String PARA_DIR        = "/data/hotupdate/para/";

    // === 安全上限 ===
    private static final int MAX_RECORDS  = 4096;
    private static final int MAX_KEY_LEN  = 255;
    private static final int MAX_PATH_LEN = 4096;
    private static final int MAX_LINE_LEN = 8192;  // key + \t + value 的总长度上限

    // === 类型常量 ===

    /** 在 filelist 中查找文件记录 */
    public static final int TYPE_FILE = 0;

    /** 在 proplist 中查找属性记录 */
    public static final int TYPE_PROP = 1;

    /** @hide */
    @IntDef({TYPE_FILE, TYPE_PROP})
    @Retention(RetentionPolicy.SOURCE)
    public @interface HotUpdateType {}

    // === 单例 ===

    private static volatile HotUpdateManager sInstance;

    /**
     * 获取 HotUpdateManager 实例。
     *
     * @return 全局唯一实例，永不返回 null
     */
    @NonNull
    public static HotUpdateManager getInstance() {
        if (sInstance == null) {
            synchronized (HotUpdateManager.class) {
                if (sInstance == null) {
                    sInstance = new HotUpdateManager();
                }
            }
        }
        return sInstance;
    }

    private HotUpdateManager() {}
```

### 2.2 接口一：`getHotUpdateFiles()`

```java
    /**
     * 读取 /data/hotupdate/filelist，返回所有热更新文件的文件名列表。
     *
     * <p>文件名是相对路径（如 "lib/libfoo.so"、"framework/framework.jar"），
     * 可用于 {@link #getHotUpdateFile(String, int)} 定位实际文件。
     *
     * <p>返回值保证：
     * <ul>
     *   <li>绝不返回 null（文件不存在或读取失败时返回空列表）</li>
     *   <li>绝不抛异常</li>
     *   <li>按首次出现顺序排列，已去重</li>
     *   <li>最多返回 {@value #MAX_RECORDS} 条</li>
     * </ul>
     *
     * @return 文件名列表，不含注释行和非法行
     */
    @NonNull
    public ArrayList<String> getHotUpdateFiles() {
        return readFirstColumn(FILE_LIST_PATH);
    }
```

### 2.3 接口二：`getHotUpdateProps()`

```java
    /**
     * 读取 /data/hotupdate/proplist，返回所有热更新属性的属性名列表。
     *
     * <p>返回值保证：
     * <ul>
     *   <li>绝不返回 null（文件不存在或读取失败时返回空列表）</li>
     *   <li>绝不抛异常</li>
     *   <li>按首次出现顺序排列，已去重</li>
     *   <li>最多返回 {@value #MAX_RECORDS} 条</li>
     * </ul>
     *
     * @return 属性名列表，不含注释行和非法行
     */
    @NonNull
    public ArrayList<String> getHotUpdateProps() {
        return readFirstColumn(PROP_LIST_PATH);
    }
```

### 2.4 接口三：`getHotUpdateFile()`

```java
    /**
     * 在列表文件中查找指定 key，找到则返回对应热更新文件的 {@link File} 对象。
     *
     * <p>查找逻辑：
     * <ol>
     *   <li>根据 type 选择 filelist（TYPE_FILE=0）或 proplist（TYPE_PROP=1）</li>
     *   <li>逐行解析，用 pathSuffix 与 key 列做精确匹配</li>
     *   <li>第一个匹配行命中即停止</li>
     *   <li>拼接 /data/hotupdate/para/ + key 作为返回路径</li>
     * </ol>
     *
     * <p>返回的 File 仅表示路径已登记在列表中，调用方可进一步用
     * {@link File#exists()} 验证文件是否已在磁盘上就绪。
     *
     * @param pathSuffix 待查 key，即 filelist 中的 filename 或 proplist 中的 propname。
     *                   必须是合法相对路径（可含 `/`，不可含 `..`、`\t`、`\n` 等）。
     * @param type 查找目标：{@link #TYPE_FILE} 或 {@link #TYPE_PROP}
     * @return 找到则返回 File 对象；未找到或参数非法返回 null
     */
    @Nullable
    public File getHotUpdateFile(@NonNull String pathSuffix, @HotUpdateType int type) {
        // 1. 参数校验
        if (pathSuffix == null || pathSuffix.isEmpty()) {
            Log.w(TAG, "getHotUpdateFile: pathSuffix is null or empty");
            return null;
        }
        if (!isValidKey(pathSuffix)) {
            Log.w(TAG, "getHotUpdateFile: pathSuffix contains invalid chars: " + pathSuffix);
            return null;
        }

        final String listPath;
        if (type == TYPE_FILE) {
            listPath = FILE_LIST_PATH;
        } else if (type == TYPE_PROP) {
            listPath = PROP_LIST_PATH;
        } else {
            Log.w(TAG, "getHotUpdateFile: unsupported type=" + type);
            return null;
        }

        // 2. 逐行读取并匹配
        String matchedKey = findKeyInList(listPath, pathSuffix);
        if (matchedKey == null) {
            return null;
        }

        // 3. 拼接绝对路径
        return new File(PARA_DIR + matchedKey);
    }
```

---

## 三、内部实现（私有方法）

### 3.1 核心解析：`readFirstColumn()`

```java
    /**
     * 读取 TSV 文件的第一列，去重后返回。
     *
     * <p>容错策略：
     * <ul>
     *   <li>文件不存在或不可读 → 返回空列表</li>
     *   <li>单行非法（缺 tab、多 tab、含禁止字符、key 超长）→ 跳过该行并 log</li>
     *   <li>文件超大 → 读至上限后停止</li>
     *   <li>尾部半行 → 跳过</li>
     * </ul>
     */
    @NonNull
    private ArrayList<String> readFirstColumn(@NonNull String path) {
        ArrayList<String> result = new ArrayList<>();
        java.util.HashSet<String> seen = new java.util.HashSet<>();

        File file = new File(path);
        if (!file.isFile()) {
            return result;
        }

        try (java.io.BufferedReader reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(
                        new java.io.FileInputStream(file),
                        java.nio.charset.StandardCharsets.UTF_8))) {

            String line;
            int lineCount = 0;

            while ((line = reader.readLine()) != null) {
                lineCount++;

                // 行数硬上限（防御性编程）
                if (lineCount > MAX_RECORDS * 2) {
                    Log.w(TAG, path + ": too many lines, stop reading");
                    break;
                }

                // 跳过空行和注释
                if (line.isEmpty() || line.charAt(0) == '#') {
                    continue;
                }

                // 跳过超长行（可能是损坏数据）
                if (line.length() > MAX_LINE_LEN) {
                    Log.w(TAG, path + ": line " + lineCount + " too long, skip");
                    continue;
                }

                // 找第一个 \t
                int tab = line.indexOf('\t');
                if (tab <= 0) {  // 无分隔符或 key 为空
                    Log.w(TAG, path + ": line " + lineCount + " has no valid tab separator");
                    continue;
                }

                // 确保只有两列：不能有第二个 \t
                if (line.indexOf('\t', tab + 1) != -1) {
                    Log.w(TAG, path + ": line " + lineCount + " has more than one tab, skip");
                    continue;
                }

                String key = line.substring(0, tab);
                String value = line.substring(tab + 1);

                // value 不能为空
                if (value.isEmpty()) {
                    Log.w(TAG, path + ": line " + lineCount + " has empty value, skip");
                    continue;
                }

                // key 长度校验
                if (key.length() > MAX_KEY_LEN) {
                    Log.w(TAG, path + ": line " + lineCount + " key too long, skip");
                    continue;
                }

                // 禁止字符校验
                if (containsForbiddenChars(key) || containsForbiddenChars(value)) {
                    Log.w(TAG, path + ": line " + lineCount + " contains forbidden chars, skip");
                    continue;
                }

                // 去重（保留首次出现）
                if (seen.add(key) && result.size() < MAX_RECORDS) {
                    result.add(key);
                }
            }

        } catch (java.io.FileNotFoundException e) {
            // 文件不存在，返回空列表（正常情况）
        } catch (java.io.IOException e) {
            Log.w(TAG, "IO error reading " + path, e);
        } catch (SecurityException e) {
            Log.w(TAG, "Permission denied reading " + path, e);
        }

        return result;
    }
```

### 3.2 精确匹配：`findKeyInList()`

```java
    /**
     * 在 TSV 文件中精确匹配 key，返回匹配到的 key 字符串。
     *
     * <p>与 readFirstColumn 不同，此方法不做去重——找到第一个匹配行即返回，
     * 这对于"找到即退出"的查找场景更高效。
     *
     * @param path  列表文件路径
     * @param target 待匹配的 key
     * @return 匹配到的 key（等于 target），未找到返回 null
     */
    @Nullable
    private String findKeyInList(@NonNull String path, @NonNull String target) {
        File file = new File(path);
        if (!file.isFile()) {
            return null;
        }

        try (java.io.BufferedReader reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(
                        new java.io.FileInputStream(file),
                        java.nio.charset.StandardCharsets.UTF_8))) {

            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty() || line.charAt(0) == '#') {
                    continue;
                }

                int tab = line.indexOf('\t');
                if (tab <= 0) continue;
                if (line.indexOf('\t', tab + 1) != -1) continue;

                String key = line.substring(0, tab);

                // 精确匹配
                if (target.equals(key)) {
                    // 再做一次合法性快速校验
                    String value = line.substring(tab + 1);
                    if (!value.isEmpty()
                            && !containsForbiddenChars(key)
                            && !containsForbiddenChars(value)
                            && key.length() <= MAX_KEY_LEN) {
                        return key;
                    }
                }
            }

        } catch (java.io.IOException | SecurityException e) {
            Log.w(TAG, "Error searching in " + path, e);
        }

        return null;
    }
```

### 3.3 输入校验

```java
    /**
     * 校验 key 是否合法。
     * 禁止：空、控制字符、\t \n \r、以 / 或 # 开头、以 / 结尾、含 .. 或 //、含反斜杠。
     */
    private boolean isValidKey(@NonNull String key) {
        if (key.isEmpty() || key.length() > MAX_KEY_LEN) return false;
        if (key.charAt(0) == '/' || key.charAt(0) == '#') return false;
        if (key.charAt(key.length() - 1) == '/') return false;
        if (key.contains("..")) return false;
        if (key.contains("//")) return false;
        if (key.indexOf('\\') != -1) return false;
        return !containsForbiddenChars(key);
    }

    /**
     * 包含禁止字符（控制字符、\t \n \r \0）返回 true。
     */
    private boolean containsForbiddenChars(@NonNull String s) {
        for (int i = 0, len = s.length(); i < len; i++) {
            char c = s.charAt(i);
            if (c == '\t' || c == '\n' || c == '\r' || c == '\0') return true;
            if (c < 0x20 || c == 0x7F) return true;  // 所有控制字符
        }
        return false;
    }
}
```

---

## 四、Java vs C++ 设计差异说明

| 维度 | C++ | Java |
|------|-----|------|
| **单例** | 静态库链接，无需单例 | DCL（双检锁）volatile 单例 |
| **文件读取** | POSIX `open/read` | `BufferedReader` + `InputStreamReader(UTF-8)` |
| **锁** | `flock(LOCK_SH)` 共享锁 | 无需——C++ Writer 的 rename 原子替换已保证内容完整；若并发写了半行，Java 侧跳过畸形行即可 |
| **去重** | `std::set<string>` | `HashSet<String>` |
| **返回值** | `vector<string>` / `char*` (+ bufLen) | `ArrayList<String>` / `File`（天然 GC 管理，无缓冲区溢出风险） |
| **错误处理** | 返回 null / 空 vector | 返回 null / 空列表；异常全部内部捕获 |
| **getHotUpdateFile** | C 风格 `char* GetHotUpdateFile(pathSuffix, type, buf, bufLen)` | Java 风格 `File getHotUpdateFile(pathSuffix, type)`，返回 `File` 对象 |
| **类型常量** | `int type` (0/1) | `@IntDef` + `TYPE_FILE`/`TYPE_PROP` 编译期检查 |

### 为什么 Java 侧不加 flock？

C++ Writer 采用**原子 rename** 写入模式（写 tmp → fsync → rename），文件系统保证 rename 是原子的。这意味着：

- 读者打开文件时，要么读到完整旧版本，要么读到完整新版本
- 绝不可能读到"写到一半的行"
- Java 侧即使不做任何锁，也不会出现"读到半行崩溃"的问题

唯一的极端情况是写入过程中系统崩溃，导致文件末尾有半行数据——Java 侧通过跳过非法行（无 tab、缺 value、含禁止字符）自然容错。这比引入 `FileLock` 更简单且更可靠。

---

## 五、Android 框架集成

### 5.1 源码位置

```
frameworks/base/core/java/android/app/HotUpdateManager.java
```

### 5.2 如需通过 Context.getSystemService 获取

虽然静态 `getInstance()` 已足够好用，但如果要遵循 Android 惯例（如 `context.getSystemService(Context.HOTUPDATE_SERVICE)`），需要以下配套改动：

**① `frameworks/base/core/java/android/content/Context.java`**：

```java
public static final String HOTUPDATE_SERVICE = "hotupdate";
```

**② `frameworks/base/core/java/android/app/SystemServiceRegistry.java`**：

```java
registerService(Context.HOTUPDATE_SERVICE, HotUpdateManager.class,
        new CachedServiceFetcher<HotUpdateManager>() {
    @Override
    public HotUpdateManager createService(ContextImpl ctx) {
        return HotUpdateManager.getInstance();
    }
});
```

**③ 更新 API 签名**：

```bash
make update-api -j8
```

本文按"静态 getInstance"方式交付，简单直接。如团队有 Context 惯例要求，按上述三步骤改造即可。

### 5.3 Android.bp

HotUpdateManager 是纯 Java 类，直接放入 framework 的已有编译目标即可，无需独立 `java_library`。

它位于 `frameworks/base/core/java/android/app/` 目录下，会被 `framework.jar` 的构建自动纳入。确认 `frameworks/base/Android.bp` 中没有将 `android/app/` 排除即可。

### 5.4 API 签名更新

新增了公开类和方法，编译后必须运行：

```bash
make update-api -j8
```

这会自动将 `HotUpdateManager` 及其 public 方法写入 `frameworks/base/api/current.txt`。

---

## 六、健壮性设计清单

| 防护点 | 实现方式 |
|--------|----------|
| **绝不抛异常** | 所有 IOException / SecurityException 在内部 catch 并 log，返回安全默认值（空列表 / null） |
| **文件不存在** | `File.isFile()` 前置检查；FileNotFoundException 单独 catch |
| **畸形行** | 空行跳过、缺 tab 跳过、多 tab 跳过、空 value 跳过、禁止字符跳过、超长行跳过 |
| **尾部半行** | `BufferedReader.readLine()` 以 `\n`/`\r\n`/EOF 为界，尾部半行无换行符会被当作一行——此时因缺 tab 或缺 value 被跳过 |
| **超大数据** | 行数上限 `MAX_RECORDS * 2`、单行上限 `MAX_LINE_LEN`、key 上限 `MAX_KEY_LEN`、结果上限 `MAX_RECORDS` |
| **内存控制** | `HashSet` 和 `ArrayList` 上限为 `MAX_RECORDS`，不会无限增长 |
| **编码** | 显式指定 UTF-8（`StandardCharsets.UTF_8`），避免平台默认编码差异 |
| **路径安全** | key 禁止 `..`、`//`、以 `/` 开头、`\`，防止路径穿越 |
| **线程安全** | 无共享可变状态，每个方法调用创建独立数据结构 |
| **权限不足** | `SecurityException` 被捕获，返回安全默认值 |
| **单例安全** | DCL + volatile，防止指令重排导致的半初始化对象 |

---

## 七、与 C++ 方案的一致性对照

| C++ 函数 | Java 等效 | 行数对应 |
|----------|-----------|----------|
| `gethotupdatefiles()` | `getHotUpdateFiles()` | 直接对应 |
| `gethotupdateprops()` | `getHotUpdateProps()` | 直接对应 |
| `GetHotUpdateFile(pathSuffix, type, buf, bufLen)` | `getHotUpdateFile(pathSuffix, type)` | Java 返回 `File` 替代 C 的 buf 写入模式 |
| `ReadEntries(path)` | `readFirstColumn(path)` | 返回值不同：C++ 返回 `vector<pair>`，Java 只返第一列 |
| `ParseTsvLine(line, key, value)` | 内联于 `readFirstColumn()` | Java 直接将解析逻辑内联，避免额外对象分配 |
| `IsValidFileName()` | `isValidKey()` | Java 版本更宽松（允许 `/`，与 filename 语义一致） |
| `HasForbiddenChars()` | `containsForbiddenChars()` | 逻辑完全相同 |

---

## 八、App 开发者使用示例

### 8.1 读取所有热更新文件

```java
import android.app.HotUpdateManager;
import java.io.File;
import java.util.ArrayList;

HotUpdateManager hu = HotUpdateManager.getInstance();
ArrayList<String> files = hu.getHotUpdateFiles();

for (String filename : files) {
    Log.d("HotUpdate", "热更新文件: " + filename);

    // 定位实际文件
    File hotFile = hu.getHotUpdateFile(filename, HotUpdateManager.TYPE_FILE);
    if (hotFile != null && hotFile.exists()) {
        Log.d("HotUpdate", "  -> " + hotFile.getAbsolutePath()
                + " (" + hotFile.length() + " bytes)");
    }
}
```

### 8.2 读取所有热更新属性

```java
ArrayList<String> props = hu.getHotUpdateProps();
for (String propName : props) {
    Log.d("HotUpdate", "热更新属性: " + propName);
}
```

### 8.3 查找特定文件

```java
File f = hu.getHotUpdateFile("lib/libfoo.so", HotUpdateManager.TYPE_FILE);
if (f != null && f.exists()) {
    // 使用 f 进行后续操作，如加载 so、校验签名等
    System.load(f.getAbsolutePath());
} else {
    Log.w("HotUpdate", "libfoo.so 未在热更新列表中或文件未就绪");
}
```

---

## 九、测试建议

```java
// === Android 设备/模拟器上验证命令 ===

// 查看文件内容
adb shell cat /data/hotupdate/filelist
adb shell cat /data/hotupdate/proplist

// 确认 tab 分隔符（^I 表示 tab）
adb shell cat -A /data/hotupdate/filelist

// 确认 SELinux 标签
adb shell ls -Z /data/hotupdate/

// 查看 log 中 HotUpdateManager 的输出
adb logcat -s HotUpdateManager:V
```

单元测试关注点：
1. 正常 TSV → 正确解析
2. filelist 不存在 → 返回空列表
3. 行中有多个 tab → 跳过
4. 行中无 tab → 跳过
5. value 为空 → 跳过
6. 包含 `\0`/`\t`/`\n`/`\r` → 跳过
7. 重复 key → 只保留第一个
8. `findKeyInList` 精确匹配 vs 部分匹配
9. pathSuffix 为 null → 返回 null
10. pathSuffix 含 `..` → 返回 null
11. type 非法值 → 返回 null
12. 并发读取（多线程同时调用）→ 无异常无死锁

---

## 十、方案总结

| 层次 | 决策 |
|------|------|
| **API 入口** | `android.app.HotUpdateManager`，DCL 单例 |
| **文件格式** | 两列 TSV，`key\tvalue`，`#` 注释，UTF-8，与 C++ 方案一致 |
| **核心技术** | `BufferedReader` + 逐行解析，无 JNI 依赖 |
| **并发安全** | 无锁设计——利用 C++ Writer 的 rename 原子性保证内容完整性 |
| **错误处理** | 内部全捕获，绝不抛异常，返回空列表 / null |
| **安全防护** | 行数 / 长度 / key 长度 / 禁止字符 / 路径穿越 多重防御 |
| **性能** | 文件 < 1MB，无缓存（每次读最新），O(n) 线性扫描 |
| **集成方式** | 单文件放入 `frameworks/base/core/java/android/app/`，`make update-api` |
