# Android 12 热更新读接口 —— JNI 内置 `libhotupdate_client.so` 免新增制品方案

> 目标：在**不新增任何系统 `.so` 制品**的前提下，让 App 端 Java SDK 经 JNI 复用 native reader，
> 从而既保持「仅维护一份 C++ 逻辑、两端行为一致」，又规避「为一个全新 `.so` 走完整入库/专家评审流程」
> 的时间成本。
>
> 做法一句话：**把 JNI 桥接作为一个独立源文件，直接编进已经过评审的 `libhotupdate_client.so`。**
>
> 本方案是《热更新接口Java-JNI封装方案》（独立 `libhotupdate_jni.so`）的**落地变体**，
> 逻辑分层与代码完全一致，差异只在「制品如何打包」。选型见第九章。

---

## 一、背景与动机

| 约束 | 说明 |
|---|---|
| 公司管控 | 所有系统编译产物受管控，**新增一个 `.so`** 需走流程 + 专家评审 |
| 交付压力 | 时间紧，走完整新制品评审流程成本高 |
| 已有资产 | `libhotupdate_client.so`（native reader）**已存在且已过审** |
| 诉求 | 只维护 C++、Java 与 C++ 行为一致，同时尽量少走流程 |

**结论**：把 JNI 入口合并进已过审的 `libhotupdate_client.so`，只修改现有制品、不新增制品，
是满足上述全部约束的最优解。

---

## 二、为什么这样做几乎零副作用

1. **JNI 只是「头文件依赖」，不引入运行时依赖**
   `jni.h` 是纯头文件；`JNIEnv*` 由 ART 运行时传入。使用**原生 JNI**（不使用 `JNIHelp` 宏）时，
   **无需链接 `libnativehelper` 或任何新 `.so`**。因此 `libhotupdate_client.so` 的**运行时依赖一个都不增加**。

2. **对纯 C++ 调用方零影响**
   `JNI_OnLoad` 只有在 ART 通过 `System.loadLibrary` 加载该库时才会被调用。系统内 native 进程以普通
   `DT_NEEDED` / `dlopen` 链接该库时，`JNI_OnLoad` **根本不会被触发**——它只是一个用不到的导出符号，
   无任何运行时开销或风险。

3. **只新增一个导出符号**
   用 `JNI_OnLoad` + `RegisterNatives` 绑定后，三个 `nativeXxx` 桥接函数放进匿名命名空间（不导出）。
   整个库对外**仅多出 `JNI_OnLoad` 这一个标准符号**，ABI 变化面极小。

4. **业务逻辑零改动**
   解析 / 校验 / 去重 / 上限 / `para` 拼接仍全部只在 `hotupdate_reader.cpp` / `hotupdate_common.cpp`，
   一行都不动。JNI 只是「贴」上去的一层薄壳。

---

## 三、总体架构

```
┌─────────────────────────────────────────────┐
│  App (Java)                                   │
│   HotUpdateManager.getHotUpdateFiles() ...    │  ← 薄壳：加载/空安全/类型转换
│   System.loadLibrary("hotupdate_client")      │     （注意：加载的是 client 库本身）
└───────────────┬───────────────────────────────┘
                │ private static native ...
┌───────────────▼───────────────────────────────┐
│  libhotupdate_client.so   （单一制品，不新增）    │
│  ┌─────────────────────────────────────────┐   │
│  │ hotupdate_jni.cpp   （新增源文件，纯转换）  │   │  ← 仅 JNI 桥接，无业务逻辑
│  ├─────────────────────────────────────────┤   │
│  │ hotupdate_reader.cpp / hotupdate_common  │   │  ← 唯一业务逻辑（原样不动）
│  │  gethotupdatefiles / gethotupdateprops / │   │
│  │  GetHotUpdateFile                        │   │
│  └─────────────────────────────────────────┘   │
└───────────────┬───────────────────────────────┘
                │ 免锁读取（依赖 writer 的 rename 原子替换）
        /data/hotupdate/{filelist,proplist,para/}
```

**关键点**：**源文件层面保持干净分离**（JNI 一个文件、业务逻辑另有文件），
**制品层面合成一个 `.so`**。评审时 JNI 边界一眼可辨；纯 C++ 消费者继续用 `android::hotupdate::*`
namespace 符号，与 JNI 互不干扰。

---

## 四、目录结构

```
system/.../hotupdate/
├── Android.bp
├── include/hotupdate/
│   ├── hotupdate_client.h        # 读接口头（不变）
│   └── hotupdate_common.h        # 公共（不变）
├── hotupdate_common.cpp          # 公共逻辑（不变）
├── hotupdate_reader.cpp          # 纯 C++ 读实现（不变）
└── hotupdate_jni.cpp             # ★ 新增：JNI 桥接，编进 client 库
```

---

## 五、构建改动（`Android.bp`，最小化）

改动只有两行：`srcs` 加一个文件、新增 `header_libs`。**依赖列表、分区、可见性均不变。**

```python
cc_library_shared {
    name: "libhotupdate_client",
    srcs: [
        "hotupdate_reader.cpp",
        "hotupdate_jni.cpp",        // ★ 唯一新增源文件
    ],
    header_libs: ["jni_headers"],   // ★ 头文件依赖，无运行时 .so 依赖
    static_libs: ["libhotupdate_common"],
    shared_libs: ["liblog"],        // 运行时依赖不变（未新增）
    export_include_dirs: ["include"],
    cflags: ["-Wall", "-Werror"],
    vendor_available: true,
    system_ext_specific: true,
}
```

> 说明：`jni_headers` 是 AOSP 提供 `jni.h` 的 `header_libs`（纯头），不产生运行时链接依赖。

---

## 六、JNI 桥接源文件（`hotupdate_jni.cpp`）

```cpp
/*
 * Copyright (C) 2024 The Vendor Project
 * SPDX-License-Identifier: Apache-2.0
 *
 * JNI 桥接层：只做类型转换，不含任何业务逻辑。
 * 编进 libhotupdate_client.so，复用同库内的 native reader，不新增制品。
 */

#define LOG_TAG "hotupdate_jni"

#include <jni.h>
#include <limits.h>          // PATH_MAX

#include <string>
#include <vector>

#include <log/log.h>

#include "hotupdate/hotupdate_client.h"   // 同库内的 native reader 公开头

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
        // 及时释放局部引用，避免记录数较多时局部引用表溢出
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

// RegisterNatives 绑定：对外只导出 JNI_OnLoad 一个符号，桥接函数保持匿名命名空间（不导出）
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

> 该文件与独立 `libhotupdate_jni.so` 方案中的桥接代码**完全一致**——差别仅在于它被编进 client 库，
> 而非独立库。`buf/bufLen` 在 `nativeGetHotUpdateFile` 内用栈上 `char buf[PATH_MAX]` 消化，不上浮到 Java。

---

## 七、Java 层实现（`HotUpdateManager.java`）

与独立 `.so` 方案唯一的区别：`System.loadLibrary` 的目标从 `"hotupdate_jni"` 改为 `"hotupdate_client"`。
其余代码一字不改。

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
 * 热更新记录读取 SDK（App 侧）。
 *
 * <p>薄壳：解析 / 校验 / 去重 / 上限 / 路径拼接逻辑全部在 native（同一个
 * {@code libhotupdate_client.so} 内），本类仅负责加载库、空安全、返回值到 Java 类型的转换，
 * 因此行为与系统内 C++ 调用方逐字节一致。永不抛异常。
 *
 * <p>纯静态无状态，线程安全。
 */
public final class HotUpdateManager {

    private static final String TAG = "HotUpdate";

    /** 在 filelist 中查找（与 native type 一致）。 */
    public static final int TYPE_FILE = 0;
    /** 在 proplist 中查找（与 native type 一致）。 */
    public static final int TYPE_PROP = 1;

    /** native 库是否可用；加载失败时各接口安全降级。 */
    private static final boolean NATIVE_AVAILABLE = loadNativeLib();

    private HotUpdateManager() {
    }

    private static boolean loadNativeLib() {
        try {
            // 注意：JNI 入口内置于 client 库，直接加载 client 库本身
            System.loadLibrary("hotupdate_client");
            return true;
        } catch (UnsatisfiedLinkError e) {
            Log.e(TAG, "load libhotupdate_client.so failed; APIs will return empty", e);
            return false;
        }
    }

    /** 读取所有热更新文件名。文件不存在 / 无记录 / 库不可用时返回空列表，永不返回 null。 */
    public static ArrayList<String> getHotUpdateFiles() {
        if (!NATIVE_AVAILABLE) {
            return new ArrayList<>();
        }
        String[] arr = nativeGetHotUpdateFiles();
        return arr == null ? new ArrayList<>() : new ArrayList<>(Arrays.asList(arr));
    }

    /** 读取所有热更新属性名。文件不存在 / 无记录 / 库不可用时返回空列表，永不返回 null。 */
    public static ArrayList<String> getHotUpdateProps() {
        if (!NATIVE_AVAILABLE) {
            return new ArrayList<>();
        }
        String[] arr = nativeGetHotUpdateProps();
        return arr == null ? new ArrayList<>() : new ArrayList<>(Arrays.asList(arr));
    }

    /**
     * 在 filelist / proplist 中精确查找 {@code pathSuffix}，命中后返回 para 目录下的实体文件。
     * 参数与 native {@code GetHotUpdateFile} 对齐（{@code buf/bufLen} 由 JNI 层内部处理）。
     * 返回的 {@link File} 不保证磁盘上一定存在，调用方应自行 {@link File#exists()} / {@link File#canRead()}。
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

## 八、两处务必注意

1. **符号可见性**
   若 `libhotupdate_client` 使用了 `-fvisibility=hidden` 或 version script（`.map`），要确保
   `JNI_OnLoad` 被导出。`JNIEXPORT` 宏本身带 `visibility("default")`，通常足够；若库有 version script，
   需把 `JNI_OnLoad` 显式加入导出列表。

2. **ABI 检查**
   若该库受 `header-abi-checker` / `abidiff` 管控，新增的 `JNI_OnLoad` 会出现在 ABI diff 中。
   它是标准 JNI 符号，解释成本低，但**要预期它会被工具标出**，提前在评审材料里说明。

---

## 九、与「独立 `libhotupdate_jni.so`」方案对比

| 维度 | 独立 `libhotupdate_jni.so` | 内置进 `libhotupdate_client.so`（本方案） |
|---|---|---|
| 制品数量 | **新增 1 个** `.so` | **不新增**，仅改现有库 |
| 评审流程 | 需为新制品走完整入库 + 专家评审 | 只走「改现有库」流程，材料更简单 |
| 运行时依赖 | 新增库依赖 client 库 | **零新增运行时依赖** |
| 导出符号变化 | 新库自带 `JNI_OnLoad` | 现库 **+1** 个 `JNI_OnLoad` |
| 分层洁癖 | JNI 与 reader 物理隔离，最“纯” | 源文件隔离、制品合一，够清晰 |
| Java `loadLibrary` | `"hotupdate_jni"` | `"hotupdate_client"` |
| 适用 | 允许自由新增系统制品、追求彻底解耦 | **制品受管控、交付紧、已有 reader 库**（本场景） |

逻辑分层、JNI 代码、SELinux/DAC 依赖、UTF-8 注意点等，两方案**完全相同**，此处不赘述，
详见《热更新接口Java-JNI封装方案》。

---

## 十、DAC / SELinux 权限（与独立库方案一致）

权限按**进程**判定，与「JNI 内置还是独立」无关：JNI 代码运行在 **App 进程**，继承 App 的 UID 与 SELinux 域。

```te
typeattribute platform_app hotupdate_reader_domain;
typeattribute priv_app     hotupdate_reader_domain;
# 三方 untrusted_app 受平台 neverallow 限制，无法文件级直接放开，
# 如确需暴露给三方应用，走 system_server 的 Binder 接口转发。

allow hotupdate_reader_domain hotupdate_dir:dir { search getattr };
allow hotupdate_reader_domain hotupdate_public_file:file { open read getattr };
```

- **文件侧配置**（类型 / file_contexts / neverallow）与纯 C++、独立库方案完全共享。
- **读授权主体**必须是真正 `open()` 文件的域——此处是 App 域。
- 三方 App 若要 `System.loadLibrary("hotupdate_client")`，该库仍需登记为 public library
  并在 `AndroidManifest.xml` 声明 `<uses-native-library>`；系统/预置 App 无此限制。
- 无权限时：native `open()` 被拒 → reader 返回空 → JNI 返回空数组 → Java 返回空列表/null，**App 不崩溃**。

---

## 十一、对评审如实说明（不过度承诺）

本方案**规避的是「新增一个系统制品」**——不必为全新 `.so` 走完整入库/评审。但它**仍是对已过审库的修改**
（多一个源文件、一个头依赖、一个导出符号、体积略增）：

- 若贵司「改现有库」流程比「新增库」轻（通常如此），本方案能实打实省流程；
- 若「任何 ABI / 依赖变更」都要同级评审，则省下的主要是「新制品登记」部分，评审仍需走，
  但材料更简单——可强调三点：**零新增运行时依赖、仅 +1 个标准符号 `JNI_OnLoad`、JNI 层无业务逻辑**。

---

## 十二、落地前替换 / 确认项

1. **包名 / 类名**：`com.vendor.hotupdate.HotUpdateManager` 为占位，替换为实际值；
   `hotupdate_jni.cpp` 中 `kClassName` 必须与 Java 包名严格一致。
2. **reader 头文件路径**：`#include "hotupdate/hotupdate_client.h"` 按实际路径调整。
3. **符号导出**：确认 client 库的 version script / visibility 设置放行 `JNI_OnLoad`。
4. **三方可用性**：面向三方 App 时配好 public library + `<uses-native-library>` + SELinux 读者白名单。
5. **`TYPE_PROP` 语义**：仍继承综合方案 `GetHotUpdateFile(type=1)` 的未决点，由 C++ 侧统一定义，
   Java/JNI 自动跟随。

---

## 十三、一句话总结

> 把 `hotupdate_jni.cpp` 作为独立源文件编进已过审的 `libhotupdate_client.so`，
> 用 `RegisterNatives` 对外只暴露 `JNI_OnLoad` 一个符号，**不引入新运行时依赖、不改业务逻辑、不新增 `.so` 制品**。
> Java 侧改一行 `System.loadLibrary("hotupdate_client")` 即可。
> 以「改现有库」替代「新增制品评审」，在满足公司管控与交付时限的同时，
> 保留 JNI 方案「单一事实源、两端逐字节一致」的全部优点。
