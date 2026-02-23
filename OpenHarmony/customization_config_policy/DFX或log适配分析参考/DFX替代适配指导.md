# config_policy DFX 替代适配指导

## 适用场景

移植目标系统**没有** OpenHarmony HiSysEvent / HiLog 诊断框架，
需要用目标系统自有的日志或诊断接口替代 `frameworks/dfx/` 目录下的实现。

---

## 一、现有 DFX 代码分析

### 1.1 目录结构

```
frameworks/dfx/
├── hisysevent.yaml                        # OH DFX 事件 schema 定义
└── hisysevent_adapter/
    ├── hisysevent_adapter.h               # 对外接口声明（仅此一个头文件）
    └── hisysevent_adapter.cpp             # 依赖 HiSysEvent + HiLog 的实现
```

### 1.2 对外接口

`hisysevent_adapter.h` 只暴露一个枚举和一个函数：

```cpp
namespace OHOS::Customization::ConfigPolicy {

enum class ReportType {
    CONFIG_POLICY_FAILED = 0,   // 故障上报：核心函数返回 NULL 时触发
    CONFIG_POLICY_EVENT,        // 统计上报：定义在 yaml，但代码中从未调用
};

void ReportConfigPolicyEvent(ReportType reportType,
                              const std::string &apiName,
                              const std::string &msgInfo);
}
```

### 1.3 外部依赖

`hisysevent_adapter.cpp` 依赖以下两个 OH 专有库：

| 依赖 | 头文件 | 用途 |
|------|--------|------|
| HiSysEvent | `hisysevent.h` | `HiSysEventWrite()` — 结构化事件上报 |
| HiLog | `hilog/log.h` | `HILOG_ERROR()` — 错误日志输出 |

### 1.4 调用点分析

`ReportConfigPolicyEvent` 共有 **5 处调用**，全部位于 NAPI/FFI 层，全部是错误路径：

| 文件 | 触发条件 | 上报类型 |
|------|----------|----------|
| `config_policy_napi.cpp` | `GetCfgDirList()` 返回 NULL（异步） | FAILED |
| `config_policy_napi.cpp` | `GetCfgDirList()` 返回 NULL（同步） | FAILED |
| `config_policy_ffi.cpp` | `GetCfgDirList()` 返回 NULL | FAILED |
| `config_policy_ffi.cpp` | `GetCfgFilesEx()` 返回 NULL | FAILED |
| `config_policy_ffi.cpp` | `GetOneCfgFileEx()` 返回 NULL | FAILED |

> **关键发现**：`CONFIG_POLICY_EVENT`（统计类型）在 `hisysevent.yaml` 中定义，
> 但在现有代码中**从未被调用**，移植时可忽略。

---

## 二、替换策略

只需处理以下三个文件，调用方**零改动**：

| 文件 | 处理方式 | 说明 |
|------|----------|------|
| `hisysevent.yaml` | **直接删除** | OH DFX 专有 schema，目标系统不使用 |
| `hisysevent_adapter.h` | **保持不变** | 接口稳定，NAPI/FFI 调用方无需修改 |
| `hisysevent_adapter.cpp` | **替换实现** | 唯一依赖 OH 专有库的文件 |
| `port/config_policy_log.h` | **新增** | 宏桥接文件，用户填入目标系统接口 |

---

## 三、方案A：宏桥接（推荐）

最灵活，不绑定任何具体日志库。
用户只需编辑 `port/config_policy_log.h` 一个文件，将宏映射到目标系统的日志调用。

### 3.1 新建 `port/config_policy_log.h`

```c
/*
 * port/config_policy_log.h
 *
 * 将此文件中的宏替换为目标系统的日志接口。
 * 默认实现：输出到 stderr，不依赖任何外部库。
 *
 * 替换方式：注释掉下方默认实现，填入目标系统的日志调用，
 * 参考本文件末尾的各平台示例。
 */
#ifndef CONFIG_POLICY_LOG_H
#define CONFIG_POLICY_LOG_H

/* ── 在此处替换为目标系统的日志接口 ─────────────────────────────── */

#ifndef CONFIG_POLICY_LOG_ERROR
#  include <stdio.h>
#  define CONFIG_POLICY_LOG_ERROR(fmt, ...) \
       fprintf(stderr, "[CONFIG_POLICY][E] " fmt "\n", ##__VA_ARGS__)
#endif

#ifndef CONFIG_POLICY_LOG_INFO
#  include <stdio.h>
#  define CONFIG_POLICY_LOG_INFO(fmt, ...) \
       fprintf(stderr, "[CONFIG_POLICY][I] " fmt "\n", ##__VA_ARGS__)
#endif

/* ─────────────────────────────────────────────────────────────────── */

#endif /* CONFIG_POLICY_LOG_H */
```

### 3.2 替换 `hisysevent_adapter.cpp`

```cpp
/*
 * frameworks/dfx/hisysevent_adapter/hisysevent_adapter.cpp
 *
 * 移植版：用 config_policy_log.h 中的宏替代 HiSysEvent + HiLog。
 * 调用方（config_policy_napi.cpp、config_policy_ffi.cpp）零改动。
 */
#include "hisysevent_adapter.h"
#include "config_policy_log.h"   // 替代 hisysevent.h + hilog/log.h

namespace OHOS {
namespace Customization {
namespace ConfigPolicy {

void ReportConfigPolicyEvent(ReportType reportType,
                              const std::string &apiName,
                              const std::string &msgInfo)
{
    if (reportType == ReportType::CONFIG_POLICY_FAILED) {
        /*
         * 对应原来的 HiSysEventWrite(FAULT) + HILOG_ERROR。
         * msgInfo 通常是固定字符串，如 "CfgDirList is nullptr."
         */
        CONFIG_POLICY_LOG_ERROR("api=%s failed: %s",
                                 apiName.c_str(), msgInfo.c_str());
    } else {
        /* CONFIG_POLICY_EVENT：统计类，当前代码实际上从未调用 */
        CONFIG_POLICY_LOG_INFO("api=%s", apiName.c_str());
    }
}

} // namespace ConfigPolicy
} // namespace Customization
} // namespace OHOS
```

### 3.3 各平台日志接口填写示例

在 `port/config_policy_log.h` 中按需选择，替换默认的 `fprintf` 实现：

```c
/* ── 示例1：POSIX syslog ─────────────────────────────────────────── */
#include <syslog.h>
#define CONFIG_POLICY_LOG_ERROR(fmt, ...) \
    syslog(LOG_ERR,  "[config_policy] " fmt, ##__VA_ARGS__)
#define CONFIG_POLICY_LOG_INFO(fmt, ...) \
    syslog(LOG_INFO, "[config_policy] " fmt, ##__VA_ARGS__)

/* ── 示例2：Android logcat ───────────────────────────────────────── */
#include <android/log.h>
#define CONFIG_POLICY_LOG_ERROR(fmt, ...) \
    __android_log_print(ANDROID_LOG_ERROR, "config_policy", fmt, ##__VA_ARGS__)
#define CONFIG_POLICY_LOG_INFO(fmt, ...) \
    __android_log_print(ANDROID_LOG_INFO,  "config_policy", fmt, ##__VA_ARGS__)

/* ── 示例3：目标系统自有日志（接口为 YourLog(level, tag, fmt, ...)） */
#include "your_system_log.h"
#define CONFIG_POLICY_LOG_ERROR(fmt, ...) \
    YourLog(LOG_LEVEL_ERROR, "config_policy", fmt, ##__VA_ARGS__)
#define CONFIG_POLICY_LOG_INFO(fmt, ...) \
    YourLog(LOG_LEVEL_INFO,  "config_policy", fmt, ##__VA_ARGS__)

/* ── 示例4：完全静默（不需要任何日志输出） ──────────────────────── */
#define CONFIG_POLICY_LOG_ERROR(fmt, ...) ((void)0)
#define CONFIG_POLICY_LOG_INFO(fmt, ...)  ((void)0)
```

---

## 四、方案B：回调函数注册

适合**日志系统在运行期才能确定**的场景（例如通过插件加载日志库）。

### 4.1 在 `hisysevent_adapter.h` 末尾追加声明

```cpp
// 可选：注册自定义日志回调，不调用则使用默认 fprintf 输出
// level: 0 = ERROR, 1 = INFO
typedef void (*ConfigPolicyLogFunc)(int level, const char *tag,
                                    const char *api, const char *msg);

void SetConfigPolicyLogCallback(ConfigPolicyLogFunc callback);
```

### 4.2 替换 `hisysevent_adapter.cpp`

```cpp
#include "hisysevent_adapter.h"
#include <cstdio>

namespace OHOS {
namespace Customization {
namespace ConfigPolicy {

static ConfigPolicyLogFunc g_logCallback = nullptr;

void SetConfigPolicyLogCallback(ConfigPolicyLogFunc callback)
{
    g_logCallback = callback;
}

static void DefaultLog(int level, const char *tag,
                        const char *api, const char *msg)
{
    const char *lvStr = (level == 0) ? "E" : "I";
    fprintf(stderr, "[CONFIG_POLICY][%s] tag=%s api=%s %s\n",
            lvStr, tag, api, msg ? msg : "");
}

void ReportConfigPolicyEvent(ReportType reportType,
                              const std::string &apiName,
                              const std::string &msgInfo)
{
    ConfigPolicyLogFunc fn = g_logCallback ? g_logCallback : DefaultLog;
    int level = (reportType == ReportType::CONFIG_POLICY_FAILED) ? 0 : 1;
    fn(level, "config_policy", apiName.c_str(), msgInfo.c_str());
}

} // namespace ConfigPolicy
} // namespace Customization
} // namespace OHOS
```

### 4.3 在程序初始化阶段注册回调

```cpp
#include "hisysevent_adapter.h"
using namespace OHOS::Customization::ConfigPolicy;

// 程序启动时注册一次即可
SetConfigPolicyLogCallback([](int level, const char *tag,
                               const char *api, const char *msg) {
    // 替换为目标系统的日志调用
    YourSystemLog(level == 0 ? LEVEL_ERROR : LEVEL_INFO,
                  "%s: api=%s %s", tag, api, msg);
});
```

---

## 五、两种方案对比

| 对比项 | 方案A：宏桥接 | 方案B：回调注册 |
|--------|--------------|----------------|
| 实现复杂度 | 低 | 中 |
| 日志接口确定时机 | 编译期 | 运行期 |
| 性能 | 零开销（宏内联） | 间接调用（函数指针） |
| 适合场景 | 日志接口在编译期已知 | 日志库动态加载或插件化 |
| 推荐程度 | **推荐** | 按需选用 |

---

## 六、CMakeLists.txt 修改

在 `移植指导.md` 的构建脚本基础上，移除 OH DFX 依赖，加入替换文件：

```cmake
# NAPI/FFI 层（包含 hisysevent_adapter 的替换实现）
add_library(config_policy_napi SHARED
    interfaces/kits/js/src/config_policy_napi.cpp
    frameworks/dfx/hisysevent_adapter/hisysevent_adapter.cpp  # 已替换实现
)

target_include_directories(config_policy_napi PRIVATE
    frameworks/dfx/hisysevent_adapter   # hisysevent_adapter.h（保持不变）
    port                                # config_policy_log.h（方案A新增）
    interfaces/inner_api/include
    # 已移除：hisysevent 和 hilog 的头文件路径
)

target_compile_options(config_policy_napi PRIVATE
    -std=c++14
)

# 已移除原来的依赖：
# target_link_libraries(config_policy_napi hisysevent hilog)

# 方案A：如使用 POSIX syslog，需链接（某些平台需要显式链接）
# target_link_libraries(config_policy_napi) # syslog 通常无需单独链接

# 方案A：如使用 Android logcat
# target_link_libraries(config_policy_napi log)
```

---

## 七、注意事项

### 7.1 `hisysevent.yaml` 不需要替换

该文件是 OH DFX 框架用于注册事件 schema 的配置文件，与运行时代码无关。
移植时直接删除，目标系统不需要对应文件。

### 7.2 `CONFIG_POLICY_EVENT` 统计类型实际未使用

虽然 `ReportType::CONFIG_POLICY_EVENT` 在枚举中定义，
但现有代码的 5 个调用点全部使用 `CONFIG_POLICY_FAILED`，
`CONFIG_POLICY_EVENT` 从未被调用。
适配层中对该分支做基础处理（如 INFO 级日志）即可，无需特别关注。

### 7.3 宏中的可变参数兼容性

方案A 使用 `##__VA_ARGS__` 语法，这是 GCC/Clang 扩展，
C99/C11 标准的对应写法是 `__VA_ARGS__`（不带 `##`）。
大多数嵌入式工具链（GCC、Clang、ARMCC 新版）均支持 `##__VA_ARGS__`，
若遇到编译器不支持，改为 `__VA_ARGS__` 并确保调用时始终传入至少一个格式参数。

### 7.4 线程安全

方案B 中 `g_logCallback` 是全局变量。
若存在多线程并发调用 `ReportConfigPolicyEvent` 与 `SetConfigPolicyLogCallback` 的场景，
需在 `SetConfigPolicyLogCallback` 中加锁或使用原子指针：

```cpp
#include <atomic>
static std::atomic<ConfigPolicyLogFunc> g_logCallback{nullptr};
```

方案A 的宏调用本身没有全局状态，线程安全性由目标日志库保证。

---

## 八、改动文件总览

```
frameworks/dfx/
├── hisysevent.yaml                        ← 删除
└── hisysevent_adapter/
    ├── hisysevent_adapter.h               ← 保持不变（方案B 末尾追加声明）
    └── hisysevent_adapter.cpp             ← 替换实现

port/
├── config_policy_param_adapter.h          （来自 环境变量适配指导.md）
├── compat_securec.h                       （来自 移植指导.md）
└── config_policy_log.h                    ← 新增（方案A 宏桥接）
```

外部依赖从 `hisysevent` + `hilog` 两个 OH 专有组件，
变为**零外部依赖**（默认 `fprintf`）或目标系统日志库（用户自选）。
