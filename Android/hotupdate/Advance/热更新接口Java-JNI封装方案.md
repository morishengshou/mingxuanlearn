# Android 12 热更新读接口 —— Java 经 JNI 封装 C++ 方案

> 目标：**只维护一份 C++ 逻辑**，Java SDK 通过 JNI 调用 native 的
> `gethotupdatefiles / gethotupdateprops / GetHotUpdateFile`，从而保证 Java 与 C++
> 两端「取到的内容、解析规则、校验规则、去重语义、上限约束」**完全一致**，且只需在 C++ 侧演进。
>
> 本方案与《热更新接口Java SDK方案》（纯 Java 直读）是**互斥的两条技术路线**，文末给出选型对照。

---

## 一、结论先行

| 问题 | 结论 |
|---|---|
| Java SDK 调用 C++ `.so` 是否可行？ | **可行**。这是 Android framework 的标准做法（`System.loadLibrary` + JNI）。 |
| 用 JNI 写 Android SDK 接口是否可行？ | **可行且成熟**，但要处理好「.so 分发 / ABI / native 崩溃防御 / 局部引用管理」四件事。 |
| 相比纯 Java 直读，优点是什么？ | **单一事实源**：逻辑只在 C++，两端行为零漂移；复用已加固的 native 代码（`O_NOFOLLOW`、上限、去重）。 |
| 效率上更快吗？ | 对本场景（<100 条、<1MB）**基本持平**。JNI 有跨界与字符串编解码开销，纯 Java IO 也很快；速度不是选它的理由，**一致性与可维护性才是**。 |

---

## 二、为什么选 JNI 桥接（优点）

1. **单一事实源，杜绝逻辑漂移**
   TSV 解析、字段校验、`key` 去重、大小/记录数上限、`para` 路径拼接、精确匹配——全部只存在于 C++。
   Java 侧不再复制任何一行解析逻辑，也就不存在「改了 C++ 忘了改 Java」导致两端结果不一致的风险。

2. **复用已加固的 native 实现**
   native reader 已具备 `O_NOFOLLOW`、免锁读取、畸形行跳过、1MB/4096 上限等防御。JNI 直接复用，
   无需在 Java 再实现一遍并承担再次犯错的可能。

3. **行为天然对齐 native 调用方**
   系统内 C++ 调用方与 App 端 Java 调用方走的是**同一个函数**，返回结果逐字节一致，便于对拍与联调。

4. **维护面收敛**
   新增字段校验、调整上限、修复解析 bug，只改 C++ 一处、重编一个 `.so`，Java 层无需改动、无需重新验证。

### 代价（需正视）

| 代价 | 说明与缓解 |
|---|---|
| native 崩溃会拖垮 App 进程 | JNI 桥接层必须极度防御；所幸底层 reader「永不抛异常、只返回空/null」，桥接层只做转换，风险可控 |
| `.so` 分发与 ABI | 系统库随镜像分发（无 ABI 问题）；若打 AAR 则需按 ABI 打包多份 `.so` |
| 三方 App 加载系统 `.so` 受限 | 需把库登记为 public library（见第七章），否则只有系统 App 能 `loadLibrary` |
| JNI 编写门槛 | 局部引用管理、异常检查、修改版 UTF-8 等细节需谨慎（本文均已处理） |

---

## 三、总体架构与分层

```
┌─────────────────────────────────────────────┐
│  App (Java)                                   │
│   HotUpdateManager.getHotUpdateFiles() ...    │  ← 薄壳：只做加载/空安全/类型转换
└───────────────┬───────────────────────────────┘
                │ System.loadLibrary("hotupdate_jni")
                │ private static native ...
┌───────────────▼───────────────────────────────┐
│  libhotupdate_jni.so   (JNI 桥接层，纯转换)      │  ← 只做 jstring<->std::string、vector<->String[]
│   Java_..._nativeGetHotUpdateFiles(...)        │
└───────────────┬───────────────────────────────┘
                │ 调用 C++ 读接口
┌───────────────▼───────────────────────────────┐
│  libhotupdate_client.so  (native reader，唯一逻辑) │  ← 解析/校验/去重/上限/para 拼接
│   gethotupdatefiles / gethotupdateprops /       │
│   GetHotUpdateFile                              │
└───────────────┬───────────────────────────────┘
                │ 免锁读取（依赖 writer 的 rename 原子替换）
        /data/hotupdate/{filelist,proplist,para/}
```

**分层原则**：JNI 层 **只做类型转换，不含任何业务逻辑**。这样 reader 仍可被系统内 C++ 直接复用，
JNI 层则薄到「一眼看穿、几乎不会出错」。

---

## 四、接口签名映射（与 C++ 保持一致）

| C++ 读接口 | JNI native 方法 | Java 公开 API |
|---|---|---|
| `std::vector<std::string> gethotupdatefiles()` | `nativeGetHotUpdateFiles() : String[]` | `ArrayList<String> getHotUpdateFiles()` |
| `std::vector<std::string> gethotupdateprops()` | `nativeGetHotUpdateProps() : String[]` | `ArrayList<String> getHotUpdateProps()` |
| `char* GetHotUpdateFile(const char* pathSuffix, int type, char* buf, int bufLen)` | `nativeGetHotUpdateFile(String pathSuffix, int type) : String` | `File getHotUpdateFile(String pathSuffix, int type)` |

### 关于 `GetHotUpdateFile` 的参数

- **`pathSuffix`、`type` 与 C++ 完全一致**，直接透传。
- **`buf` / `bufLen` 不上浮到 Java**：它们是 C ABI 的「调用方提供输出缓冲区」机制。JNI 桥接层在
  native 栈上开 `char buf[PATH_MAX]` 作为缓冲区调用 C++，再把结果转成 `jstring` 返回。Java 端由
  `File` 对象承载路径、GC 管理内存，天然规避缓冲区溢出，无需暴露 `buf/bufLen`。
- 返回类型：C++ 返回 `char*`（成功为 `buf`，失败 `NULL`）→ JNI 转为 `String`（失败 `null`）→ Java 包成 `File`（失败 `null`）。

---

## 五、Java 层实现（`HotUpdateManager.java`）

```java
/*
 * Copyright (C) 2024 The Vendor Project
 * SPDX-License-Identifier: Apache-2.0
 */

package com.vendor.hotupdate;

import android.util.Log;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;

/**
 * 热更新记录读取 SDK（App 侧，JNI 版）。
 *
 * <p>本类是一层薄壳：所有解析 / 校验 / 去重 / 上限 / 路径拼接逻辑都在 native
 * {@code libhotupdate_client.so} 中，本类仅负责：加载 JNI 库、空安全、native 返回值到
 * Java 类型的转换。因此其行为与系统内 C++ 调用方逐字节一致。
 *
 * <p><b>永不抛异常</b>：JNI 库加载失败或 native 返回空，一律降级为空列表 / null。
 *
 * <p><b>前置条件</b>：调用方 SELinux 域需在 {@code hotupdate_reader_domain} 白名单内，且能
 * dlopen {@code libhotupdate_jni.so}（系统 App 直接可用；三方 App 需库登记为 public library）。
 *
 * <p>纯静态无状态，线程安全。
 */
public final class HotUpdateManager {

    private static final String TAG = "HotUpdate";

    /** 在 filelist 中查找（与 native type 一致）。 */
    public static final int TYPE_FILE = 0;
    /** 在 proplist 中查找（与 native type 一致）。 */
    public static final int TYPE_PROP = 1;

    /** JNI 库是否可用；加载失败时各接口安全降级。 */
    private static final boolean NATIVE_AVAILABLE = loadNativeLib();

    private HotUpdateManager() {
    }

    private static boolean loadNativeLib() {
        try {
            System.loadLibrary("hotupdate_jni");
            return true;
        } catch (UnsatisfiedLinkError e) {
            Log.e(TAG, "load libhotupdate_jni.so failed; APIs will return empty", e);
            return false;
        }
    }

    /**
     * 读取所有热更新文件名。文件不存在 / 无记录 / 库不可用时返回空列表，永不返回 null。
     */
    public static ArrayList<String> getHotUpdateFiles() {
        if (!NATIVE_AVAILABLE) {
            return new ArrayList<>();
        }
        String[] arr = nativeGetHotUpdateFiles();
        return arr == null ? new ArrayList<>() : new ArrayList<>(Arrays.asList(arr));
    }

    /**
     * 读取所有热更新属性名。文件不存在 / 无记录 / 库不可用时返回空列表，永不返回 null。
     */
    public static ArrayList<String> getHotUpdateProps() {
        if (!NATIVE_AVAILABLE) {
            return new ArrayList<>();
        }
        String[] arr = nativeGetHotUpdateProps();
        return arr == null ? new ArrayList<>() : new ArrayList<>(Arrays.asList(arr));
    }

    /**
     * 在 filelist / proplist 中精确查找 {@code pathSuffix}，命中后返回 para 目录下的实体文件。
     *
     * <p>参数与 native {@code GetHotUpdateFile} 对齐（{@code buf/bufLen} 由 JNI 层内部处理）。
     * 返回的 {@link File} 不保证磁盘上一定存在，调用方应自行 {@link File#exists()} / {@link File#canRead()}。
     *
     * @param pathSuffix TYPE_FILE 时为相对路径 filename，TYPE_PROP 时为 propname
     * @param type       {@link #TYPE_FILE} 或 {@link #TYPE_PROP}
     * @return 命中返回 {@link File}；参数非法 / 未命中 / 库不可用返回 null
     */
    public static File getHotUpdateFile(String pathSuffix, int type) {
        if (!NATIVE_AVAILABLE || pathSuffix == null || pathSuffix.isEmpty()) {
            return null;
        }
        String path = nativeGetHotUpdateFile(pathSuffix, type);
        return path == null ? null : new File(path);
    }

    /** 便捷重载，默认在 filelist 中查找。 */
    public static File getHotUpdateFile(String pathSuffix) {
        return getHotUpdateFile(pathSuffix, TYPE_FILE);
    }

    // === native 方法（经 JNI_OnLoad 中 RegisterNatives 绑定）===
    private static native String[] nativeGetHotUpdateFiles();
    private static native String[] nativeGetHotUpdateProps();
    private static native String nativeGetHotUpdateFile(String pathSuffix, int type);
}
```

---

## 六、JNI 桥接层实现（`hotupdate_jni.cpp`）

```cpp
/*
 * Copyright (C) 2024 The Vendor Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * JNI 桥接层：只做类型转换，不含任何业务逻辑。
 * 所有解析 / 校验 / 去重 / 上限 / para 拼接均在 libhotupdate_client 中。
 */

#define LOG_TAG "hotupdate_jni"

#include <jni.h>
#include <limits.h>          // PATH_MAX

#include <string>
#include <vector>

#include <log/log.h>

#include "hotupdate/hotupdate_client.h"   // native reader 公开头

namespace {

// vector<string> -> Java String[]；任何分配失败返回 nullptr（Java 侧按空处理）
jobjectArray VectorToStringArray(JNIEnv* env,
                                 const std::vector<std::string>& items) {
    jclass string_class = env->FindClass("java/lang/String");
    if (string_class == nullptr) {
        return nullptr;  // 有 pending 异常
    }
    jobjectArray array =
        env->NewObjectArray(static_cast<jsize>(items.size()), string_class, nullptr);
    env->DeleteLocalRef(string_class);
    if (array == nullptr) {
        return nullptr;  // OOM，pending 异常
    }
    jsize index = 0;
    for (const std::string& item : items) {
        jstring str = env->NewStringUTF(item.c_str());
        if (str == nullptr) {
            return nullptr;  // OOM
        }
        env->SetObjectArrayElement(array, index++, str);
        // 及时释放局部引用，避免记录数较多时局部引用表溢出（默认容量有限）
        env->DeleteLocalRef(str);
    }
    return array;
}

jobjectArray nativeGetHotUpdateFiles(JNIEnv* env, jclass /*clazz*/) {
    return VectorToStringArray(env, android::hotupdate::gethotupdatefiles());
}

jobjectArray nativeGetHotUpdateProps(JNIEnv* env, jclass /*clazz*/) {
    return VectorToStringArray(env, android::hotupdate::gethotupdateprops());
}

jstring nativeGetHotUpdateFile(JNIEnv* env, jclass /*clazz*/,
                               jstring j_suffix, jint type) {
    if (j_suffix == nullptr) {
        return nullptr;
    }
    const char* suffix = env->GetStringUTFChars(j_suffix, nullptr);
    if (suffix == nullptr) {
        return nullptr;  // OOM
    }

    // buf/bufLen 在此消化：栈上缓冲区，交给 C++ 填充绝对路径
    char buf[PATH_MAX];
    char* result = android::hotupdate::GetHotUpdateFile(
        suffix, static_cast<int>(type), buf, static_cast<int>(sizeof(buf)));

    env->ReleaseStringUTFChars(j_suffix, suffix);

    return result == nullptr ? nullptr : env->NewStringUTF(result);
}

const JNINativeMethod kMethods[] = {
    {"nativeGetHotUpdateFiles", "()[Ljava/lang/String;",
     reinterpret_cast<void*>(nativeGetHotUpdateFiles)},
    {"nativeGetHotUpdateProps", "()[Ljava/lang/String;",
     reinterpret_cast<void*>(nativeGetHotUpdateProps)},
    {"nativeGetHotUpdateFile", "(Ljava/lang/String;I)Ljava/lang/String;",
     reinterpret_cast<void*>(nativeGetHotUpdateFile)},
};

const char* kClassName = "com/vendor/hotupdate/HotUpdateManager";

}  // namespace

// 用 RegisterNatives 显式绑定：无需导出 Java_* 符号、查找更快、可用匿名命名空间收敛符号
extern "C" JNIEXPORT jint JNI_OnLoad(JavaVM* vm, void* /*reserved*/) {
    JNIEnv* env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) {
        ALOGE("GetEnv failed");
        return JNI_ERR;
    }
    jclass clazz = env->FindClass(kClassName);
    if (clazz == nullptr) {
        ALOGE("FindClass %s failed", kClassName);
        return JNI_ERR;
    }
    jint rc = env->RegisterNatives(
        clazz, kMethods, sizeof(kMethods) / sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    if (rc != JNI_OK) {
        ALOGE("RegisterNatives failed: %d", rc);
        return JNI_ERR;
    }
    return JNI_VERSION_1_6;
}
```

### JNI 关键点说明

| 点 | 处理 |
|---|---|
| **符号绑定** | 用 `JNI_OnLoad` + `RegisterNatives`，而非依赖 `Java_pkg_Class_method` 命名导出。查找更快、可把桥接函数放匿名命名空间收敛符号、重构 Java 包名时不牵连符号名 |
| **局部引用管理** | 循环内 `NewStringUTF` 后立即 `DeleteLocalRef`，避免记录多时局部引用表溢出 |
| **异常/OOM 安全** | 各分配点检查 `nullptr` 并直接返回，让 pending 异常自然带回 Java |
| **崩溃防御** | 底层 reader 保证「不抛异常、只返回空/null」，桥接层只做转换，无解引用越界风险 |
| **`buf/bufLen`** | 在 `nativeGetHotUpdateFile` 内以 `char buf[PATH_MAX]` 消化，不暴露给 Java |
| **UTF-8 注意** | `NewStringUTF`/`GetStringUTFChars` 用的是「修改版 UTF-8」。路径为 ASCII 时与标准 UTF-8 一致；若 filename 可能含**增补平面字符（4 字节 UTF-8）**，见下方「兼容性注意」 |

> **兼容性注意（增补平面字符）**：`NewStringUTF` 对 U+10000 以上字符的编码与标准 UTF-8 不同，
> 可能得到乱码。本方案字段校验已禁止控制字符，但未禁止增补平面字符。若业务确有此类文件名，
> 应改为在 C++ 侧返回 `std::string` 的原始字节、用 `env->NewByteArray` 传回，Java 端
> `new String(bytes, StandardCharsets.UTF_8)` 解码。纯 ASCII / BMP 场景无需处理。

---

## 七、构建与分发

### 7.1 Android.bp（系统库形态，随镜像分发）

```python
cc_library_shared {
    name: "libhotupdate_jni",
    srcs: ["hotupdate_jni.cpp"],
    header_libs: ["jni_headers"],          // 提供 jni.h
    shared_libs: [
        "liblog",
        "libhotupdate_client",             // 复用 native reader，不重复逻辑
    ],
    cflags: ["-Wall", "-Werror"],
    system_ext_specific: true,             // 与 client 库同分区
    // 若需三方 App 可 dlopen，配合 public.libraries（见 7.3）
}
```

> 说明：JNI 库依赖 **共享库** `libhotupdate_client`（reader），而非把 reader 源码再编一份，
> 确保「reader 逻辑全系统唯一一份」。

### 7.2 两种分发形态

| 形态 | 适用 | 特点 |
|---|---|---|
| **系统库**（`.so` 装入 `/system_ext/lib*`） | 系统/预置 App、厂商 App | 单副本、随 OTA 升级；三方 App 需 public library 登记 |
| **AAR 内置 `jniLibs`** | 需要分发给三方 App | 每 ABI 打一份 `.so` 随 APK；App 私有进程加载；但 native 逻辑被复制进 App，**部分削弱「单一副本」优势**（逻辑源仍唯一，副本随 SDK 版本走） |

### 7.3 三方 App 加载系统 `.so`（public library）

系统库默认对三方 App 不可见。如需放开，登记为 public library：

```
# /system_ext/etc/public.libraries-vendor.txt （或 vendor 对应位置）
libhotupdate_jni.so
```

并在 App 的 `AndroidManifest.xml` 用 `<uses-native-library android:name="libhotupdate_jni.so"/>`（Android 12 要求非 NDK 库需声明）。系统/预置 App 无此限制。

> 注意：即便 `.so` 能加载，**能否读到文件仍取决于 SELinux 读者白名单**（第八章）。两道门缺一不可。

---

## 八、DAC / SELinux 权限：前置依赖，与 JNI/纯 C++ 的异同

### 8.1 前置依赖（与纯 Java 版一致）

```te
typeattribute platform_app hotupdate_reader_domain;
typeattribute priv_app     hotupdate_reader_domain;
# 三方 untrusted_app 受平台 neverallow 限制，无法文件级直接放开，
# 如确需暴露给三方应用，走 system_server 的 Binder 接口转发。

allow hotupdate_reader_domain hotupdate_dir:dir { search getattr };
allow hotupdate_reader_domain hotupdate_public_file:file { open read getattr };
```

无权限时：native `open()` 被 SELinux 拒绝 → reader 返回空 vector → JNI 返回空数组 → Java 返回空列表/null，
**App 不崩溃**。排障：`adb shell dmesg | grep avc`。

### 8.2 JNI 调用与纯 C++ 的权限差异

一句话核心：**Android 的权限按「进程」判定，不看语言、也不看是否走 JNI**。JNI 的 `.so` 被 App 加载后，
运行在 **App 自己的进程**里，继承 App 的 UID（DAC）和 SELinux 域（domain）——它**不会获得任何独立身份**。

#### (a) DAC 层：两者完全一样

DAC 只认**进程的 UID/GID**，与语言无关。本方案权限为：

```
/data/hotupdate/          0711 root root   → o+x，任意 UID 可穿越到已知路径
/data/hotupdate/filelist  0444 root root   → o+r，任意 UID 可读
```

无论是 JNI 在 App 进程里 `open()`，还是纯 C++ 进程 `open()`，DAC 判定逻辑与结果都相同（读都放行）。
**这一层无需区分配置。**

#### (b) SELinux 层：文件侧相同，主体侧不同

SELinux 是 `subject(域) × object(文件标签) × 权限` 的三元判定：

- **object 侧（文件）完全共享、一字不差**：`hotupdate_public_file` 类型、`file_contexts` 打标签、
  `neverallow` 硬锁——JNI 与纯 C++ 用同一份。
- **subject 侧（域）取决于「谁在跑代码」，两者不同**：

  | | 运行主体 | 需要授权的域 |
  |---|---|---|
  | **JNI 调用** | 代码跑在 **App 进程**内 | App 的域：`platform_app` / `priv_app` / `untrusted_app` / `system_server` … |
  | **纯 C++** | 代码跑在**那个 C++ 进程**里（通常是独立 native 服务/守护进程/命令） | 该进程自己的域：如 `hotupdate_service`、某 daemon 域、或 `shell` |

  因此 `allow ... hotupdate_public_file:file r_file_perms;` 的**主体必须写成实际运行进程的域**——
  JNI 写 App 域，纯 C++ 写它自己的域。**这条不能照抄。**

#### (c) 两条路线的配置对比

| 配置项 | JNI（App 加载 .so） | 纯 C++（独立 native 进程） |
|---|---|---|
| 文件类型 / file_contexts / neverallow | ✅ 相同，共享 | ✅ 相同，共享 |
| DAC（0444 / 0711） | ✅ 相同 | ✅ 相同 |
| SELinux 读授权**主体** | App 域（见 8.1 白名单） | 该 native 进程的域 |
| 专属步骤：域从哪来 | App 域是系统现成的，无需定义 | 需为该进程**定义 domain**（`type xxx, domain;` + `exec_type` + `init_daemon_domain()` 等） |
| 专属步骤：代码加载 | 需让 App 能 dlopen `.so`——系统库要登记 **public library** + `<uses-native-library>` | 无此问题（自身即可执行文件/自带依赖） |

**结论**：配置路线**大部分共享（文件侧 + DAC），但不完全相同**。差异有两处：
① **SELinux 读授权的主体**必须对准真正 `open()` 文件的那个域；
② **各自的专属步骤不同**——JNI 多一步「库可见性（public library）」，纯 C++ 多一步「为进程定义 SELinux 域」。

#### (d) 三个必须注意的陷阱

1. **`isolated_app` / isolatedProcess**：若 App 用隔离进程加载 JNI，域是 `isolated_app`，被平台
   `neverallow` 死锁，**无论如何授权都读不到**；纯 C++ 跑在受限域同理。
2. **`untrusted_app`（三方普通应用）**：被平台 `neverallow` 禁止打开绝大多数 `data_file_type`，
   **JNI 也绕不过**——这是进程域的限制，不是 JNI 能解决的。要给三方 App 用，只能走 `system_server`
   Binder 转发（JNI 与纯 C++ 结论一致）。
3. **JNI 加载 `.so` 本身的 SELinux**：App 执行/映射系统库通常已被平台规则放行（public 库的
   `execute/map`），一般无需额外加；真正要新增的自始至终只有那一条「数据文件读权限」。

---

## 九、调用示例

```java
import com.vendor.hotupdate.HotUpdateManager;
import java.io.File;
import java.util.ArrayList;

ArrayList<String> files = HotUpdateManager.getHotUpdateFiles();   // 与 C++ 结果逐字节一致
ArrayList<String> props = HotUpdateManager.getHotUpdateProps();

File f = HotUpdateManager.getHotUpdateFile("lib/libfoo.so", HotUpdateManager.TYPE_FILE);
if (f != null && f.canRead()) {
    loadLibrary(f);            // /data/hotupdate/para/lib/libfoo.so
} else {
    loadBuiltin();             // 未命中 / 无权限 / 库不可用 → 回退
}
```

---

## 十、纯 Java 直读 vs JNI 桥接 —— 选型对照

| 维度 | 纯 Java 直读（前一方案） | JNI 桥接 C++（本方案） |
|---|---|---|
| 逻辑事实源 | Java 与 C++ **各一份**（需人工保持同步） | **仅 C++ 一份**，Java 零逻辑 |
| 行为一致性 | 靠纪律与对拍保证，存在漂移风险 | **天然一致**（同一函数） |
| 维护成本 | 改规则需改两处、验两处 | 改规则只改 C++、重编一个 `.so` |
| 依赖 | 无 native 依赖，纯 Java | 依赖 `libhotupdate_jni.so` + `libhotupdate_client.so` |
| 崩溃域 | Java 异常，进程安全 | native 崩溃会杀进程（桥接层已防御到位则风险低） |
| 分发 | 一个 `.jar/.class`，无 ABI 问题 | 需 `.so`；三方 App 需 public library 登记 |
| 三方 App 可用性 | 只要有 SELinux 读权限即可 | 需同时满足 public library + SELinux 读权限 |
| 效率（本场景） | 快 | 基本持平（多一次 JNI 跨界 + 字符串编解码） |
| 适用 | 想零 native 依赖、调用方以系统/预置为主 | **强一致性 + 单点维护**优先；已有 native reader 库 |

**推荐**：既然系统内已经有 `libhotupdate_client`（native reader），且你的诉求明确是
「仅维护 C++、两端一致」，**本 JNI 方案更契合**；纯 Java 版可作为「native 库不可用时的可选降级实现」保留。

### 可选增强：native 不可用时降级为纯 Java 直读

`NATIVE_AVAILABLE == false` 时，可在 `HotUpdateManager` 内回退到纯 Java 版的直读逻辑，
兼得「一致性」与「鲁棒性」。代价是又引入一份 Java 逻辑，是否值得取决于对可用性的要求，按需选用。

---

## 十一、健壮性清单

| 措施 | 实现 |
|---|---|
| 库加载失败降级 | `System.loadLibrary` 包 try/catch，失败置 `NATIVE_AVAILABLE=false`，接口返回空/null |
| 空安全 | 列表方法永不返回 null；`getHotUpdateFile` 明确 null 语义 |
| 异常隔离 | 底层 reader 不抛异常；JNI 层各分配点检查并回传 pending 异常 |
| 局部引用安全 | 循环内即时 `DeleteLocalRef`，防引用表溢出 |
| 缓冲区安全 | `buf[PATH_MAX]` 在 JNI 内，C++ 内部严格 `bufLen` 边界检查 |
| 逻辑复用 | 解析/校验/去重/上限/para 拼接全部复用 native，Java 零复制 |
| 线程安全 | 无状态静态方法；native reader 免锁读取 |

---

## 十二、落地前替换 / 确认项

1. **包名/库名**：`com.vendor.hotupdate`、`libhotupdate_jni` 均为占位，替换为实际值；`RegisterNatives`
   的 `kClassName` 必须与 Java 包名严格一致。
2. **reader 头文件路径**：`#include "hotupdate/hotupdate_client.h"` 按综合方案实际路径调整。
3. **分发形态**：系统库 or AAR；若面向三方 App，配好 public library + `<uses-native-library>`。
4. **`TYPE_PROP` 语义**：仍继承综合方案 `GetHotUpdateFile(type=1)` 的未决问题——由 C++ 侧统一定义，
   Java/JNI 无需改动即自动跟随（这正是单一事实源的好处）。
5. **增补平面字符**：若 filename 可能含 4 字节 UTF-8 字符，改用 `byte[]` 传递方案（见第六章注意）。

---

## 十三、一句话总结

> 用一个「只做类型转换」的薄桥接层 `libhotupdate_jni.so` 把 native reader 暴露给 Java，
> Java 侧 `HotUpdateManager` 仅负责加载、空安全与 `String[]→ArrayList` / `String→File` 转换。
> 由此**解析、校验、去重、上限、`para` 拼接全部只存在于 C++**，Java 与 C++ 两端行为逐字节一致，
> 演进只需维护 C++ 一处——以可接受的 JNI 复杂度与 `.so` 分发成本，换取强一致性与单点维护。
