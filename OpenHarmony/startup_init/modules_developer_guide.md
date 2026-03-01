# startup_init modules 模块开发指南

> **面向读者**：OpenHarmony / C 语言开发新手
> **文档目标**：帮助你理解 `services/modules/` 的架构，并从零开发一个新模块
> **源码路径**：`D:\projects\startup_init\services\modules\`

---

## 目录

1. [modules 目录是什么](#1-modules-目录是什么)
2. [插件化架构核心概念](#2-插件化架构核心概念)
   - 2.1 [MODULE_CONSTRUCTOR 宏](#21-module_constructor-宏)
   - 2.2 [HookMgr 钩子管理器](#22-hookmgr-钩子管理器)
   - 2.3 [AddCmdExecutor 命令注册](#23-addcmdexecutor-命令注册)
   - 2.4 [静态模块与动态模块](#24-静态模块与动态模块)
3. [现有 14 个模块详解](#3-现有-14-个模块详解)
4. [完整钩子点参考表](#4-完整钩子点参考表)
5. [可用 API 速查手册](#5-可用-api-速查手册)
6. [新模块开发全流程（实战）](#6-新模块开发全流程实战)
   - 6.1 [第一步：规划模块](#61-第一步规划模块)
   - 6.2 [第二步：创建目录和文件](#62-第二步创建目录和文件)
   - 6.3 [第三步：编写核心逻辑](#63-第三步编写核心逻辑)
   - 6.4 [第四步：编写静态初始化文件](#64-第四步编写静态初始化文件)
   - 6.5 [第五步：编写 BUILD.gn 构建配置](#65-第五步编写-buildgn-构建配置)
   - 6.6 [第六步：注册到父目录 BUILD.gn](#66-第六步注册到父目录-buildgn)
7. [常见开发场景与代码模板](#7-常见开发场景与代码模板)
   - 7.1 [场景一：在启动时执行一次性任务](#71-场景一在启动时执行一次性任务)
   - 7.2 [场景二：注册新的 init.cfg 命令](#72-场景二注册新的-initcfg-命令)
   - 7.3 [场景三：监听服务的启动/停止事件](#73-场景三监听服务的启动停止事件)
   - 7.4 [场景四：解析服务配置中的自定义字段](#74-场景四解析服务配置中的自定义字段)
   - 7.5 [场景五：通过系统参数控制模块开关](#75-场景五通过系统参数控制模块开关)
8. [调试与日志使用](#8-调试与日志使用)
9. [完整示例：hello_module](#9-完整示例hello_module)
10. [常见错误与排查](#10-常见错误与排查)
11. [参考资料](#11-参考资料)

---

## 1. modules 目录是什么

`services/modules/` 是 init 系统的**可插拔功能扩展层**。

### 为什么需要它？

init 主进程（PID=1）需要保持代码精简、职责单一。但随着系统功能增加，各种需求不断涌入：要统计启动耗时、要加载安全策略、要支持模块热更新……如果把这些全塞进 init 主逻辑，代码会变得臃肿且难以维护。

`modules/` 的设计解决了这个问题：**功能以"插件"形式独立存在，通过钩子机制挂入 init 的生命周期**。

### 与 init 主进程的关系

```
init 主进程 (PID=1)
    │
    ├── 核心逻辑（不变）
    │       main.c / init.c / init_service_manager.c ...
    │
    └── 插件系统（可扩展）
            │
            ├── 静态模块（编译进 init 可执行文件）
            │       bootchart_static.c, udid_static.c ...
            │
            └── 动态模块（运行时加载的 .so 文件）
                    /system/lib64/init/bootchart.so
                    /system/lib64/init/inittrace.so
                    ...
```

- **静态模块**：在 init 启动时自动执行，负责"早期决策"（如：要不要加载某个动态模块）
- **动态模块**：`.so` 共享库，被静态模块按需加载，包含主要业务逻辑

---

## 2. 插件化架构核心概念

在写代码之前，必须理解三个核心机制。

### 2.1 MODULE_CONSTRUCTOR 宏

这是**所有模块的入口点**。

```c
MODULE_CONSTRUCTOR(void)
{
    // 这里的代码在模块被加载时自动执行
    // 相当于 C++ 的全局对象构造函数
}
```

**底层原理**：这个宏展开后是 `__attribute__((constructor))`，这是 GCC 的特性，被标记的函数会在 `main()` 之前或 `.so` 被 `dlopen()` 时自动调用。

对应的析构宏是：

```c
MODULE_DESTRUCTOR(void)
{
    // 模块卸载时执行，用于释放资源
    // 相当于 C++ 的全局对象析构函数
}
```

### 2.2 HookMgr 钩子管理器

HookMgr 是模块与 init 主流程交互的核心桥梁。

**原理类比**：想象 init 的启动过程是一条流水线，流水线上有很多"插座"（钩子点）。模块可以向任意"插座"插入自己的处理函数，当流水线执行到那里时，会自动调用所有插入的函数。

```c
// 向钩子点注册处理函数
HookMgrAdd(
    GetBootStageHookMgr(),   // 获取全局钩子管理器
    INIT_POST_CFG_LOAD,      // 钩子点：配置文件加载后
    0,                       // 优先级（数字越小越先执行）
    MyHookFunction           // 你的处理函数
);
```

**处理函数的签名**（固定格式）：

```c
static int MyHookFunction(const HOOK_INFO *hookInfo, void *cookie)
{
    // hookInfo: 钩子自身信息（可忽略）
    // cookie:   钩子点传递的上下文数据（不同钩子点类型不同）

    // 执行你的逻辑 ...

    return 0; // 返回 0 表示成功
}
```

### 2.3 AddCmdExecutor 命令注册

允许模块向 init 注册新命令，这些命令可以在 `.cfg` 配置文件中使用。

```c
// 注册命令
AddCmdExecutor("my_command", MyCommandHandler);
```

注册后，你就可以在 `init.cfg` 中这样使用：

```json
{
    "name": "init",
    "cmds": [
        "my_command arg1 arg2"
    ]
}
```

**命令处理函数签名**（固定格式）：

```c
static int MyCommandHandler(int id, const char *name, int argc, const char **argv)
{
    // id:    命令的内部 ID（通常忽略）
    // name:  命令名称，如 "my_command"
    // argc:  参数个数（不含命令名本身）
    // argv:  参数数组，argv[0] 是第一个参数

    if (argc < 1) {
        PLUGIN_LOGE("my_command: need at least 1 argument");
        return -1;
    }

    PLUGIN_LOGI("my_command called with: %s", argv[0]);
    return 0; // 0 表示成功
}
```

### 2.4 静态模块与动态模块

| 特性 | 静态模块 (`*_static.c`) | 动态模块（主 `.c` 文件） |
|------|------------------------|--------------------------|
| 编译产物 | 直接编译进 init 可执行文件 | 独立的 `.so` 共享库 |
| 加载时机 | init 启动时自动加载 | 由静态模块调用 `InitModuleMgrInstall()` 按需加载 |
| 主要职责 | 注册早期钩子，决定是否加载动态模块 | 实现主要业务逻辑 |
| 典型代码 | `InitAddPreCfgLoadHook(0, EarlyHook)` | 业务函数 + `MODULE_CONSTRUCTOR` |

**静态模块加载动态模块的流程**：

```c
// 静态模块：udid_static.c
static int UDidCalc(const HOOK_INFO *hookInfo, void *cookie)
{
    InitModuleMgrInstall("udidmodule");    // 加载 udidmodule.so
    InitModuleMgrUnInstall("udidmodule"); // 用完卸载
    return 0;
}

MODULE_CONSTRUCTOR(void)
{
    InitAddPreCfgLoadHook(0, UDidCalc); // 在配置加载前触发
}
```

`InitModuleMgrInstall("xxx")` 实际上是去 `/system/lib64/init/xxx.so`（或 `lib/init/`）找对应的 `.so` 文件并加载它。

---

## 3. 现有 14 个模块详解

```
services/modules/
├── bootchart/       性能监控
├── bootevent/       启动事件追踪
├── crashhandler/    崩溃信号处理
├── encaps/          内核权限封装
├── init_context/    多 SELinux 上下文管理
├── init_eng/        工程模式分区挂载
├── init_hook/       ★ 钩子基础设施（其他模块依赖它）
├── module_update/   模块热更新
├── reboot/          重启/关机控制
├── seccomp/         系统调用过滤
├── selinux/         SELinux 策略集成
├── sysevent/        系统事件上报
├── trace/           内核 ftrace 追踪
└── udid/            唯一设备 ID 生成
```

### bootchart — 启动性能监控

| 项目 | 内容 |
|------|------|
| **功能** | 后台线程定期采集 `/proc/stat`（CPU）、`/proc/[pid]/stat`（进程）、`/proc/diskstats`（磁盘）统计数据 |
| **触发条件** | 系统参数 `persist.init.bootchart.enabled=1` |
| **输出文件** | `/data/service/el0/startup/init/proc_stat.log` 等 |
| **关键文件** | `bootchart.c`（主逻辑）、`bootchart_static.c`（参数检测） |
| **钩子点** | `INIT_POST_PERSIST_PARAM_LOAD`（读参数后决定是否启用） |

**静态模块逻辑**：读取参数 `persist.init.bootchart.enabled`，若为 `"1"` 则加载 `bootchart.so`。

---

### bootevent — 启动事件时间轴

| 项目 | 内容 |
|------|------|
| **功能** | 记录各服务的 fork 时间和 ready 时间，输出可视化的 JSON 启动时间轴 |
| **输出文件** | `/data/log/startup/bootup.trace` |
| **关键文件** | `bootevent.c`、`bootevent.h` |
| **钩子点** | `INIT_CMD_RECORD`（命令计时）、`INIT_SERVICE_FORK_AFTER`（fork后打时间戳） |
| **服务配置字段** | 服务 JSON 中的 `"bootevent"` 字段 |

---

### crashhandler — 崩溃信号处理

| 项目 | 内容 |
|------|------|
| **功能** | 为 init 进程自身安装崩溃信号处理器（SIGSEGV、SIGABRT 等）。若 init（PID=1）自身崩溃，触发系统 panic 重启；普通进程则直接退出。 |
| **关键文件** | `crash_handler.c` |
| **注意** | 不使用 `MODULE_CONSTRUCTOR`，而是由 init 主进程直接调用 `InstallLocalSignalHandler()` |

---

### encaps — 内核权限封装

| 项目 | 内容 |
|------|------|
| **功能** | 通过 `/dev/encaps` 设备的 `ioctl` 接口，在服务启动前为其设置内核级权限封装（细粒度权限控制） |
| **关键文件** | `encaps_static.c` |
| **钩子点** | `INIT_SERVICE_SET_PERMS_BEFORE`（服务权限设置前） |
| **编译条件** | `init_use_encaps = true` 时才编译 |

---

### init_context — 多上下文 sub-init 管理

| 项目 | 内容 |
|------|------|
| **功能** | 支持以不同的 SELinux 上下文运行 init 命令。主要用于 chipset 域（芯片厂商）的初始化命令需要在 `u:r:chipset_init:s0` 上下文下执行，而不是主 init 的上下文。 |
| **关键文件** | `init_context.c`、`init_context.h` |
| **原理** | Fork 一个子 init 进程，通过 socketpair 进行 IPC，将命令发给子进程执行 |
| **钩子点** | `INIT_PRE_CFG_LOAD`（早期初始化） |

---

### init_eng — 工程模式分区挂载

| 项目 | 内容 |
|------|------|
| **功能** | 当内核 cmdline 中有 `ohos.boot.root_package=on` 时，额外挂载 `/eng_system` 和 `/eng_chipset` 分区，用于工程调试 |
| **关键文件** | `init_eng.c`、`init_eng_static.c` |
| **钩子点** | `INIT_GLOBAL_INIT`（全局初始化阶段，优先级 2） |

---

### init_hook — 钩子基础设施（★重要）

| 项目 | 内容 |
|------|------|
| **功能** | 1. 提供 `ServiceExtData` 机制，允许模块向服务挂载额外数据；2. 封装所有 `InitAdd*Hook()` 辅助函数；3. 注册 `setloglevel`、`initcmd` 等基础命令；4. 启动完成时清理钩子和释放内存 |
| **关键文件** | `init_hook.c`、`init_hook.h` |
| **被依赖** | 几乎所有其他模块都依赖本模块提供的 API |

`ServiceExtData` 用法：模块可以向任意服务附加自定义数据，而无需修改 `Service` 结构体：

```c
// selinux 模块用法：给服务存储 SELinux 上下文字符串
ServiceExtData *extData = AddServiceExtData(
    serviceName,          // 服务名
    HOOK_ID_SELINUX,      // 模块自定义的 ID（用于区分不同模块的数据）
    seconText,            // 数据指针
    strlen(seconText) + 1 // 数据长度
);
```

---

### module_update — 模块热更新

| 项目 | 内容 |
|------|------|
| **功能** | 挂载 tmpfs 到 `/module_update`，执行 `check_module_update_init` 检查并应用模块更新。启动完成后自动卸载自身（`AutorunModuleMgrUnInstall`）。 |
| **关键文件** | `module_update_init.cpp`（C++ 实现） |
| **钩子点** | `INIT_MOUNT_STAGE`（文件系统挂载阶段）、`INIT_BOOT_COMPLETE`（启动完成） |

---

### reboot — 重启/关机控制

| 项目 | 内容 |
|------|------|
| **功能** | 实现所有重启场景：正常重启（`reboot`）、崩溃重启（`panic`）、关机（`shutdown`）、进入刷机模式（`updater`）等。写入 misc 分区的重启原因供下次启动读取。 |
| **关键文件** | `reboot.c`、`reboot_static.c`、`reboot_misc.c` |
| **注册命令** | `reboot`、`panic`、`shutdown`、`updater` |
| **钩子点** | `INIT_REBOOT`（重启事件） |

---

### seccomp — 系统调用过滤

| 项目 | 内容 |
|------|------|
| **功能** | 为不同类型的进程（app/system/updater）加载对应的 seccomp 过滤策略，限制进程可以使用的系统调用集合，增强安全性 |
| **关键文件** | `seccomp_policy.c`、`seccomp_policy/` 目录下的策略文件 |
| **钩子点** | `INIT_SERVICE_SET_PERMS_BEFORE`（服务权限设置前注入过滤器） |
| **编译条件** | `build_seccomp = true` 时才编译 |

---

### selinux — SELinux 安全策略集成

| 项目 | 内容 |
|------|------|
| **功能** | 加载 SELinux 策略文件（`loadSelinuxPolicy`），在服务 fork 后设置其 SELinux 执行上下文（`setServiceContent`），递归恢复文件的 SELinux 标签（`restoreContentRecurse`） |
| **关键文件** | `selinux_adp.c`、`selinux_static.c` |
| **服务配置字段** | 服务 JSON 中的 `"secon": "u:r:my_service:s0"` |
| **编译条件** | `build_selinux = true` 时才编译 |

---

### sysevent — 系统事件上报

| 项目 | 内容 |
|------|------|
| **功能** | 将启动耗时等关键事件上报到 HiSysEvent 框架，供系统诊断、性能分析使用 |
| **关键文件** | `sys_event.c`、`init_hisysevent.c`、`init_events.yaml` |
| **被调用方式** | 其他模块通过 `ReportSysEvent()` 或 `ReportServiceStart()` 调用 |

---

### trace — 内核 ftrace 追踪

| 项目 | 内容 |
|------|------|
| **功能** | 封装 Linux ftrace 接口，在 init 阶段采集内核跟踪数据，支持 zlib 压缩输出，帮助分析内核级的启动行为 |
| **触发条件** | `debug.hitrace.tags.enableflags` 参数不为 0 |
| **输出文件** | `/data/service/el0/startup/init/init_trace.log`（或 `.zip`） |
| **关键文件** | `init_trace.c`、`init_trace_static.c`、`init_trace.cfg` |
| **注册命令** | `init_trace`（接受 `start`/`stop` 参数） |

---

### udid — 唯一设备 ID 生成

| 项目 | 内容 |
|------|------|
| **功能** | 根据设备硬件特征计算一个 64 字符的十六进制唯一设备标识符（UDID），写入系统参数缓存 |
| **关键文件** | `udid_adp.c`、`udid_comm.c`、`udid_static.c` |
| **钩子点** | `INIT_PRE_CFG_LOAD`（配置文件加载前计算，计算完立即卸载动态模块） |

---

## 4. 完整钩子点参考表

以下是 `bootstage.h` 中定义的所有钩子点，按执行顺序排列：

| 枚举值 | 数值 | 触发时机 | 推荐注册函数 |
|--------|------|----------|--------------|
| `INIT_GLOBAL_INIT` | 0 | init 全局初始化开始 | `InitAddGlobalInitHook(prio, hook)` |
| `INIT_FIRST_STAGE` | 1 | 第一阶段初始化 | `HookMgrAdd(..., INIT_FIRST_STAGE, ...)` |
| `INIT_MOUNT_STAGE` | 3 | 文件系统挂载阶段 | `HookMgrAdd(..., INIT_MOUNT_STAGE, ...)` |
| `INIT_PRE_PARAM_SERVICE` | 10 | 参数服务启动前 | `InitAddPreParamServiceHook(prio, hook)` |
| `INIT_PRE_PARAM_LOAD` | 20 | 参数文件加载前 | `InitAddPreParamLoadHook(prio, hook)` |
| `INIT_PARAM_LOAD_FILTER` | 25 | 参数加载过滤器 | `InitAddParamLoadFilterHook(prio, filter)` |
| `INIT_PRE_CFG_LOAD` | 30 | init.cfg 加载前 | `InitAddPreCfgLoadHook(prio, hook)` |
| `INIT_SERVICE_PARSE` | 35 | 服务配置解析时 | `InitAddServiceParseHook(hook)` |
| `INIT_POST_PERSIST_PARAM_LOAD` | 40 | 持久化参数加载后 | `InitAddPostPersistParamLoadHook(prio, hook)` |
| `INIT_POST_CFG_LOAD` | 50 | init.cfg 加载后 | `InitAddPostCfgLoadHook(prio, hook)` |
| `INIT_CMD_RECORD` | 51 | 每条命令执行时 | `HookMgrAdd(..., INIT_CMD_RECORD, ...)` |
| `INIT_REBOOT` | 55 | 系统重启事件 | `InitAddRebootHook(hook)` |
| `INIT_SERVICE_FORK_BEFORE` | 58 | 服务 fork 之前（父进程） | `InitAddServiceHook(hook, INIT_SERVICE_FORK_BEFORE)` |
| `INIT_SERVICE_SET_PERMS_BEFORE` | 59 | 服务设置权限前（子进程） | `InitAddServiceHook(hook, INIT_SERVICE_SET_PERMS_BEFORE)` |
| `INIT_SERVICE_SET_PERMS` | 60 | 服务权限设置时（子进程） | `InitAddServiceHook(hook, INIT_SERVICE_SET_PERMS)` |
| `INIT_SERVICE_FORK_AFTER` | 61 | 服务 fork 之后（父进程） | `InitAddServiceHook(hook, INIT_SERVICE_FORK_AFTER)` |
| `INIT_SERVICE_REAP` | 65 | 服务退出被回收时 | `HookMgrAdd(..., INIT_SERVICE_REAP, ...)` |
| `INIT_JOB_PARSE` | 70 | Job 配置解析时 | `InitAddJobParseHook(hook)` |
| `INIT_SERVICE_RESTART` | 71 | 服务重启时 | `InitServiceRestartHook(hook, INIT_SERVICE_RESTART)` |
| `INIT_BOOT_COMPLETE` | 100 | 启动完成（`boot` Job 执行完） | `InitAddBootCompleteHook(prio, hook)` |

**优先级（prio）说明**：数字越小，越先执行。0 是最高优先级，同优先级按注册顺序执行。

---

## 5. 可用 API 速查手册

开发模块时常用的 API，来自 `init_module_engine.h`：

```c
// ============================================================
// 头文件（在你的 .c 文件中包含）
// ============================================================
#include "init_module_engine.h"   // 模块引擎主头文件（包含以下所有）
#include "bootstage.h"            // 钩子点枚举和注册函数
#include "plugin_adapter.h"       // PLUGIN_LOGI/LOGE 等日志宏
#include "init_hook.h"            // ServiceExtData API

// ============================================================
// 参数系统
// ============================================================
// 读取系统参数（类似 getprop）
int SystemReadParam(const char *name, char *value, unsigned int *len);
// 写入系统参数（类似 setprop）
int SystemWriteParam(const char *name, const char *value);

// ============================================================
// 钩子注册（常用封装函数）
// ============================================================
int InitAddGlobalInitHook(int prio, OhosHook hook);
int InitAddPreCfgLoadHook(int prio, OhosHook hook);
int InitAddPostCfgLoadHook(int prio, OhosHook hook);
int InitAddPostPersistParamLoadHook(int prio, OhosHook hook);
int InitAddBootCompleteHook(int prio, OhosHook hook);
int InitAddServiceParseHook(ServiceParseHook hook);
int InitAddJobParseHook(JobParseHook hook);
int InitAddServiceHook(ServiceHook hook, int hookState);

// ============================================================
// 命令执行器
// ============================================================
int AddCmdExecutor(const char *cmdName, CmdExecutor execCmd);
void RemoveCmdExecutor(const char *cmdName, int id);

// ============================================================
// 模块管理
// ============================================================
int InitModuleMgrInstall(const char *moduleName);        // 加载 .so
void InitModuleMgrUnInstall(const char *moduleName);     // 卸载 .so
void AutorunModuleMgrUnInstall(const char *moduleName);  // 启动完成后自动卸载

// ============================================================
// Job 执行
// ============================================================
int DoJobNow(const char *jobName);   // 立即触发一个 job

// ============================================================
// 日志宏（来自 plugin_adapter.h）
// ============================================================
PLUGIN_LOGI("格式化字符串 %s", 变量);   // INFO 级别
PLUGIN_LOGE("格式化字符串 %d", 变量);   // ERROR 级别
PLUGIN_LOGW("格式化字符串", ...);       // WARN 级别
PLUGIN_LOGV("格式化字符串", ...);       // VERBOSE 级别（调试用）

// ============================================================
// 服务扩展数据
// ============================================================
ServiceExtData *AddServiceExtData(const char *serviceName, uint32_t id,
                                   void *data, uint32_t dataLen);
ServiceExtData *GetServiceExtData(const char *serviceName, uint32_t id);
void DelServiceExtData(const char *serviceName, uint32_t id);
```

---

## 6. 新模块开发全流程（实战）

我们将开发一个名为 `hello_module` 的示例模块，它的功能是：

1. 在系统启动完成后，向日志输出一条信息
2. 注册一个名为 `hello` 的 init 命令，可以在 `.cfg` 文件中使用

### 6.1 第一步：规划模块

开始写代码前，先回答这几个问题：

| 问题 | 本示例的答案 |
|------|-------------|
| 模块名称是什么？ | `hello_module` |
| 动态 `.so` 的名称？ | `hellomodule` |
| 需要在什么时机执行？ | 启动完成后（`INIT_BOOT_COMPLETE`） |
| 需要注册什么命令？ | `hello` |
| 是否需要静态初始化？ | 是（用于按需加载动态模块） |
| 是否依赖特定系统参数？ | 是：`persist.init.hello.enabled` |

### 6.2 第二步：创建目录和文件

在 `services/modules/` 下创建新目录：

```
services/modules/hello_module/
├── hello_module.c        # 动态模块主逻辑
├── hello_module.h        # 模块内部头文件（可选）
├── hello_module_static.c # 静态初始化文件
└── BUILD.gn              # 构建配置
```

### 6.3 第三步：编写核心逻辑

**文件：`hello_module.c`**

```c
/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * ...
 */

// ★ 必须包含的头文件
#include "init_module_engine.h"
#include "bootstage.h"
#include "plugin_adapter.h"

// ============================================================
// 命令处理函数
// 当 init.cfg 中执行 "hello <name>" 时被调用
// ============================================================
static int HelloCmdHandler(int id, const char *name, int argc, const char **argv)
{
    // 不用 id 和 name，用 UNUSED 宏消除编译警告
    UNUSED(id);
    UNUSED(name);

    if (argc < 1) {
        // PLUGIN_LOGE 相当于带标签的 printf，会输出到 /dev/kmsg
        PLUGIN_LOGE("hello: missing argument. Usage: hello <name>");
        return -1; // 返回非 0 表示失败
    }

    PLUGIN_LOGI("Hello, %s! Module is working.", argv[0]);
    return 0; // 返回 0 表示成功
}

// ============================================================
// 启动完成钩子处理函数
// ============================================================
static int OnBootComplete(const HOOK_INFO *hookInfo, void *cookie)
{
    // 这两个参数在本例中不使用
    UNUSED(hookInfo);
    UNUSED(cookie);

    PLUGIN_LOGI("[hello_module] System boot completed! Everything is ready.");

    // 可以在这里做一些"启动完成后"才能做的事
    // 例如：读取系统参数，写入状态，通知其他进程...
    char productModel[64] = {0};
    unsigned int len = sizeof(productModel);
    int ret = SystemReadParam("const.product.model", productModel, &len);
    if (ret == 0) {
        PLUGIN_LOGI("[hello_module] Running on device: %s", productModel);
    }

    return 0;
}

// ============================================================
// MODULE_CONSTRUCTOR：模块的"入口函数"
// 当 .so 被 dlopen() 加载时自动调用
// ============================================================
MODULE_CONSTRUCTOR(void)
{
    PLUGIN_LOGI("[hello_module] Module loaded, registering hooks...");

    // 注册启动完成钩子
    InitAddBootCompleteHook(0, OnBootComplete);

    // 注册 "hello" 命令，使其可在 .cfg 文件中使用
    AddCmdExecutor("hello", HelloCmdHandler);
}

// ============================================================
// MODULE_DESTRUCTOR：模块的"清理函数"（可选）
// 当 .so 被卸载时调用
// ============================================================
MODULE_DESTRUCTOR(void)
{
    PLUGIN_LOGI("[hello_module] Module unloaded.");
    // 如果有分配的资源，在这里释放
    // 如果注册了命令，可以在这里注销（通常不需要）
}
```

### 6.4 第四步：编写静态初始化文件

**文件：`hello_module_static.c`**

静态文件的职责：检查是否应该加载动态模块，如果是则加载它。

```c
/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * ...
 */

// ★ 静态文件只需包含这三个头文件
#include "init_module_engine.h"
#include "plugin_adapter.h"
#include "init_hook.h"    // 如果用到 InitAdd*Hook 系列函数则需要

// ============================================================
// 早期钩子：检查参数，决定是否加载动态模块
// 在持久化参数加载完成后执行，此时可以读取 persist. 参数
// ============================================================
static int HelloModuleEarlyHook(const HOOK_INFO *hookInfo, void *cookie)
{
    UNUSED(hookInfo);
    UNUSED(cookie);

    // 读取开关参数
    char enable[8] = {0};
    unsigned int len = sizeof(enable);
    SystemReadParam("persist.init.hello.enabled", enable, &len);

    if (strcmp(enable, "1") != 0 && strcmp(enable, "true") != 0) {
        PLUGIN_LOGI("[hello_module] disabled by param, skip loading.");
        return 0; // 参数未开启，不加载动态模块
    }

    // 参数开启，加载动态模块
    // "hellomodule" 对应 /system/lib64/init/hellomodule.so
    PLUGIN_LOGI("[hello_module] enabled, installing dynamic module...");
    InitModuleMgrInstall("hellomodule");
    return 0;
}

// ============================================================
// 静态模块的 MODULE_CONSTRUCTOR
// 在 init 启动时立即执行（比动态模块更早）
// ============================================================
MODULE_CONSTRUCTOR(void)
{
    // 注册钩子：等持久化参数加载完后，再检查是否需要加载动态模块
    // 因为参数 persist.* 只有加载后才能读取
    InitAddPostPersistParamLoadHook(0, HelloModuleEarlyHook);
}
```

> **为什么选 `INIT_POST_PERSIST_PARAM_LOAD`？**
> 因为我们需要读取 `persist.init.hello.enabled` 参数，而 `persist.*` 前缀的参数
> 是在持久化参数加载步骤（`load_persist_params`）之后才能读到的。
> 如果不需要读参数，可以选更早的 `INIT_GLOBAL_INIT` 或 `INIT_PRE_CFG_LOAD`。

### 6.5 第五步：编写 BUILD.gn 构建配置

**文件：`BUILD.gn`**

> BUILD.gn 是 OpenHarmony 的构建描述文件，类似于 CMakeLists.txt，告诉构建系统如何编译这个模块。

```python
# Copyright (c) 2024 Huawei Device Co., Ltd.
# Licensed under the Apache License, Version 2.0 (the "License");
# ...

# 导入必要的构建模板
import("//base/startup/init/begetd.gni")   # init 项目的公共变量
import("//build/ohos.gni")                  # OpenHarmony 标准构建模板

# ============================================================
# 动态模块：编译成 hellomodule.so
# 安装路径：/system/lib64/init/hellomodule.so（64位）
#           /system/lib/init/hellomodule.so（32位）
# ============================================================
ohos_shared_library("hellomodule") {
  # 源文件列表
  sources = [ "hello_module.c" ]

  # 头文件搜索路径
  include_dirs = [
    ".",                              # 当前目录（hello_module.h）
    "..",                             # 父目录（可以包含其他模块的头文件）
    "//base/startup/init/interfaces/innerkits/include/param",
  ]

  # 本项目内部依赖
  deps = [
    # 必须依赖 init_module_engine，它提供了所有插件 API
    "//base/startup/init/interfaces/innerkits/init_module_engine:libinit_module_engine",
  ]

  # 外部组件依赖（其他子系统提供的库）
  external_deps = [
    "bounds_checking_function:libsec_shared",  # 安全函数库（strcpy_s 等）
  ]

  # 组件归属信息（固定填 init/startup）
  part_name = "init"
  subsystem_name = "startup"

  # 安装目录：根据 CPU 架构自动选择 lib64 或 lib
  if (target_cpu == "arm64" || target_cpu == "x86_64" || target_cpu == "riscv64") {
    module_install_dir = "lib64/init"
  } else {
    module_install_dir = "lib/init"
  }
}

# ============================================================
# 静态模块配置块
# 用于让父 BUILD.gn 能引用这个 static 编译目标
# ============================================================
config("libhello_module_static_config") {
  include_dirs = [
    ".",
    "..",
  ]
}

# ============================================================
# 静态模块：编译成 .a 静态库，链接进 init 可执行文件
# ============================================================
ohos_source_set("libhello_module_static") {
  sources = [ "hello_module_static.c" ]

  # 对外暴露头文件搜索路径
  public_configs = [ ":libhello_module_static_config" ]

  # 导出 init_module_engine 的公共配置（被链接者需要这些头文件）
  public_configs += [
    "//base/startup/init/interfaces/innerkits/init_module_engine:init_module_engine_exported_config",
  ]

  external_deps = [
    "bounds_checking_function:libsec_shared",
  ]

  part_name = "init"
  subsystem_name = "startup"
}
```

### 6.6 第六步：注册到父目录 BUILD.gn

**修改文件：`services/modules/BUILD.gn`**

在两个 `group` 中分别添加你的模块：

```python
group("static_modules") {
  if (!defined(ohos_lite)) {
    deps = [
      "bootchart:libbootchart_static",
      "bootevent:libbootevent_static",
      "init_context:initcontext_static",
      "init_eng:libiniteng_static",
      "init_hook:inithook",
      "reboot:libreboot_static",
      "trace:inittrace_static",
      "udid:libudid_static",
      "hello_module:libhello_module_static",   # ← 添加这一行
    ]
    # ...（保留原有的 if 条件块）
  }
}

group("modulesgroup") {
  if (!defined(ohos_lite)) {
    deps = [
      "bootchart:bootchart",
      "init_context:init_context",
      "init_eng:init_eng",
      "module_update:module_update_init",
      "reboot:rebootmodule",
      "sysevent:eventmodule",
      "trace:inittrace",
      "udid:udidmodule",
      "hello_module:hellomodule",              # ← 添加这一行
    ]
    # ...（保留原有的 if 条件块）
  }
}
```

---

## 7. 常见开发场景与代码模板

### 7.1 场景一：在启动时执行一次性任务

**适用钩子**：`INIT_PRE_CFG_LOAD`（配置加载前）或 `INIT_BOOT_COMPLETE`（启动完成）

```c
static int MyStartupTask(const HOOK_INFO *hookInfo, void *cookie)
{
    UNUSED(hookInfo);
    UNUSED(cookie);

    // 在这里执行你的一次性任务
    PLUGIN_LOGI("Performing startup task...");

    // 示例：写入系统参数
    SystemWriteParam("my.module.status", "initialized");

    // 执行完后，如果是动态加载的模块，可以选择卸载自身
    // InitModuleMgrUnInstall("mymodule");

    return 0;
}

MODULE_CONSTRUCTOR(void)
{
    // 在配置文件加载前执行
    InitAddPreCfgLoadHook(0, MyStartupTask);
}
```

### 7.2 场景二：注册新的 init.cfg 命令

**需求**：在 `init.cfg` 中能写 `write_status <key> <value>`。

```c
// 命令处理函数
static int WriteStatusCmd(int id, const char *name, int argc, const char **argv)
{
    UNUSED(id);
    UNUSED(name);

    // 参数校验：需要 2 个参数
    if (argc < 2) {
        PLUGIN_LOGE("write_status: Usage: write_status <key> <value>");
        return -1;
    }

    const char *key   = argv[0];
    const char *value = argv[1];

    PLUGIN_LOGI("write_status: setting %s = %s", key, value);
    int ret = SystemWriteParam(key, value);
    if (ret != 0) {
        PLUGIN_LOGE("write_status: failed to write param %s, ret=%d", key, ret);
        return -1;
    }

    return 0;
}

// 需要在参数服务初始化后才能注册命令
static int RegisterCmdsHook(const HOOK_INFO *hookInfo, void *cookie)
{
    UNUSED(hookInfo);
    UNUSED(cookie);
    AddCmdExecutor("write_status", WriteStatusCmd);
    return 0;
}

MODULE_CONSTRUCTOR(void)
{
    // INIT_GLOBAL_INIT 阶段注册命令
    InitAddGlobalInitHook(0, RegisterCmdsHook);
}
```

之后就可以在任意 `.cfg` 文件中使用：

```json
{
    "name": "post-fs-data",
    "cmds": [
        "write_status my.app.data_ready true"
    ]
}
```

### 7.3 场景三：监听服务的启动/停止事件

**需求**：每当有服务启动后，打印一条日志。

```c
// ServiceHook 的签名是固定的
static void OnServiceStarted(SERVICE_INFO_CTX *serviceCtx)
{
    if (serviceCtx == NULL) return;
    PLUGIN_LOGI("Service started: %s", serviceCtx->serviceName);

    // 你可以根据服务名做不同的处理
    if (strcmp(serviceCtx->serviceName, "appspawn") == 0) {
        PLUGIN_LOGI("appspawn is ready, apps can now be launched!");
        SystemWriteParam("my.appspawn.ready", "1");
    }
}

static void OnServiceStopped(SERVICE_INFO_CTX *serviceCtx)
{
    if (serviceCtx == NULL) return;
    PLUGIN_LOGW("Service stopped: %s", serviceCtx->serviceName);
}

MODULE_CONSTRUCTOR(void)
{
    // INIT_SERVICE_FORK_AFTER：服务 fork 成功后（父进程中）
    InitAddServiceHook(OnServiceStarted, INIT_SERVICE_FORK_AFTER);

    // INIT_SERVICE_REAP：服务退出被 init 回收后
    HookMgrAdd(GetBootStageHookMgr(), INIT_SERVICE_REAP, 0,
        (OhosHook)OnServiceStopped);
}
```

> **注意**：`ServiceHook` 的函数签名是 `void (*)(SERVICE_INFO_CTX *)` （无返回值），而 `OhosHook` 的签名是 `int (*)(const HOOK_INFO *, void *)` 。使用 `InitAddServiceHook()` 还是 `HookMgrAdd()` 取决于具体钩子点。查看 `bootstage.h` 中各 `InitAdd*` 函数的签名来确认。

### 7.4 场景四：解析服务配置中的自定义字段

**需求**：允许在服务配置文件中添加一个 `"my_priority"` 字段，并读取它的值。

```c
#include "init_hook.h"
#include "cJSON.h"

// 自定义数据的 ID（选一个不与现有模块冲突的值）
#define HOOK_ID_MY_MODULE 0x12345678

// 存储自定义数据的结构
typedef struct {
    int priority;
} MyModuleServiceData;

// 服务解析钩子：在 init 解析服务 JSON 时被调用
static void ParseMyServiceField(SERVICE_PARSE_CTX *ctx)
{
    if (ctx == NULL || ctx->serviceNode == NULL) return;

    // 从 JSON 节点读取 "my_priority" 字段
    cJSON *priorityNode = cJSON_GetObjectItem(ctx->serviceNode, "my_priority");
    if (priorityNode == NULL || !cJSON_IsNumber(priorityNode)) {
        return; // 没有这个字段，跳过
    }

    MyModuleServiceData data;
    data.priority = priorityNode->valueint;

    PLUGIN_LOGI("Service %s has my_priority = %d",
                ctx->serviceName, data.priority);

    // 将数据附加到服务上，以便后续钩子使用
    AddServiceExtData(ctx->serviceName, HOOK_ID_MY_MODULE, &data, sizeof(data));
}

// 在服务启动前读取自定义数据
static void UseMyServiceData(SERVICE_INFO_CTX *serviceCtx)
{
    if (serviceCtx == NULL) return;

    ServiceExtData *extData = GetServiceExtData(
        serviceCtx->serviceName, HOOK_ID_MY_MODULE);
    if (extData == NULL) return;

    MyModuleServiceData *data = (MyModuleServiceData *)extData->data;
    PLUGIN_LOGI("Service %s will start with priority %d",
                serviceCtx->serviceName, data->priority);
}

MODULE_CONSTRUCTOR(void)
{
    InitAddServiceParseHook(ParseMyServiceField);
    InitAddServiceHook(UseMyServiceData, INIT_SERVICE_FORK_BEFORE);
}
```

配置文件中这样使用：

```json
{
    "services": [{
        "name": "my_service",
        "path": ["/system/bin/my_service"],
        "my_priority": 5
    }]
}
```

### 7.5 场景五：通过系统参数控制模块开关

这是 bootchart 模块使用的标准模式：

**静态文件（`*_static.c`）**：

```c
static int CheckEnableAndLoad(const HOOK_INFO *hookInfo, void *cookie)
{
    UNUSED(hookInfo);
    UNUSED(cookie);

    char enable[8] = {0};
    unsigned int len = sizeof(enable);
    SystemReadParam("persist.init.mymodule.enabled", enable, &len);

    if (strcmp(enable, "1") == 0 || strcmp(enable, "true") == 0) {
        PLUGIN_LOGI("mymodule: enabled, loading...");
        InitModuleMgrInstall("mymodule");     // 加载 mymodule.so
    } else {
        PLUGIN_LOGI("mymodule: disabled.");
    }
    return 0;
}

MODULE_CONSTRUCTOR(void)
{
    // 等 persist.* 参数加载完后再检查
    InitAddPostPersistParamLoadHook(0, CheckEnableAndLoad);
}
```

**动态文件（`*_main.c`）**：正常实现功能逻辑即可。

**使用方式**：

```bash
# 开启模块（重启后生效）
begetctl param set persist.init.mymodule.enabled 1

# 关闭模块
begetctl param set persist.init.mymodule.enabled 0
```

---

## 8. 调试与日志使用

### 日志宏说明

所有日志宏来自 `plugin_adapter.h`（即使该文件不存在于你能找到的路径，也会通过编译系统自动提供）：

```c
PLUGIN_LOGI("这是信息日志: %s", someString);   // INFO
PLUGIN_LOGW("这是警告日志: %d", someInt);       // WARN
PLUGIN_LOGE("这是错误日志: %s", errorMsg);      // ERROR
PLUGIN_LOGV("这是调试日志");                    // VERBOSE（调试构建才输出）
```

日志会写入 `/dev/kmsg`，可通过以下方式查看：

```bash
# 方法 1：开机后查看内核日志（包含 init 日志）
dmesg | grep "\[hello_module\]"

# 方法 2：使用 hilog 查看
hilog | grep "hello_module"

# 方法 3：直接查看 init 日志文件（如果存在）
cat /data/service/el0/startup/init/init.log
```

### 常用调试技巧

**1. 验证模块是否被加载**：

```bash
# 检查 .so 文件是否存在
ls /system/lib64/init/

# 检查 init 进程加载的库（运行时）
cat /proc/1/maps | grep hellomodule
```

**2. 用参数控制调试级别**：

```bash
# 提高 init 日志级别到 DEBUG（VERBOSE 可见）
begetctl param set persist.init.debug.loglevel 1
```

**3. 验证命令是否注册成功**：

在 `init.cfg` 的任一 job 中加入你的命令，然后查看 init 日志是否有对应输出。

---

## 9. 完整示例：hello_module

下面是所有文件的完整可用代码：

### 目录结构

```
services/modules/hello_module/
├── hello_module.c
├── hello_module_static.c
└── BUILD.gn
```

### hello_module.c（动态模块）

```c
/*
 * Copyright (c) 2024 Your Name.
 * Licensed under the Apache License, Version 2.0.
 */
#include "init_module_engine.h"
#include "bootstage.h"
#include "plugin_adapter.h"

static int HelloCmdHandler(int id, const char *name, int argc, const char **argv)
{
    UNUSED(id);
    UNUSED(name);
    if (argc < 1) {
        PLUGIN_LOGE("[hello_module] Usage: hello <name>");
        return -1;
    }
    PLUGIN_LOGI("[hello_module] Hello, %s!", argv[0]);
    return 0;
}

static int OnBootComplete(const HOOK_INFO *hookInfo, void *cookie)
{
    UNUSED(hookInfo);
    UNUSED(cookie);
    PLUGIN_LOGI("[hello_module] Boot complete! All services started.");

    char model[64] = {0};
    unsigned int len = sizeof(model);
    if (SystemReadParam("const.product.model", model, &len) == 0) {
        PLUGIN_LOGI("[hello_module] Device model: %s", model);
    }
    SystemWriteParam("my.hello.status", "boot_complete");
    return 0;
}

MODULE_CONSTRUCTOR(void)
{
    PLUGIN_LOGI("[hello_module] Dynamic module loaded.");
    InitAddBootCompleteHook(0, OnBootComplete);
    AddCmdExecutor("hello", HelloCmdHandler);
}

MODULE_DESTRUCTOR(void)
{
    PLUGIN_LOGI("[hello_module] Dynamic module unloaded.");
}
```

### hello_module_static.c（静态模块）

```c
/*
 * Copyright (c) 2024 Your Name.
 * Licensed under the Apache License, Version 2.0.
 */
#include "init_module_engine.h"
#include "plugin_adapter.h"

static int HelloModuleEarlyHook(const HOOK_INFO *hookInfo, void *cookie)
{
    UNUSED(hookInfo);
    UNUSED(cookie);

    char enable[8] = {0};
    unsigned int len = sizeof(enable);
    SystemReadParam("persist.init.hello.enabled", enable, &len);

    if (strcmp(enable, "1") == 0 || strcmp(enable, "true") == 0) {
        PLUGIN_LOGI("[hello_module] Enabled, installing hellomodule...");
        InitModuleMgrInstall("hellomodule");
    } else {
        PLUGIN_LOGI("[hello_module] Not enabled (set persist.init.hello.enabled=1 to enable).");
    }
    return 0;
}

MODULE_CONSTRUCTOR(void)
{
    InitAddPostPersistParamLoadHook(0, HelloModuleEarlyHook);
}
```

### BUILD.gn

```python
# Copyright (c) 2024 Your Name.
# Licensed under the Apache License, Version 2.0.

import("//base/startup/init/begetd.gni")
import("//build/ohos.gni")

ohos_shared_library("hellomodule") {
  sources = [ "hello_module.c" ]
  include_dirs = [
    ".",
    "..",
    "//base/startup/init/interfaces/innerkits/include/param",
  ]
  deps = [
    "//base/startup/init/interfaces/innerkits/init_module_engine:libinit_module_engine",
  ]
  external_deps = [ "bounds_checking_function:libsec_shared" ]
  part_name = "init"
  subsystem_name = "startup"
  if (target_cpu == "arm64" || target_cpu == "x86_64" || target_cpu == "riscv64") {
    module_install_dir = "lib64/init"
  } else {
    module_install_dir = "lib/init"
  }
}

config("libhello_module_static_config") {
  include_dirs = [ ".", ".." ]
}

ohos_source_set("libhello_module_static") {
  sources = [ "hello_module_static.c" ]
  public_configs = [ ":libhello_module_static_config" ]
  public_configs += [
    "//base/startup/init/interfaces/innerkits/init_module_engine:init_module_engine_exported_config",
  ]
  external_deps = [ "bounds_checking_function:libsec_shared" ]
  part_name = "init"
  subsystem_name = "startup"
}
```

### 验证步骤

```bash
# 1. 开启模块
begetctl param set persist.init.hello.enabled 1
# 重启设备使 persist 参数生效

# 2. 查看日志
hilog | grep hello_module

# 3. 验证参数是否被写入
begetctl param get my.hello.status
# 期望输出: boot_complete

# 4. 在 init.cfg 中使用 hello 命令（添加到任意 job 的 cmds 中）
# "hello OpenHarmony"
# 重启后查看日志: [hello_module] Hello, OpenHarmony!
```

---

## 10. 常见错误与排查

| 错误现象 | 可能原因 | 排查方法 |
|----------|----------|----------|
| 模块根本没有日志输出 | 静态文件没有加入 `BUILD.gn` 的 `static_modules` group，或模块没有被加载 | 检查 `services/modules/BUILD.gn` 是否添加了引用；检查 `InitModuleMgrInstall` 是否被调用 |
| `MODULE_CONSTRUCTOR` 执行了，但动态模块的钩子没有执行 | 动态 `.so` 没有安装到正确路径 | `ls /system/lib64/init/` 确认 `.so` 存在；检查 `module_install_dir` 配置 |
| `SystemReadParam` 始终读到空字符串 | 读取 `persist.*` 参数时用的钩子点太早（参数还未加载） | 改用 `INIT_POST_PERSIST_PARAM_LOAD` 钩子点 |
| 命令注册了，但 `.cfg` 中用时报"未知命令" | 命令注册的时机太晚（cfg 解析时命令还不存在）；或命令名拼写不一致 | 在 `INIT_GLOBAL_INIT` 钩子中注册命令（越早越好） |
| 编译报错：`undefined reference to 'InitAddBootCompleteHook'` | 没有在 `BUILD.gn` 的 `deps` 中添加 `libinit_module_engine` | 确认 `deps` 列表包含正确的依赖路径 |
| 编译报错：`PLUGIN_LOGI` 未定义 | 没有包含 `plugin_adapter.h` | 添加 `#include "plugin_adapter.h"` |
| 服务扩展数据返回 `NULL` | 服务名拼写错误，或服务尚未注册 | 确认 `serviceName` 完全匹配 `.cfg` 中的 `"name"` 字段 |

---

## 11. 参考资料

### 项目内关键文件

| 文件路径 | 说明 |
|----------|------|
| `interfaces/innerkits/init_module_engine/include/bootstage.h` | ★ 所有钩子点枚举和注册函数声明 |
| `interfaces/innerkits/init_module_engine/include/init_module_engine.h` | ★ 模块引擎主头文件（参数、命令、模块管理） |
| `interfaces/innerkits/init_module_engine/include/init_running_hooks.h` | 运行时钩子（参数 set 钩子） |
| `services/modules/init_hook/init_hook.h` | `ServiceExtData` API 声明 |
| `services/modules/init_hook/init_hook.c` | `ServiceExtData` 实现 + `init_hook` 自身钩子注册 |
| `services/modules/udid/udid_static.c` | ★ 最简单的静态模块示例 |
| `services/modules/bootchart/bootchart_static.c` | ★ 参数控制开关的静态模块示例 |
| `services/modules/reboot/reboot_static.c` | 复杂静态模块示例（含命令注册和 HookMgr 详细用法） |
| `services/modules/BUILD.gn` | ★ 父目录构建文件（新模块必须在这里注册） |

### 官方文档

| 资料 | 链接 |
|------|------|
| init 子系统服务开发文档 | https://docs.openharmony.cn/pages/v4.0/zh-cn/device-dev/subsystems/subsys-boot-init-service.md |
| init 插件开发文档 | https://docs.openharmony.cn/pages/v4.0/zh-cn/device-dev/subsystems/subsys-boot-init-plugin.md |
| GN 构建系统使用指南 | https://docs.openharmony.cn/pages/v4.0/zh-cn/device-dev/subsystems/subsys-build-reference.md |
| OpenHarmony 参数系统 | https://docs.openharmony.cn/pages/v4.0/zh-cn/device-dev/subsystems/subsys-boot-syspara.md |

### C 语言基础补充

| 概念 | 说明 |
|------|------|
| `__attribute__((constructor))` | GCC 特性，被标记的函数在程序启动或 `.so` 加载时自动调用，`MODULE_CONSTRUCTOR` 宏就是对它的封装 |
| `dlopen` / `dlsym` | Linux 动态库加载 API，`InitModuleMgrInstall` 内部使用这两个函数加载 `.so` |
| `UNUSED(x)` | 宏，展开为 `(void)(x)`，用于消除"未使用参数"的编译警告 |
| `cJSON` | 轻量级 JSON 解析库，用于解析服务配置节点。`cJSON_GetObjectItem(node, "key")` 读取字段 |

---

*文档基于源码 `D:\projects\startup_init` 分析生成 · 2026-03-02*
