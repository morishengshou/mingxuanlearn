# dex2oat 开发指导文档（Android 12 / ART）

> 面向系统开发新手。目标：在你没有 dex2oat 背景的情况下，建立对它的整体认知，并能动手定位"dex2oat 挂死"问题。
> 文档中所有源码引用均来自本机 `D:\Android12\art\dex2oat`，格式为 `文件:行号`，可直接跳转。

---

## 目录

1. [先建立全局认知：dex2oat 是什么](#1-先建立全局认知dex2oat-是什么)
2. [读懂 dex2oat 代码的步骤（学习路径）](#2-读懂-dex2oat-代码的步骤学习路径)
3. [源码目录结构](#3-源码目录结构)
4. [完整执行流程（从 main 到产物落盘）](#4-完整执行流程从-main-到产物落盘)
5. [核心子系统详解](#5-核心子系统详解)
6. [WatchDog 看门狗机制（与"挂死"强相关）](#6-watchdog-看门狗机制与挂死强相关)
7. [挂死问题分析方法](#7-挂死问题分析方法)
8. [维测日志：加在哪、怎么加、如何不影响性能](#8-维测日志加在哪怎么加如何不影响性能)
9. [华为设备专项（EMUI/Kirin）](#9-华为设备专项emuikirin)
10. [参考资料](#10-参考资料)

---

## 1. 先建立全局认知：dex2oat 是什么

### 1.1 一句话定义

**dex2oat 是 ART 的 AOT（Ahead-Of-Time，提前编译）编译器**：它把 APK/jar 里的 `.dex` 字节码，**提前**编译成目标 CPU（arm64 等）的本地机器码，输出 `.oat`/`.odex` 文件，让 App 运行时不必每次都解释执行或 JIT，从而加快启动、提升运行性能。

可以这样类比：
- `.dex` = Java 源码编译后的"中间字节码"（给虚拟机看的）
- `dex2oat` = 把字节码再"翻译"成 CPU 能直接跑的机器码的工具
- `.oat`（封装在 ELF `.so` 里）= 翻译后的成品

> 概念补充：什么是 AOT / JIT / 解释执行，三者关系，建议先读：
> - ART 与 Dalvik 概览（官方）：https://source.android.com/docs/core/runtime
> - ART 配置与编译选项：https://source.android.com/docs/core/runtime/configure

### 1.2 dex2oat 在系统里何时被调用（这对定位挂死很重要）

dex2oat 是一个**独立可执行程序**（`/apex/com.android.art/bin/dex2oat64`），它不是被你直接调用的，而是被系统在这些时机 `fork+exec` 起来：

| 触发时机 | 调用方 | 典型场景 |
|---------|--------|---------|
| 应用安装/更新 | `installd`（`PackageManagerService` 通过它） | 装 APK 时做 dexopt |
| 系统升级后首次开机 | `installd` / OTA 脚本 | 开机时批量编译，**最容易"挂"且最显眼** |
| 空闲时后台优化 | `dexopt` / `BackgroundDexOptService` | 充电+空闲时按 profile 重编译 |
| 首次启动构建 boot image | zygote 前置流程 | 编译 boot.art / boot.oat |

> 你遇到的"频繁挂死"，先确认是**哪个场景**触发的（开机批量 dexopt？还是装应用？）。
> 调用参数（命令行）是定位第一手资料，见 [第 7 节](#7-挂死问题分析方法)。

> 参考：installd 与 dexopt 调用关系
> - `frameworks/native/cmds/installd/dexopt.cpp`（调用 dex2oat 的地方，不在 art 仓库内）
> - dexopt 总览：https://source.android.com/docs/core/runtime/configure#how_app_compilation_works

### 1.3 dex2oat 的几种产物

| 产物 | 是什么 | 由谁写出 |
|------|--------|---------|
| `.oat` / `.odex` | 编译后的机器码 + 元数据，封装成 ELF | `OatWriter` + `ElfWriter` |
| `.vdex` | 校验过的 dex + 校验结果（verifier deps），避免下次重复 verify | `Setup`/vdex 流程 |
| `.art`（boot.art / app image） | 预初始化好的对象堆镜像，加速加载 | `ImageWriter` |

---

## 2. 读懂 dex2oat 代码的步骤（学习路径）

按这个顺序走，可以从"完全不懂"到"能改代码"。**不要一上来逐行读 3000 行的 `dex2oat.cc`**。

### 第 0 步：跑通认知（半天）
- 读 1.1 ~ 1.3，理解输入输出。
- 在真机上抓一条真实命令行（见 7.1），知道它实际被喂了什么参数。

### 第 1 步：抓主干（1 天）
只看"控制流主线"，忽略所有细节分支：
1. `main()` → `dex2oat.cc:3182`
2. `Dex2oat()` → `dex2oat.cc:3089`（整个生命周期都在这）
3. `DoCompilation()` → `dex2oat.cc:3042`（编译+落盘的高层步骤）

把这三段当成"目录"读，先记住**阶段顺序**：
```
ParseArgs → OpenFile → Setup → DoCompilation(Compile → WriteOutputFiles → HandleImage)
```

### 第 2 步：逐阶段深入（2~3 天）
对每个阶段，找到对应方法读一遍，只问三个问题：**输入是什么 / 干了什么 / 失败或卡住会怎样**：
- `ParseArgs` → 参数解析（`dex2oat_options.cc` / `.def`）
- `Setup()` → `dex2oat.cc:1415`（建 Runtime、打开 dex、装 watchdog）
- `Compile()` → `dex2oat.cc:1831`（**核心，CPU 密集，挂死高发**）
- `WriteOutputFiles()` → `dex2oat.cc:2052`（**I/O 密集，挂死高发**）
- `HandleImage()` → `dex2oat.cc:2207`

### 第 3 步：钻并行与线程模型（2 天，定位挂死必读）
- `CompilerDriver::CompileAll` → `compiler_driver.cc:335`
- `CompilerDriver::PreCompile`（Resolve/Verify/Initialize）→ `compiler_driver.cc:762`
- `ParallelCompilationManager` + `ForAllLambda` → `compiler_driver.cc:1352`（线程池如何分发任务、如何 `Wait`）
- `ThreadPool`（不在 dex2oat 目录，在 `art/runtime/thread_pool.{h,cc}`）

### 第 4 步：看门狗与异常路径（半天，本任务重点）
- `WatchDog` 类 → `dex2oat.cc:280`
- 理解超时后 `Fatal()` → `exit(1)` 的逻辑（`dex2oat.cc:357`）

### 第 5 步：建立"卡点地图"
把所有**可能阻塞**的点列出来（锁、I/O、线程 join、网络/IPC、GC）。本文第 7、8 节已经帮你列好。

> 读码工具建议：用支持"跳转定义/查找引用"的编辑器（VS Code + clangd，或 Android Studio）。
> AOSP 在线代码搜索（强烈推荐，能跨仓库跳转）：https://cs.android.com/

---

## 3. 源码目录结构

`D:\Android12\art\dex2oat` 主要内容：

```
dex2oat/
├── dex2oat.cc              # 【主入口】main、Dex2Oat 类、WatchDog、全流程编排 (3191 行)
├── dex2oat_options.def     # 命令行选项的声明表（用宏定义所有 --xxx 选项）
├── dex2oat_options.{h,cc}  # 选项解析实现
├── driver/
│   ├── compiler_driver.{h,cc}   # 【编译总调度】驱动 resolve/verify/compile，管理线程池 (2796 行)
│   └── compiler_driver-inl.h
├── linker/
│   ├── oat_writer.{h,cc}        # 【写 .oat】把编译结果序列化进 oat (4092 行)
│   ├── image_writer.{h,cc}      # 【写 .art】生成对象堆镜像 (3554 行)
│   ├── elf_writer*.{h,cc}       # 把 oat 封装成 ELF(.so)
│   └── relative_patcher*        # 机器码里相对地址的回填(patch)
├── dex/
│   └── quick_compiler_callbacks.{h,cc}  # 编译期回调（verify 结果等）
└── *_test.cc                # 各种单元测试（读测试是理解用法的捷径）
```

**给新手的阅读优先级**：`dex2oat.cc` ≫ `compiler_driver.cc` ≫ `oat_writer.cc`/`image_writer.cc`（后两个先了解职责即可，不必逐行）。

> 真正"把一个方法编译成机器码"的优化器/代码生成在 **`art/compiler/`** 目录（不在 dex2oat 下），由 `compiler_driver` 调过去。如果挂死发生在编译单个方法上，最终要往那里查。

---

## 4. 完整执行流程（从 main 到产物落盘）

下面是把上面读到的代码串起来的**主线时序**（括号是源码位置）：

```
main()                                              dex2oat.cc:3182
└─ Dex2oat(argc, argv)                              dex2oat.cc:3089
   ├─ ParseArgs()                                   解析命令行；在此创建 WatchDog (dex2oat.cc:843)
   ├─ MemMap::Init()
   ├─ LoadProfile()           (若有 profile)        读取 profile，决定哪些方法重点编译
   ├─ UpdateCompilerOptionsBasedOnProfile()         按 profile 调整编译过滤器(filter)
   ├─ OpenFile()                                    dex2oat.cc:1178  打开 oat/vdex/image 输出文件
   ├─ Setup()                                       dex2oat.cc:1415  建 Runtime、打开输入 dex、AddDexFileSources
   ├─ VerifyProfileData()     (若有 profile)
   └─ DoCompilation(dex2oat)                         dex2oat.cc:3042
      ├─ LoadClassProfileDescriptors()
      ├─ Compile()  ──► 返回 class_loader            dex2oat.cc:1831   【CPU 密集核心】
      │   └─ CompileDexFiles()                       dex2oat.cc:1932
      │       ├─ driver_->InitializeThreadPools()
      │       ├─ driver_->PreCompile()               compiler_driver.cc:762
      │       │    ├─ LoadImageClasses
      │       │    ├─ Resolve        (并行)          compiler_driver.cc:522
      │       │    ├─ Verify         (并行)          compiler_driver.cc:1811
      │       │    └─ InitializeClasses
      │       ├─ driver_->CompileAll()               compiler_driver.cc:335  → Compile 每个方法(并行)
      │       └─ driver_->FreeThreadPools()
      ├─ WriteOutputFiles(class_loader)              dex2oat.cc:2052   【I/O 密集】OatWriter/ElfWriter
      ├─ FlushOutputFiles()                          落盘
      ├─ HandleImage()                               dex2oat.cc:2207   生成 boot.art/app image
      ├─ CopyOatFilesToSymbolsDirectoryAndStrip()    strip 符号(target)
      └─ DumpTiming()                                打印各阶段耗时（重要！见第8节）
```

落盘后 `main()` 会调用 `FastExit()`（`dex2oat.cc:3187`）**直接退出进程**，故意跳过 Runtime 析构以省时间（这也是为什么有些资源不"优雅释放"）。

### 阶段职责速记表

| 阶段 | 主要工作 | 资源特征 | 挂死风险点 |
|------|---------|---------|-----------|
| ParseArgs | 解析参数、起看门狗 | 轻 | 低 |
| OpenFile / Setup | 打开文件、建 Runtime、读 dex | I/O + 内存 | 文件锁、坏 vdex |
| Resolve | 解析类/方法/字段符号引用 | CPU + 锁 | 线程池死锁 |
| Verify | 校验字节码合法性 | CPU + 锁 | 类加载死锁、死循环 |
| CompileAll | 逐方法生成机器码 | **CPU 密集** | 大方法编译爆炸、内存不足触发疯狂 GC/swap |
| WriteOutputFiles | 序列化 oat / ELF | **I/O 密集** | 磁盘满、I/O 卡住、文件锁 |
| HandleImage | 写 image | I/O + 内存 | 内存不足 |

---

## 5. 核心子系统详解

### 5.1 Dex2Oat 类（dex2oat.cc:505）

把整个编译任务的状态都装在这个类里：输入 dex、输出文件句柄、编译选项 `compiler_options_`、`CompilerDriver driver_`、`WatchDog watchdog_` 等。流程函数（`Setup`/`Compile`/`WriteOutputFiles`…）都是它的成员。**它就是 dex2oat 的"主对象"**。

### 5.2 CompilerDriver（driver/compiler_driver.cc）—— 编译总调度

它不亲自生成机器码，而是**调度**整个编译：
- `PreCompile()`（:762）：按顺序做 7 件事——加载 image 类、Resolve、（确定性构建时）ResolveConstStrings、Verify、InitializeClasses、UpdateImageClasses、初始化类型检查 bitstring。
- `CompileAll()`（:335）：真正逐方法编译，内部走 `CompileMethodHarness`（:367）→ 调 `art/compiler/` 的优化编译器。
- 管理两个线程池（`InitializeThreadPools`/`FreeThreadPools`），并用 `CheckThreadPools()`（:681）做断言。

**关键点**：`CompileMethodHarness` 里有一段已存在的"慢方法告警"逻辑（:395-401）——当 `kTimeCompileMethod` 打开时，单方法编译超过阈值会 `LOG(WARNING)`。这正是你做维测可以利用/扩展的现成钩子（见 8.3）。

### 5.3 ParallelCompilationManager + ThreadPool（compiler_driver.cc:1352）—— 并行模型

这是**理解挂死的核心**。模式很经典："任务队列 + 工作线程 + 主线程等待"：

```cpp
// ForAllLambda  (compiler_driver.cc:1397)
index_.store(begin);                       // 一个原子游标
for (i in work_units)                        // 投递 N 个 worker 任务
    thread_pool_->AddTask(self, new ForAllClosureLambda(...));
thread_pool_->StartWorkers(self);            // 放工人去抢任务
thread_pool_->Wait(self, true, false);       // ★主线程在这里阻塞等所有任务做完★
thread_pool_->StopWorkers(self);
```

每个 worker 在 `ForAllClosureLambda::Run`（:1433）里循环 `NextIndex()` 抢下一个 index 处理，直到游标越界。

**为什么这里和挂死强相关**：
- 主线程卡在 `thread_pool_->Wait()`，**只要任何一个 worker 不返回**（死循环 / 死锁 / 等一个永远不来的锁 / 等 GC），主线程就永远等下去 → 表现为"挂死"。
- worker 内编译某个超大/病态方法时间过长，也会让整体迟迟不结束。
- `kRunnable` 状态断言（:1411）和 GC 安全点：worker 与 GC 线程之间的挂起协议如果出问题，会互相等待。

### 5.4 OatWriter / ImageWriter / ElfWriter（linker/）

- `OatWriter`（oat_writer.cc，4092 行）：把每个方法的机器码、元数据、查找表，按精确的偏移布局序列化。先"算偏移"再"写内容"。
- `ImageWriter`（image_writer.cc）：把预初始化的对象堆按绝对地址布局写成 `.art`。
- `ElfWriter`（elf_writer_quick.cc）：把 oat 数据塞进 ELF（`.so`）容器，并 patch 程序头。

这一层是 **I/O 密集**：写大文件、`fsync`/flush（`FlushOutputFile` dex2oat.cc:2260）。磁盘满、存储驱动卡顿都会在这里表现为卡住。新手先理解"它负责落盘"即可。

---

## 6. WatchDog 看门狗机制（与"挂死"强相关）

**这是你排查挂死时第一个要理解的东西。** dex2oat 自带一个看门狗线程，专门防止自己卡死把系统拖垮。

源码：`dex2oat.cc:280-424`。

### 6.1 工作原理

```cpp
// 构造时(dex2oat.cc:296) 起一个独立 pthread 跑 Wait()
// Wait() 核心 (dex2oat.cc:378)
pthread_cond_timedwait(&cond_, &mutex_, &timeout_ts);   // 等 timeout 毫秒
// 超时 → ETIMEDOUT → Fatal("dex2oat did not finish after N seconds")
// Fatal() (dex2oat.cc:357): 打日志 → (host 上)dump 所有线程 → exit(1)
```

- 主流程正常结束时，`~WatchDog()`（:312）会 `signal` 让看门狗提前醒来退出，不会误杀。
- 主流程卡住超过超时 → 看门狗超时 → **强制 `exit(1)`**。

### 6.2 关键超时值（dex2oat.cc:341-347）

```cpp
// 默认 9.5 分钟（release 构建）
static constexpr int64_t kWatchDogTimeoutSeconds = kWatchdogSlowdownFactor * (9*60 + 30);
```

注释里明确写了设计意图：**比 PackageManagerService 的 10 分钟看门狗略短**，目的是让 dex2oat **自己先死**，避免连累 system_server 被它的看门狗打死。

> 这非常重要：你看到的"挂死"现象，可能有两层：
> 1. dex2oat 自己的看门狗 9.5 分钟超时 `exit(1)` → logcat 里会有 `dex2oat did not finish after 570 seconds`
> 2. 如果连看门狗都没反应，或上层 installd/PMS 卡住 → 可能是 10 分钟 PMS 看门狗，甚至更外层
>
> PackageManagerService watchdog：参考 AOSP `frameworks/base/services/core/java/com/android/server/Watchdog.java`

### 6.3 可调参数

命令行选项（`dex2oat_options.def:53-54`）：
- `--watchdog-timeout=<ms>`（`WatchdogTimeout`）：改超时时长
- 关看门狗：`-j`/相关 `Watchdog` 布尔（`watch_dog_enabled`，dex2oat.cc:844）

> **调试技巧**：定位挂死时，临时把 `--watchdog-timeout` 调大（或关闭），让进程卡住别退出，然后用 `debuggerd -b <pid>` 抓它当时的线程栈，能直接看到卡在哪个函数。见第 7 节。

---

## 7. 挂死问题分析方法

按"由外到内"的顺序排查，**先不要改代码**。

### 7.1 第一步：确认是谁、用什么参数起的 dex2oat

```bash
# 挂住时，先找到 dex2oat 进程
adb shell ps -A | grep dex2oat
# 看它的完整命令行（关键！能看出是 boot image / app / 哪个 filter）
adb shell cat /proc/<pid>/cmdline | tr '\0' ' '
# 看父进程是谁（installd? ）
adb shell cat /proc/<pid>/status | grep PPid
```
重点看命令行里的：`--compiler-filter=`（speed/speed-profile/verify…）、是否 `--boot-image`、`--dex-file=`、`-j<线程数>`。

### 7.2 第二步：抓卡住时的线程栈（最有价值）

dex2oat 卡住时，**当场抓 native 栈**，能直接看到卡在 `Wait` / 某个锁 / 某个方法编译 / I/O：
```bash
adb shell debuggerd -b <pid>        # dump 所有线程的 native backtrace
# 或
adb shell kill -3 <pid>             # 触发 SIGQUIT，ART 会 dump（看门狗 Fatal 在 host 也会 dump）
```
看栈时重点判断卡在哪一类：
- 卡在 `ThreadPool::Wait` / `ParallelCompilationManager` → 某个 worker 没回来，继续看 worker 线程栈
- 卡在 `pthread_cond_wait` / `MutexLock` / `Monitor` → **锁/死锁**
- 卡在 `OatWriter`/`write`/`fsync`/`ftruncate` → **I/O 卡住或磁盘满**
- 卡在某个具体 `Compile`/`HGraphBuilder`/优化 pass → **病态大方法**
- 大量时间在 GC / `WaitForGcToComplete` → **内存不足，疯狂 GC 或 swap 抖动**

### 7.3 第三步：看 logcat + 已有的 timing

```bash
adb logcat -b all | grep -i dex2oat
```
- 找看门狗日志：`dex2oat did not finish after N seconds`（确认是它超时）
- dex2oat 结束时会 `DumpTiming()`（dex2oat.cc:3070/3085）打印各阶段耗时——**但挂死时进程没走到这一步**，所以你需要主动加阶段日志（见第 8 节）。
- 打开 verbose：加 `-verbose:compiler` 命令行参数后，`VLOG(compiler)` 会输出每阶段内存/进度（PreCompile 里大量 `VLOG(compiler) << ... GetMemoryUsageString`，compiler_driver.cc:769-849）。

### 7.4 第四步：缩小范围

- 固定复现：用同一条命令行在 `adb shell` 里手动跑 dex2oat，加 `--watchdog-timeout=0`（关看门狗）让它一直卡，反复抓栈。
- 二分：换 `--compiler-filter=verify`（只校验不编译）能否复现？能 → 问题在 verify 阶段；不能 → 在 compile 阶段。
- 单 dex 复现：只喂出问题的那个 dex/apk。

### 7.5 常见挂死根因归类（经验）

| 现象（栈特征） | 可能根因 | 方向 |
|---------------|---------|------|
| 卡在 ThreadPool::Wait，worker 卡在 Monitor/锁 | 类加载/初始化死锁 | verify/initialize 阶段，类依赖环 |
| 卡在写 oat/image，伴随 ENOSPC | 磁盘满 | 存储清理、空间检查 |
| 卡在 write/fsync 很久 | 存储 I/O 慢/eMMC 异常 | 存储驱动/硬件 |
| 内存暴涨 + 频繁 GC + swap | 大 app/大方法 OOM 边缘 | 加 swap、限内存、降 filter |
| 单方法编译极慢 | 病态大方法/编译器 pass 爆炸 | art/compiler，方法级超时 |

---

## 8. 维测日志：加在哪、怎么加、如何不影响性能

你的第一步思路（先加维测日志再抓信息）是**对的**。下面给出"低开销、高定位价值"的落点。

### 8.1 核心原则（先记住，避免帮倒忙）

1. **只在"阶段边界"和"低频路径"打日志，绝不在"每方法/每类"的热路径无条件打日志。**
   - dex2oat 一次要编译几万个方法，`CompileAll` 内部是热到不能再热的循环。在那里每次 `LOG` 会拖慢几倍。
2. **善用已有设施，别造轮子**：
   - `VLOG(compiler)`：默认关闭，加 `-verbose:compiler` 才输出 → 天然零成本（不开就几乎无开销）。
   - `TimingLogger`/`ScopedTiming`：自动统计阶段耗时（dex2oat 已大量使用，如 `Compile` :1834、`Oat` :2053）。
   - `LOG(INFO/WARNING)`：用于真正的关键里程碑（每次运行个位数条）。
3. **热路径要打就用"采样/阈值/计数"**：只在超过时间阈值、或每 N 个、或出错时才打。
4. **带上关键上下文**：进程 pid、当前 dex location、compiler-filter、当前阶段、累计耗时。这样一条日志就能定位。

> 关于 ART 日志机制（`LOG` vs `VLOG`，`-verbose:` 开关）：
> - 源码 `art/libartbase/base/logging.h`
> - ART 命令行/verbose 选项：https://source.android.com/docs/core/runtime/configure

### 8.2 推荐落点一：阶段里程碑日志（首选，几乎零成本）

在主流程的"阶段边界"各加一条 `LOG(INFO)`，每次运行只有十来条，开销可忽略，但能立刻告诉你"卡在哪个阶段"。

落点（`dex2oat.cc`）：
- `Setup()` 开始/结束（:1415 / 其 return 处）
- `Compile()` 开始/结束（:1831 / :1929）
- `CompileDexFiles` 里 `PreCompile` 前后、`CompileAll` 前后（:1975 / :1982）
- `WriteOutputFiles()` 开始/结束（:2052）
- `HandleImage()` 开始/结束（:2207）

示例（在 `Compile()` 入口）：
```cpp
jobject Compile() {
  ClassLinker* const class_linker = Runtime::Current()->GetClassLinker();
  // 维测：阶段里程碑。每次运行仅一次，开销可忽略。
  LOG(INFO) << "[dex2oat-trace] Compile START, pid=" << getpid()
            << ", filter=" << CompilerFilter::NameOfFilter(compiler_options_->GetCompilerFilter())
            << ", dex_files=" << compiler_options_->dex_files_for_oat_file_.size();
  ...
}
```
> 更好的做法：用 `TimingLogger::ScopedTiming`（已存在）配合在异常退出路径也能 dump。但若挂死进程不退出，timing 不会被打印——所以**阶段日志要"进入即打"，不要只在"完成时打"**。这是定位挂死的关键差别。

### 8.3 推荐落点二：单方法编译"慢/卡"告警（热路径，必须带阈值）

热路径在 `CompileMethodHarness`（compiler_driver.cc:367）。这里**已经有**一个基于 `kTimeCompileMethod` 的慢方法告警（:395-401），但它默认编译期关闭。两种做法：

**做法 A（最小改动，推荐先用）**：在你的调试构建里把 `kTimeCompileMethod` 打开（它是个编译期常量，搜索其定义），这样超过阈值的方法会自动 `LOG(WARNING)` 打出方法名+耗时——**正好能抓"哪个方法编译卡住/极慢"**。

**做法 B（运行时可控）**：自己加一个"开始编译前打一条 VLOG，结束后按阈值打 WARNING"，但**用 `VLOG` 控制开始日志**（默认不输出），只有真正超时才 `LOG(WARNING)`：
```cpp
// CompileMethodHarness 内，compile_fn 调用前后
uint64_t start_ns = NanoTime();
VLOG(compiler) << "[m] begin " << dex_file.PrettyMethod(method_idx);  // 仅 -verbose:compiler 时输出
compiled_method = compile_fn(...);
uint64_t dur = NanoTime() - start_ns;
if (dur > MsToNs(kSlowMethodThresholdMs)) {   // 仅超阈值才打，热路径无额外成本
  LOG(WARNING) << "[dex2oat-trace] SLOW method " << dex_file.PrettyMethod(method_idx)
               << " took " << PrettyDuration(dur);
}
```
> 注意 `NanoTime()` 本身有微小成本，但相对单方法编译耗时可忽略；真正要避免的是无条件 `LOG`/字符串拼接。**字符串 `PrettyMethod()` 只在超阈值分支里调用**，平时不构造。

### 8.4 推荐落点三：并行等待点的"卡住"探测（直击挂死）

挂死最常卡在 `ParallelCompilationManager::ForAllLambda` 的 `thread_pool_->Wait()`（compiler_driver.cc:1414）。在这里加"周期性进度心跳"能直接抓到"卡在哪个阶段的第几个 index"。

思路：把 `Wait(self, true, false)`（无限等）改造成**带超时的轮询循环**，每隔比如 30s 打印一次当前 `index_` 进度（仅在调试构建/开关打开时启用）：
```cpp
// 伪代码示意：仅调试开关开启时走这条分支
if (kDex2oatTraceStall) {
  while (!thread_pool_->WaitForCompletion(self, /*timeout_ms=*/30000)) {
    LOG(WARNING) << "[dex2oat-trace] still compiling, progress index="
                 << index_.load(std::memory_order_relaxed) << "/" << end
                 << " dex=" << (dex_file_ ? dex_file_->GetLocation() : "?");
  }
} else {
  thread_pool_->Wait(self, true, false);   // 原逻辑，零改动路径
}
```
> `ThreadPool` 当前的 `Wait` 接口不一定直接支持超时，可能需要在 `art/runtime/thread_pool.{h,cc}` 加一个带超时的等待，或用条件变量改造。这是改动较大的方案，**作为第二阶段手段**；第一阶段先用 8.2 + 8.3。
>
> 更轻量的替代：起一个"进度打印线程"，每 30s 读一次原子 `index_` 打印，主线程逻辑完全不动——零侵入热路径。

### 8.5 推荐落点四：I/O 落盘耗时（写文件阶段）

在 `WriteOutputFiles`（:2052）、`FlushOutputFile`（:2260）、`FlushCloseOutputFile`（:2270）前后用 `ScopedTiming` 或里程碑日志，帮你区分"卡在编译"还是"卡在写盘"。写盘是**低频**调用，可以放心 `LOG(INFO)`。

### 8.6 让维测可"开关控制"（重要，避免影响量产性能）

不要硬编码总是打。用以下任一方式做成可控开关，量产默认关：
- **命令行选项**：仿照 `dex2oat_options.def` 加一个 `--runtime-arg -verbose:compiler` 或自定义 `--debug-trace`，解析进 `parser_options`。
- **系统属性**：用 `android::base::GetBoolProperty("dalvik.vm.dex2oat-trace", false)` 控制（installd 起 dex2oat 时也常通过属性传参）。
- **编译期常量 + 调试构建**：像 `kTimeCompileMethod`/`kIsDebugBuild` 那样，`userdebug`/`eng` 才生效。

> ART 属性与 dex2oat 参数透传：`dalvik.vm.*` 系列属性，参考
> https://source.android.com/docs/core/runtime/configure

### 8.7 落点优先级总结

| 优先级 | 落点 | 位置 | 成本 | 价值 |
|-------|------|------|------|------|
| ★★★ 先做 | 阶段里程碑（进入即打） | dex2oat.cc 各阶段函数入口 | 极低 | 立刻知道卡哪个阶段 |
| ★★★ 先做 | 慢方法阈值告警 | compiler_driver.cc:367/395 | 低（带阈值） | 抓病态方法 |
| ★★ 次做 | I/O 阶段计时 | dex2oat.cc:2052/2260 | 低 | 区分计算 vs 写盘 |
| ★ 进阶 | 并行进度心跳 | compiler_driver.cc:1414 + thread_pool | 中（需改接口） | 直击挂死现场 |

---

## 9. 华为设备专项（EMUI/Kirin）

> 本章针对"目标设备是华为"补充。**前提结论先行**：本机这份 `art` 源码经核实是 **纯 AOSP `sc-release`（Android 12）**，不含任何华为改动，因此对照真机调试时务必先看 9.1。

### 9.1 ⚠️ 你手里的源码 ≠ 设备上跑的代码

核实依据（本机 `art` 的 git 记录）：

```
8d44c3d61d Merge cherrypicks of [...] into sc-release   # sc = Snow Cone = Android 12
fe3c74bd60 Snap for 7633965 ...
7b4fead5e9 odrefresh: Respect "dalvik.vm.systemservercompilerfilter".
```

全部是 Google gerrit 的 cherrypick，`METADATA` 为标准 AOSP —— 这是 **Google 原版**。

**影响**：华为(EMUI)几乎一定改过 ART / `installd` / `PackageManagerService`（厂商普遍会改 dexopt 调度、看门狗、编译策略、热控）。所以：

- 用这份 AOSP **学原理完全没问题**（流程、数据结构、阶段顺序一致）。
- 但**逐行对栈、对行号**时，设备上的真实代码可能与此不同 —— 任何"行号级"结论都要在真机用栈再验证。

> **行动**：优先从华为拿 **BSP/SDK** 里的 `art/`（那才是设备真实代码）。ART 是 Apache-2.0，华为**没有义务**公开其修改（`floss.huawei.com` 一般只放 GPL 强制的内核），所以走你们的华为 FAE/技术对接渠道索取 BSP 是正路。

### 9.2 最可疑根因：热控/功耗调度把 dex2oat "限速到超时"

这是 EMUI 设备 dex2oat "挂死"的高发且隐蔽原因 —— **进程并没真卡死，只是被限速到 9.5 分钟看门狗超时**（`dex2oat.cc:344`）后被 `exit(1)`。

机理：EMUI 功耗/热管理会把后台任务（dex2oat 被 `installd` 放进 background cgroup/cpuset）**绑小核 + 压频 + 热限频**，正常 2 分钟的编译被拖到 >9.5 分钟。

**验证（挂住期间执行）**：

```bash
adb shell top -H -p <dex2oat pid>          # 线程是否几乎不占 CPU / 跑在小核
adb shell cat /proc/<pid>/stat             # 当前在哪个 CPU 核
adb shell cat /proc/<pid>/cgroup           # 被放进哪个 cgroup（background?）
adb shell cat /sys/class/thermal/thermal_zone*/temp   # 是否高温限频
```

**若证实是限速**：方向是调整 `installd` 给 dex2oat 的调度组/cpuset、`-j` 线程数，或在热场景临时放宽 `--watchdog-timeout`。
> 注意：单纯调大看门狗只是**治标**（让它别被打死），**治本**要解决"为什么这么慢"。

### 9.3 对比设备 dexopt 属性与 AOSP 默认值

华为常改这些属性，直接决定 dex2oat 行为，改过的地方即可疑点：

```bash
adb shell getprop | grep -E "dalvik.vm|pm.dexopt"
```

重点：

| 属性 | 含义 |
|------|------|
| `pm.dexopt.*`（install/boot/bg-dexopt…） | 各场景的 compiler-filter（华为可能调成更激进/更省） |
| `dalvik.vm.dex2oat-threads` / `...-cpu-set` | dex2oat 线程数 / 绑定的 CPU 集（与 9.2 强相关） |
| `dalvik.vm.dex2oat-flags` | 透传给 dex2oat 的额外参数 |
| `dalvik.vm.systemservercompilerfilter` | system_server 编译过滤器（见上面 odrefresh 提交） |

### 9.4 取栈/调试的权限限制

华为量产 **user** 版通常：bootloader 锁定、无 root、SELinux enforcing、`debuggerd` 受限。因此：

- 用你们 BSP 编的 **userdebug / eng 版本**来抓 `debuggerd -b` / `kill -3` / 加维测日志，**别在量产 user 机上调**。
- 这与第 8 节"维测做成属性开关、出 userdebug 灰度"的建议一致。

### 9.5 先确认运行时：Android ART 还是 HarmonyOS

华为 Android 12 时代很多机型为 HarmonyOS。若设备基于 HarmonyOS，运行时可能不是标准 ART（华为有方舟/Ark 路线），dex2oat 流程会更不同。**先确认设备实际运行时**，再判断本文档适用范围。你既有 `art` 源码且为 Android 12，大概率仍是 Android 系，但值得核实一句。

### 9.6 华为专项排查清单（对原方法的修正）

| 原排查思路（第 7 节） | 华为设备下的修正 |
|---|---|
| 照 AOSP 源码对行号 | ⚠️ 先拿华为 BSP 源码；AOSP 仅用于学原理 |
| 看门狗超时 = 真卡死 | 更可能是**被限速到超时**：先查 CPU/核/温度/cgroup（9.2） |
| 直接 `debuggerd` 抓栈 | 量产 user 机权限受限，改用 userdebug 版（9.4） |
| 用 AOSP 默认行为推断 | 先 `getprop` 对比华为改过的 dexopt 属性（9.3） |
| 默认是标准 ART | 先确认非 HarmonyOS 运行时（9.5） |

---

## 10. 参考资料

**官方 / 权威**
- ART 与 Dalvik（总览）：https://source.android.com/docs/core/runtime
- 配置 ART / dexopt / 编译过滤器：https://source.android.com/docs/core/runtime/configure
- AOSP 在线代码搜索（跨仓库跳转，强烈推荐）：https://cs.android.com/
- dex2oat 源码（在线，android12 分支可切）：https://cs.android.com/android/platform/superproject/+/android12-release:art/dex2oat/

**概念扫盲**
- AOT vs JIT vs 解释执行：https://en.wikipedia.org/wiki/Ahead-of-time_compilation
- DEX 文件格式：https://source.android.com/docs/core/runtime/dex-format
- ELF 文件格式（oat 的容器）：https://en.wikipedia.org/wiki/Executable_and_Linkable_Format
- compiler-filter 含义（verify/speed/speed-profile 等）：https://source.android.com/docs/core/runtime/configure#compilation_options

**调试工具**
- `debuggerd`（抓 native backtrace）：https://source.android.com/docs/core/tests/debug
- ART 性能/调试 verbose 选项：见上面 configure 文档的 `-verbose:` 部分

**相关源码定位（本机）**
- 主流程：`art/dex2oat/dex2oat.cc`
- 编译调度：`art/dex2oat/driver/compiler_driver.cc`
- 线程池：`art/runtime/thread_pool.{h,cc}`
- 真正的方法编译/优化：`art/compiler/`
- 调用方（不在 art 仓库）：`frameworks/native/cmds/installd/dexopt.cpp`、`frameworks/base/.../PackageDexOptimizer.java`

---

### 附：给你的下一步行动建议

1. 先按 7.1~7.3 在真机复现并**抓一次卡住时的 `debuggerd -b` 栈**——这一步往往直接给出答案，不需要改代码。
2. 若需长期维测，按 8.2 + 8.3 加阶段里程碑 + 慢方法告警，做成属性开关（8.6），出 userdebug 包灰度。
3. 把抓到的栈贴出来，我可以帮你判断卡点属于哪一类（编译/锁/IO/GC），再决定要不要深入 `art/compiler/` 或线程池。
