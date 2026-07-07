# Android 12 热更新读接口 —— Java SDK 实现方案

> 本方案为《热更新接口综合方案》中三个 native 读接口的 **Java 等价实现**，封装进厂商自定义
> SDK，供普通 App / 系统服务调用。核心思路：既然文件是「人类可读明文 TSV」，Java 侧就可以
> **直接读取同一份文件**，无需 JNI 桥接、无需 Binder 服务，只要调用方的 SELinux 域有读权限即可。

---

## 一、接口对应关系

| native 读接口 | Java SDK 接口 | 说明 |
|---|---|---|
| `std::vector<std::string> gethotupdatefiles()` | `public static ArrayList<String> getHotUpdateFiles()` | 返回 filelist 第一列（文件名） |
| `std::vector<std::string> gethotupdateprops()` | `public static ArrayList<String> getHotUpdateProps()` | 返回 proplist 第一列（属性名） |
| `char* GetHotUpdateFile(const char* pathSuffix, int type, char* buf, int bufLen)` | `public static File getHotUpdateFile(String pathSuffix, int type)` | 查找并返回 para 目录下的实体文件 |

### 关于 `getHotUpdateFile` 的签名

需求中给出的是无参 `getHotUpdateFile()`，但 native 版必须有 `pathSuffix` + `type` 才能定位记录，
无参无法工作。因此本方案实现为：

```java
public static File getHotUpdateFile(String pathSuffix, int type);   // 主方法
public static File getHotUpdateFile(String pathSuffix);             // 便捷重载，默认 TYPE_FILE
```

- native 的 C 风格 `char* buf / int bufLen` 缓冲区参数在 Java 中不需要——直接返回 `File` 对象，
  由 GC 管理内存，天然规避缓冲区溢出。

---

## 二、为什么可以在 Java 侧直接读文件？

这是 TSV 明文格式相较 SQLite / 二进制格式的又一红利：

1. **无需 JNI**：不必把 native 读库通过 JNI 暴露给 App，减少一层 `.so` 依赖与符号维护。
2. **无需 Binder 服务**：不必为「读一份小列表」专门起一个系统服务 + AIDL。
3. **格式单一可信**：native writer 是唯一写者且严格校验过内容，Java reader 只做「宽容解析 + 去重」，
   与 native reader 逻辑一一对应，两端行为一致、易于对拍测试。

唯一的前置条件是 **SELinux 读权限**（见第七章）。

---

## 三、整体设计原则（与 native reader 完全对齐）

| 原则 | 实现方式 |
|---|---|
| **免锁读取** | 写端「写临时文件 + rename 原子替换」，读端任意时刻打开的都是完整旧文件或完整新文件，绝不会读到写了一半的行，因此读取无需任何文件锁 |
| **不缓存** | 文件可能被 init 随时更新，每次调用读最新内容，避免脏数据 / 内存与磁盘不一致 |
| **永不抛异常** | 文件缺失、格式损坏、IO 错误、超限一律降级为「返回空列表 / null」，绝不把异常抛给 App |
| **按 key 去重** | 第一列（filename / propname）为唯一主键，重复 key 保留首次出现（`LinkedHashMap.putIfAbsent`） |
| **输入严格校验** | `getHotUpdateFile` 入参按类型分别用 filename / propname 规则校验，并对拼接结果做「不逃逸 para 目录」兜底 |
| **安全上限** | 文件 1MB、记录 4096、单行 8192、filename 255B、propname 128B，全部与 native 常量一致 |
| **线程安全** | 纯静态无状态工具类 |

---

## 四、类结构

```
com.vendor.hotupdate
└── HotUpdateManager                (final，私有构造，工具类)
    ├── 公开常量
    │   ├── TYPE_FILE = 0           查 filelist
    │   └── TYPE_PROP = 1           查 proplist
    ├── 公开接口
    │   ├── getHotUpdateFiles() : ArrayList<String>
    │   ├── getHotUpdateProps() : ArrayList<String>
    │   ├── getHotUpdateFile(String, int) : File
    │   └── getHotUpdateFile(String) : File
    └── 内部实现
        ├── readEntries(String) : LinkedHashMap<String,String>   读+解析+去重
        ├── parseTsvLine(String) : String[]                      单行两列解析
        ├── hasForbiddenChar(String) : boolean                   控制字符检查
        ├── isValidFileName(String) : boolean                    filename 校验
        ├── isValidPropName(String) : boolean                    propname 校验
        └── isUnderParaDir(File) : boolean                       路径逃逸兜底
```

---

## 五、完整实现

```java
/*
 * Copyright (C) 2024 The Vendor Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 */

package com.vendor.hotupdate;

import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;

/**
 * 热更新记录读取 SDK（App 侧）。
 *
 * <p>本类是 native 读接口 {@code gethotupdatefiles / gethotupdateprops / GetHotUpdateFile}
 * 的 Java 等价实现，供普通 App / 系统服务调用。它直接读取 init 写入的两份人类可读明文文件：
 *
 * <ul>
 *   <li>{@code /data/hotupdate/filelist} —— {@code filename<TAB>filepath}</li>
 *   <li>{@code /data/hotupdate/proplist} —— {@code propname<TAB>proppath}</li>
 * </ul>
 *
 * <p><b>设计要点（与 native reader 完全对齐）：</b>
 * <ul>
 *   <li><b>免锁读取</b>：写端采用「写临时文件 + rename 原子替换」，读端任意时刻打开的都是
 *       一个完整的旧文件或完整的新文件，绝不会读到写了一半的行，因此读取无需任何文件锁。</li>
 *   <li><b>不缓存</b>：文件可能被 init 随时更新，每次调用都读最新内容，避免脏数据。</li>
 *   <li><b>永不抛异常</b>：文件缺失、格式损坏、IO 错误、超限一律降级为「返回空列表 / null」，
 *       绝不把异常抛给调用方。文件不存在等价于「无热更新记录」（恢复出厂后即为此状态）。</li>
 *   <li><b>按 key 去重</b>：第一列（filename / propname）为唯一主键，重复 key 保留首次出现。</li>
 *   <li><b>输入校验</b>：{@link #getHotUpdateFile} 的入参按类型分别用 filename / propname 规则
 *       严格校验，并对拼接结果做「不逃逸 para 目录」的兜底检查。</li>
 * </ul>
 *
 * <p><b>前置条件</b>：调用方所在的 SELinux 域必须已被授予对 {@code hotupdate_public_file} 的读权限
 * （见 sepolicy 中 {@code hotupdate_reader_domain} 白名单）。若无权限，read 会失败，本类各方法
 * 会安全地返回空列表 / null，而不会崩溃。
 *
 * <p>本类为纯静态工具类，无状态，线程安全。
 */
public final class HotUpdateManager {

    private static final String TAG = "HotUpdate";

    // === 路径常量（必须与 native 侧、file_contexts 保持一致）===
    private static final String HOTUPDATE_DIR = "/data/hotupdate";
    private static final String FILE_LIST_PATH = HOTUPDATE_DIR + "/filelist";
    private static final String PROP_LIST_PATH = HOTUPDATE_DIR + "/proplist";
    private static final String PARA_PREFIX = HOTUPDATE_DIR + "/para/";

    // === GetHotUpdateFile 的查找类型（与 native 的 type 参数一致）===
    /** 在 filelist 中查找。 */
    public static final int TYPE_FILE = 0;
    /** 在 proplist 中查找。 */
    public static final int TYPE_PROP = 1;

    // === 安全上限（与 native 侧一致，防御异常膨胀 / OOM）===
    private static final long MAX_LIST_FILE_SIZE = 1L << 20;  // 单个列表文件 1MB
    private static final int MAX_RECORDS = 4096;              // 最大有效记录数
    private static final int MAX_LINE_LEN = 8192;             // 单行最大长度
    private static final int MAX_FILE_NAME_LEN = 255;         // filename 字节上限
    private static final int MAX_PROP_NAME_LEN = 128;         // propname 字节上限

    /** 工具类，禁止实例化。 */
    private HotUpdateManager() {
    }

    // ---------------------------------------------------------------------
    // 公开接口
    // ---------------------------------------------------------------------

    /**
     * 读取 {@code /data/hotupdate/filelist} 中所有热更新文件名（第一列）。
     *
     * @return 去重后的文件名列表（保持首次出现顺序）；文件不存在或无有效记录时返回空列表，
     *         永不返回 {@code null}。
     */
    public static ArrayList<String> getHotUpdateFiles() {
        return new ArrayList<>(readEntries(FILE_LIST_PATH).keySet());
    }

    /**
     * 读取 {@code /data/hotupdate/proplist} 中所有热更新属性名（第一列）。
     *
     * @return 去重后的属性名列表（保持首次出现顺序）；文件不存在或无有效记录时返回空列表，
     *         永不返回 {@code null}。
     */
    public static ArrayList<String> getHotUpdateProps() {
        return new ArrayList<>(readEntries(PROP_LIST_PATH).keySet());
    }

    /**
     * 在 filelist / proplist 中精确查找 {@code pathSuffix}，命中后返回其在 para 目录下的实体文件。
     *
     * <p>拼接规则：{@code /data/hotupdate/para/ + pathSuffix}。例如 filelist 中存在一行
     * {@code lib/libfoo.so\t/system/lib64/libfoo.so}，调用 {@code getHotUpdateFile("lib/libfoo.so",
     * TYPE_FILE)} 返回 {@code File("/data/hotupdate/para/lib/libfoo.so")}。
     *
     * <p><b>注意</b>：返回的 {@link File} 只保证「记录存在且路径合法」，不保证磁盘上文件一定存在、
     * 一定可读。调用方使用前应自行判断 {@link File#exists()} / {@link File#canRead()}。
     *
     * @param pathSuffix 待匹配的键：{@code TYPE_FILE} 时为相对路径 filename，
     *                   {@code TYPE_PROP} 时为 propname。
     * @param type       查找类型：{@link #TYPE_FILE} 或 {@link #TYPE_PROP}。
     * @return 命中时返回拼接后的 {@link File}；下列情况返回 {@code null}：
     *         参数为空 / 含非法字符、type 非法、未找到匹配项、路径逃逸校验失败、读取失败。
     */
    public static File getHotUpdateFile(String pathSuffix, int type) {
        if (pathSuffix == null || pathSuffix.isEmpty()) {
            Log.e(TAG, "getHotUpdateFile: null/empty pathSuffix");
            return null;
        }

        // 1. 按 type 选择目标列表 + 对应的键合法性规则
        final String listPath;
        final boolean valid;
        switch (type) {
            case TYPE_FILE:
                listPath = FILE_LIST_PATH;
                valid = isValidFileName(pathSuffix);
                break;
            case TYPE_PROP:
                listPath = PROP_LIST_PATH;
                valid = isValidPropName(pathSuffix);
                break;
            default:
                Log.e(TAG, "getHotUpdateFile: unsupported type=" + type);
                return null;
        }
        if (!valid) {
            Log.e(TAG, "getHotUpdateFile: invalid pathSuffix for type=" + type);
            return null;
        }

        // 2. 读取列表并精确匹配（键唯一，命中即确定）
        if (!readEntries(listPath).containsKey(pathSuffix)) {
            Log.w(TAG, "getHotUpdateFile: '" + pathSuffix + "' not found");
            return null;
        }

        // 3. 拼接 + 兜底防路径逃逸（纵深防御，输入校验已禁止 .. 等）
        File target = new File(PARA_PREFIX + pathSuffix);
        if (!isUnderParaDir(target)) {
            Log.e(TAG, "getHotUpdateFile: resolved path escapes para dir");
            return null;
        }
        return target;
    }

    /**
     * {@link #getHotUpdateFile(String, int)} 的便捷重载，默认在 filelist 中查找。
     */
    public static File getHotUpdateFile(String pathSuffix) {
        return getHotUpdateFile(pathSuffix, TYPE_FILE);
    }

    // ---------------------------------------------------------------------
    // 内部实现
    // ---------------------------------------------------------------------

    /**
     * 读取并解析列表文件，返回按 key 去重（保留首次出现）的有序键值映射。
     *
     * <p>任何异常（不存在 / 超限 / IO 错误 / 格式错）都退化为返回空映射或跳过坏行，绝不抛出。
     */
    private static LinkedHashMap<String, String> readEntries(String path) {
        LinkedHashMap<String, String> entries = new LinkedHashMap<>();

        File file = new File(path);
        long length = file.length();                 // 不存在返回 0
        if (length > MAX_LIST_FILE_SIZE) {
            Log.w(TAG, path + " exceeds size limit (" + length + "B), ignored");
            return entries;
        }

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (entries.size() >= MAX_RECORDS) {
                    Log.w(TAG, path + " has too many records, truncated at " + MAX_RECORDS);
                    break;
                }
                // readLine() 已剥离 \n / \r\n / \r，无需再处理行尾
                if (line.isEmpty() || line.charAt(0) == '#' || line.length() > MAX_LINE_LEN) {
                    continue;
                }
                String[] kv = parseTsvLine(line);
                if (kv == null) {
                    continue;  // 畸形行：跳过，不影响其余记录
                }
                entries.putIfAbsent(kv[0], kv[1]);  // 按 key 去重，保留首次出现
            }
        } catch (FileNotFoundException e) {
            // 文件不存在 == 无热更新记录，属正常状态
        } catch (IOException | RuntimeException e) {
            Log.w(TAG, "read " + path + " failed", e);
            return new LinkedHashMap<>();  // 读中途出错：丢弃部分结果，返回空
        }
        return entries;
    }

    /**
     * 解析一行两列 TSV。合法返回 {@code [key, value]}，注释 / 空行 / 畸形行返回 {@code null}。
     */
    private static String[] parseTsvLine(String line) {
        int tab = line.indexOf('\t');
        if (tab <= 0) {
            return null;  // 无 tab，或 tab 在行首（key 为空）
        }
        if (line.indexOf('\t', tab + 1) >= 0) {
            return null;  // 超过两列
        }
        String key = line.substring(0, tab);
        String value = line.substring(tab + 1);
        if (value.isEmpty()) {
            return null;
        }
        if (hasForbiddenChar(key) || hasForbiddenChar(value)) {
            return null;
        }
        return new String[]{key, value};
    }

    /**
     * 检查字符串是否含禁止字符：{@code \0 \t \n \r} 及所有 ASCII 控制字符（0x00~0x1F、0x7F）。
     */
    private static boolean hasForbiddenChar(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < 0x20 || c == 0x7F) {  // 覆盖 \0 \t \n \r 及全部控制字符
                return true;
            }
        }
        return false;
    }

    /**
     * filename 合法性校验（与 native {@code IsValidFileName} 对齐）：相对路径，可含 {@code /}，
     * 但不得以 {@code /} 开头 / 结尾，不含 {@code ..}、{@code //}、{@code \}、空格、{@code #} 开头。
     */
    private static boolean isValidFileName(String name) {
        int byteLen = name.getBytes(StandardCharsets.UTF_8).length;
        if (byteLen == 0 || byteLen > MAX_FILE_NAME_LEN) {
            return false;
        }
        if (hasForbiddenChar(name)) {
            return false;
        }
        if (name.indexOf(' ') >= 0 || name.indexOf('\\') >= 0) {
            return false;
        }
        if (name.charAt(0) == '#' || name.charAt(0) == '/') {
            return false;
        }
        if (name.charAt(name.length() - 1) == '/') {
            return false;
        }
        return !name.contains("..") && !name.contains("//");
    }

    /**
     * propname 合法性校验（与 native {@code IsValidPropName} 对齐）：仅允许 {@code [a-zA-Z0-9_.-]}。
     */
    private static boolean isValidPropName(String name) {
        int byteLen = name.getBytes(StandardCharsets.UTF_8).length;
        if (byteLen == 0 || byteLen > MAX_PROP_NAME_LEN) {
            return false;
        }
        for (int i = 0; i < name.length(); i++) {
            char c = name.charAt(i);
            boolean ok = (c >= 'a' && c <= 'z')
                    || (c >= 'A' && c <= 'Z')
                    || (c >= '0' && c <= '9')
                    || c == '_' || c == '.' || c == '-';
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    /**
     * 纵深防御：确认拼接结果规范化后仍位于 para 目录内，防止符号链接 / 意外逃逸。
     */
    private static boolean isUnderParaDir(File target) {
        try {
            String paraCanonical = new File(PARA_PREFIX).getCanonicalPath();
            String targetCanonical = target.getCanonicalPath();
            return targetCanonical.equals(paraCanonical)
                    || targetCanonical.startsWith(paraCanonical + File.separator);
        } catch (IOException e) {
            Log.w(TAG, "canonicalize failed for " + target, e);
            return false;
        }
    }
}
```

---

## 六、调用示例

```java
import com.vendor.hotupdate.HotUpdateManager;

import java.io.File;
import java.util.ArrayList;

// 1) 拉取全部热更新文件名
ArrayList<String> files = HotUpdateManager.getHotUpdateFiles();
for (String name : files) {
    Log.d("App", "hot-updated file: " + name);   // 如 "lib/libfoo.so"
}

// 2) 拉取全部热更新属性名
ArrayList<String> props = HotUpdateManager.getHotUpdateProps();

// 3) 定位某个热更新文件的实体路径并读取
File f = HotUpdateManager.getHotUpdateFile("lib/libfoo.so", HotUpdateManager.TYPE_FILE);
if (f != null && f.canRead()) {
    // 得到 /data/hotupdate/para/lib/libfoo.so，可进一步加载
    loadLibrary(f);
} else {
    // 记录不存在 / 无权限 / 文件缺失 —— 回退到系统内置版本
    loadBuiltin();
}
```

> **契约提醒**：两个列表方法永不返回 `null`（最坏返回空列表）；`getHotUpdateFile` 命中返回 `File`
> （不保证磁盘存在），未命中 / 非法 / 无权限返回 `null`。调用方只需判空 + `canRead()` 即可。

---

## 七、SELinux 前置依赖

Java SDK 直接读文件，**能否读到完全取决于调用方 App 的 SELinux 域是否在读者白名单内**。这与
《热更新接口综合方案》第七章的 sepolicy 配套：

```te
# 把需要读取的 App 域加入白名单属性
typeattribute platform_app hotupdate_reader_domain;
typeattribute priv_app     hotupdate_reader_domain;
# 三方普通应用（untrusted_app）受平台 neverallow 限制，无法直接文件级放开，
# 如确需暴露，请通过 system_server 的 Binder 接口转发。

allow hotupdate_reader_domain hotupdate_dir:dir { search getattr };
allow hotupdate_reader_domain hotupdate_public_file:file { open read getattr };
```

- **无权限时的表现**：`open()` 触发 SELinux 拒绝 → Java 侧捕获 `FileNotFoundException`/`IOException`
  → 返回空列表 / null，**App 不会崩溃**，但也读不到数据。
- **排障**：`adb shell dmesg | grep avc` 查看是否因缺少 `hotupdate_public_file` 读权限被拒。

---

## 八、健壮性清单

| 措施 | 实现 |
|---|---|
| 空安全 | 列表方法永不返回 null；`getHotUpdateFile` 明确返回 null 语义 |
| 异常隔离 | 所有 IO / 运行时异常在内部捕获并降级，绝不抛给 App |
| 文件缺失容错 | `FileNotFoundException` 视为「无记录」，返回空——契合恢复出厂后的初始态 |
| 畸形数据容错 | 坏行 / 多列 / 空字段 / 含控制字符的行直接跳过 |
| 防 OOM | 文件 1MB、记录 4096、单行 8192 三重上限 |
| 输入校验 | `getHotUpdateFile` 按 type 分别用 filename / propname 规则校验入参 |
| 防路径逃逸 | 校验禁止 `..`/`//`/`\`/前导 `/`，并用 `getCanonicalPath()` 兜底确认落在 para 目录内 |
| 编码确定性 | 固定 `UTF-8` 读取，避免设备默认编码差异 |
| 免锁一致性 | 依赖写端 rename 原子替换，读端无锁即可读到完整快照 |
| 线程安全 | 无状态静态方法 |

---

## 九、与 native reader 的一致性对照

| 行为 | native (`hotupdate_reader.cpp`) | Java (`HotUpdateManager`) |
|---|---|---|
| 路径常量 | `/data/hotupdate/{filelist,proplist}`、`para/` 前缀 | 完全一致 |
| 去重 | `std::set` 按 key，保留首次出现 | `LinkedHashMap.putIfAbsent`，保留首次出现 |
| 注释 / 空行 | 跳过 `#` 开头与空行 | 跳过 `#` 开头与空行 |
| 两列校验 | 恰好一个 `\t`，两字段非空 | 恰好一个 `\t`，value 非空（key 由 `tab>0` 保证非空） |
| 禁止字符 | `\0\t\n\r` + 控制字符 | `<0x20` + `0x7F`（等价覆盖） |
| 大小 / 数量上限 | 1MB / 4096 | 1MB / 4096 |
| `GetHotUpdateFile` 匹配 | 精确匹配 key，首个命中 | 精确匹配 key（去重后唯一） |
| 缓冲区安全 | `bufLen` 严格边界检查 | 返回 `File`，无缓冲区，天然安全 |

---

## 十、落地前需替换 / 确认项

1. **包名**：占位 `com.vendor.hotupdate`，替换为你的 SDK 实际包名。
2. **SDK 暴露方式**：若作为系统 SDK（`@SystemApi`）暴露给特定 App，需在框架 stub 中标注；
   若打成独立 AAR / jar 分发，直接引入即可。
3. **`TYPE_PROP` 语义**：与综合方案里 `GetHotUpdateFile(type=1)` 同一未决问题——
   `para/ + propname` 是否对应真实文件，取决于 para 下属性文件的组织方式。确定后 Java 侧
   同步调整，保持与 native 一致。
4. **读者白名单**：把实际调用本 SDK 的 App 域加入 `hotupdate_reader_domain`，否则读不到数据。

---

## 十一、一句话总结

> 借助 TSV 明文格式，Java SDK 以一个 **无状态、免锁、永不抛异常** 的静态工具类
> `HotUpdateManager`，直接读取与 native 同一份文件，完成 `getHotUpdateFiles /
> getHotUpdateProps / getHotUpdateFile` 三接口；健壮性（空安全、异常隔离、上限防御、
> 输入校验、路径逃逸兜底）与 native reader 逐条对齐，落地只需保证调用方 App 的
> SELinux 域在读者白名单内。
