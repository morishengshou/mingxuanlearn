# dex2oat：Android 12 → Android 16 稳定性改进与可迁移分析

> 对比范围：`android12-release` vs `android16-release`（`D:\Android12\art` 仓库）
> 变更规模：514 个提交，83 个文件，+12,700 / -4,952 行
> 聚焦：dex2oat 挂死/死锁修复 + 可向 Android 12 回迁的改进

---

## 目录

1. [总览：变更分布](#1-总览变更分布)
2. [挂死/死锁修复 Top 10（按严重性排序）](#2-挂死死锁修复-top-10按严重性排序)
3. [WatchDog 看门狗变化](#3-watchdog-看门狗变化)
4. [稳定性关键改进](#4-稳定性关键改进)
5. [ThreadPool 重构](#5-threadpool-重构)
6. [linker/ 写文件阶段变化](#6-linker-写文件阶段变化)
7. [新增基础设施](#7-新增基础设施)
8. [可向 Android 12 回迁的改进（优先级排序）](#8-可向-android-12-回迁的改进优先级排序)
9. [不可回迁的改进（依赖架构变更）](#9-不可回迁的改进依赖架构变更)
10. [回迁实施建议](#10-回迁实施建议)

---

## 1. 总览：变更分布

| 模块 | 变更量 | 重点领域 |
|------|--------|---------|
| `dex2oat/dex2oat.cc` | ~1,800 行 | WatchDog、编译流程、错误处理、boot image 降级 |
| `dex2oat/driver/compiler_driver.cc` | ~2,000 行 | **并行模型**、Resolve/Verify/Compile 流程重构 |
| `dex2oat/linker/oat_writer.cc` | ~3,100 行 | Oat 写入重构、CodeInfo 去重 |
| `dex2oat/linker/image_writer.cc` | ~2,800 行 | Image 生成改进、GC 交互 |
| `runtime/thread_pool.{h,cc}` | ~449 行 | **抽象基类化**、工厂方法、Worker 随机重启 |
| `dex2oat/transaction.{h,cc}` | **新增** 1,181 行 | 事务性写入（原子替换） |
| `dex2oat/utils/swap_space.{h,cc}` | **新增** 467 行 | 统一 Swap 空间管理 |
| `dex2oat/utils/dedupe_set.{h,cc}` | **新增** 339 行 | CodeInfo 去重数据结构 |
| `dex2oat/utils/atomic_dex_ref_map.{h,cc}` | **新增** 237 行 | 无锁 Dex 引用映射 |

**新增能力**：
- RISC-V 支持（`dex2oat/linker/riscv64/`）
- SDK Checker（`dex2oat/sdk_checker.{h,cc}`）
- 多 Profile / 多 dirty-image-objects / FD 传递
- Cloud Compilation（确定性 oat checksum）

---

## 2. 挂死/死锁修复 Top 10（按严重性排序）

### #1 🔴 移除并行阶段中的「提前解析所有字段与方法」

**位置**：`compiler_driver.cc` — `ResolveClassFieldsAndMethodsVisitor` **整类删除**

**Android 12 问题**：
```
ResolveDexFile() → 
  ResolveTypeVisitor（并行解析所有类型）→ 
  ResolveClassFieldsAndMethodsVisitor（并行解析每个类的每个方法和字段）
```

`ResolveClassFieldsAndMethodsVisitor` 对每个类定义，调用 `class_linker->ResolveMethod` 和 `ResolveField`。这些调用会**触发类加载**（参数类型、返回类型、超类），而在线程池中 N 个线程同时做这些操作，形成了经典的 **ABBA 锁反转死锁**：

- 线程 A 持有 Verifier 锁，等待 ClassLinker 锁来加载返回类型
- 线程 B 持有 ClassLinker 锁，等待 Verifier 锁来完成另一个类的验证

**Android 16 修复**：
完全删除 `ResolveClassFieldsAndMethodsVisitor`。所有字段/方法的解析推迟到 **编译阶段**（`CompileMethodQuick`），此时是单方法单线程处理，锁层级简单，不再有线程池碰撞。

**可回迁性**：⭐⭐⭐⭐⭐ **高**。逻辑上是纯删除 + 简化，不依赖外部新 API。但需要验证：去掉这个 pass 之后，compile 阶段是否能正确处理"尚未 resolve 的字段/方法"（理论上可以，因为 Quick Compiler 本来就会按需 resolve）。**这是最值得回迁的一项。**

---

### #2 🔴 「纯验证」场景下也先解析类型再开多线程验证

**位置**：`compiler_driver.cc` — `PreCompile()` 新增 `should_resolve_eagerly` 条件

**Android 12 问题**：
```
如果 compiler_filter = verify（不编译，只验证）→ 直接到 Verify()，不做 Resolve()
→ 验证线程遇到未解析的类型 → 必须在持有 Verifier 锁的情况下解析 →
→ 与另一个持有 ClassLinker 锁的线程碰撞 → 死锁
```

**Android 16 修复**：
```cpp
// compiler_driver.cc: PreCompile()
// 新增条件：即使不编译，只要多线程验证，也要提前解析类型
bool should_resolve_eagerly = ... || 
    (!compiler_options_->IsForceDeterminism() && parallel_thread_count_ > 1);
if (should_resolve_eagerly) {
    Resolve(class_loader, dex_files, timings);
}
```

**根本原因**：Verifier 锁 + ClassLinker 锁是两条不同的锁路径。在单线程下顺序没问题，但在线程池中就是经典的锁排序问题。提前解析类型保证了验证开始前所有依赖关系已就绪。

**可回迁性**：⭐⭐⭐⭐⭐ **高**。只需在 `PreCompile()` 中加一个条件和一次 Resolve 调用。逻辑量极少，安全变更。

---

### #3 🔴 类查找从"基于描述符字符串"改为"基于 dex_file + class_idx"

**位置**：`compiler_driver.cc` — 所有 `FindClass()` 调用（~8 处）

**Android 12 问题**：
```cpp
// 每个并行 visitor 都在用字符串描述符查类
klass = class_linker->FindClass(self, descriptor, class_loader);
```

`FindClass(descriptor)` 会触发**完整的类解析链**：查找类型 → 解析 → 加载超类 → 加载接口 → …。在并行 visitor 中，这意味着多个线程同时遍历整个类层级，持有不同的锁，极易碰撞。

**Android 16 修复**：
```cpp
// 改用索引查找，跳过全链解析
klass = class_linker->FindClass(self, *dex_file, class_idx, class_loader);
```

基于 `dex_file + class_idx` 的 `FindClass` 只解析目标类本身，**不触发超类/接口加载**。锁路径缩短了数倍，大大减少了碰撞窗口。涉及：
- `VerifyClassVisitor::Visit`
- `SetVerifiedClassVisitor::Visit`
- `InitializeClassVisitor::Visit`
- `CompileDexFile` 内部 lambda
- `LoadAndUpdateStatus`
- `EnsureVerifiedOrVerifyAtRuntime`

**可回迁性**：⭐⭐⭐⭐ **较高**。需要确认 Android 12 的 `ClassLinker` 是否已提供 `FindClass(self, dex_file, class_idx, class_loader)` 重载。Android 12-release 晚期的 tag 很可能已有这个 API（它是 Android 11 时期引入的）。如果存在，就是简单的调用替换；不存在则需要先 backport `FindClass` 重载本身。

---

### #4 🔴 调试信息压缩的 use-after-free 修复

**位置**：`dex2oat.cc:1176-1180` — `PrepareDebugInfo()` 返回值变更

**Android 12 问题**：
```cpp
// 旧代码
elf_writer->PrepareDebugInfo(debug_info);  // 启动后台压缩线程
// ... 如果出错 return false ...
// → 析构路径释放了 debug_info 内存，但后台线程仍在访问 → use-after-free → segfault
```

**Android 16 修复**：
```cpp
// 新代码
auto compression_job = elf_writer->PrepareDebugInfo(debug_info);
// 返回 std::unique_ptr<ThreadPool>
// 析构时阻塞等待后台线程结束，保证内存安全
```

RAII 风格的生命周期管理，确保即使错误路径也能安全等待后台任务完成。

**可回迁性**：⭐⭐⭐⭐ **较高**。改动小而集中。需要改 `PrepareDebugInfo` 返回类型和调用侧的 RAII 包装。**这可以解决"dex2oat 在磁盘满/写失败时崩溃"的问题。**

---

### #5 🔴 OOM 从静默清除改为 FATAL

**位置**：`compiler_driver.cc` — `CheckAndClearResolveException` → `DCheckResolveException`

**Android 12 问题**：
```cpp
// 类型解析时发生 OOM → 检查异常类型 → ClearException() → 编译继续
// → 编译在内存不足的状态下继续 → 非确定性行为 → 可能挂死
```

**Android 16 修复**：
```cpp
if (exception->GetClass() == WellKnownClasses::java_lang_OutOfMemoryError.Get()) {
    LOG(FATAL) << "Out of memory during type resolution for compilation";
}
// OOM 直接终止进程，不允许继续
```

同时修了异常类比较方式：字符串比较 `DescriptorEquals` → 指针比较 `WellKnownClasses::Get()`，更正确。

**可回迁性**：⭐⭐⭐⭐ **较高**。需要 Android 12 的 `WellKnownClasses` 支持 `java_lang_OutOfMemoryError`（通常是有的）。逻辑是加一个 early-exit 分支。

---

### #6 🔴 类验证失败后注册为「不可编译」，防止编译阶段重试

**位置**：`compiler_driver.cc` — `FastVerify` 新增回调

**Android 12 问题**：
```
验证失败 → 类的状态标记为 kRetryVerificationAtRuntime
→ 编译阶段不知道这个类有问题 → 照常编译 → 碰到未预期的状态
→ 抛异常 → 异常处理过程又碰撞到其他锁 → 可能挂死
```

**Android 16 修复**：
```cpp
if (status == ClassStatus::kRetryVerificationAtRuntime) {
    ClassReference ref(dex_file, accessor.GetClassDefIndex());
    callbacks->AddUncompilableClass(ref);  // 告诉编译阶段"跳过这个类"
}
```

**可回迁性**：⭐⭐⭐⭐ **较高**。需要 `AddUncompilableClass` 回调在 Android 12 的 callbacks 类中存在（查看 `quick_compiler_callbacks.h`）。如果存在，加两行即可。

---

### #7 🔴 Catch 块异常类型解析 visitor 重写，禁止线程挂起

**位置**：`compiler_driver.cc` — `ResolveCatchBlockExceptionsClassVisitor`

**Android 12 问题**：
```
遍历 Class 的 ObjPtr vector → 线程挂起（GC STW）→ 对象移动 → 
→ vector 里的 ObjPtr 变悬空指针 → use-after-free
```

**Android 16 修复**：
- `BitVector` 替代 `std::set<TypeReference>`（calloc 分配，零初始化）
- `ScopedAssertNoThreadSuspension` 禁止关键区间内挂起
- Boot image 地址区间检查跳过已处理类
- `FindAndResolveExceptionTypes()` 用 while 循环迭代至收敛

**可回迁性**：⭐⭐⭐ **中等**。改动较分散，需要引入 `BitVector + CallocAllocator` 和 `ScopedAssertNoThreadSuspension`。但如果 Android 12 上确实有 GC 期 use-after-free 的问题，值得迁。

---

### #8 🔴 VerifierDeps 每线程副本不再有条件限制

**位置**：`compiler_driver.cc` — Verify visitor

**Android 12 问题**：
```cpp
// 仅在非 boot image / 非 boot extension 时创建每线程 VerifierDeps
if (!IsBootImage() && !IsBootImageExtension()) { ... }
// 否则所有线程共享同一个 VerifierDeps → mutex 竞争
```

**Android 16 修复**：
```cpp
// 只要主 VerifierDeps 非空，总是创建每线程副本
if (main_verifier_deps != nullptr) { ... }
```

减少了 boot image 验证时的锁竞争，间接降低线程饥饿导致的超时。

**可回迁性**：⭐⭐⭐⭐ **较高**。一行条件替换。

---

### #9 🔴 并行 visitor 内部删除 LOG(ERROR)

**位置**：`compiler_driver.cc` — `VerifyClassVisitor`

**Android 12 问题**：
```
每个 HardFailure 在 visitor 循环内打 LOG(ERROR) →
→ logger mutex 竞争 → N 个线程争先打日志 → 一个线程在等锁，一个线程在等它
→ 线程饥饿 → 整体超时
```

**Android 16 修复**：
```cpp
case verifier::FailureKind::kHardFailure: {
    // 删除：LOG(ERROR) << "Verification failed on class " << ...
    manager_->GetCompiler()->SetHadHardVerifierFailure();
    break;
}
```

Verifier 本身已记录失败详情，visitor 内部无需重复打印。

**可回迁性**：⭐⭐⭐⭐⭐ **高**。纯删除一句话。

---

### #10 🔴 HardFailure 后从 app image 中删掉错误类

**位置**：`compiler_driver.cc` — `PreCompile()` 新增逻辑

**Android 12 问题**：
```
生成 app image 时 → 某个类 HardFailure → 该类仍然被写入了 image
→ 运行时加载这个 image → 访问错误类 → crash/hang
```

**Android 16 修复**：
```cpp
if (GetCompilerOptions().IsAppImage() && had_hard_verifier_failure_) {
    UpdateImageClasses(timings, image_classes);  // 修剪掉错误类
}
```

**可回迁性**：⭐⭐⭐⭐ **较高**。在 PreCompile 流程中加一个条件调用。

---

## 3. WatchDog 看门狗变化

### 变化很小（仅 2 处），不涉及超时值本身

| 变更 | 位置 | 详情 |
|------|------|------|
| `exit(1)` → `exit(ReturnCode::kOther)` | `dex2oat.cc` WatchDog::Fatal | 用枚举常量代替魔法数字，无行为变化 |
| 超时信息 "seconds" → "milliseconds" | `dex2oat.cc` WatchDog::Fatal | 显示原始毫秒值，不除以 1000。便于调试短超时 |

**核心结论**：看门狗的**超时值**（`kWatchDogTimeoutSeconds` = 9.5 分钟）、**校验倍率**（`kWatchdogVerifyMultiplier` = 100x for verify）、**调试倍率**（`kWatchdogSlowdownFactor` = 5x for debug）在 Android 12 和 Android 16 之间**完全一致**。

这意味着：**如果你的华为设备上 dex2oat 频繁看门狗超时（9.5 分钟 exit(1)），问题不在 ART 源码的看门狗定时机制，而在于「为什么编译超过了 9.5 分钟」**。

---

## 4. 稳定性关键改进

### 4.1 线程安全注解与断言

```cpp
// dex2oat.cc（新增）
jobject Compile() REQUIRES(!Locks::mutator_lock_);
Locks::mutator_lock_->AssertNotHeld(Thread::Current());  // debug 断言
```

如果调用链中某个函数意外持有了 mutator lock，debug build 会在编译开始前直接 crash（带栈），而不是在生产环境中随机死锁。

### 4.2 Thread State 改为 32-bit 原子访问

Commit `ddf4fd3c`："Always access Thread state and flags as 32-bit location."

**影响**：Thread 挂起请求从 `volatile` 改为 `atomic`（正确的内存顺序），消除了"线程 A 设置挂起请求但线程 B 看不到"的竞态。这是 GC 等待线程挂起超时的潜在根因之一。

### 4.3 ARM64 隐式挂起检查启用

Android 12 上 ARM64 的隐式挂起检查被禁用；Android 16 上已打开。基于 Fault 的挂起（`LDR → SIGSEGV → 信号处理 → 挂起`）比显式轮询（`LDR+TST+BNE`）更可靠，无漏检窗口。

### 4.4 读文件从 `/proc/self/fd` 改为 `fdopen()`

Commit `2bac0495`：在 Microdroid/Compos 环境下，dex2oat 没有权限访问 `/proc/self/fd/N`。改用 `fdopen()` 直接从文件描述符读取，避免了因为权限不足导致的编译失败。

### 4.5 Boot Image 缺失时优雅降级

```cpp
// dex2oat.cc — 新增逻辑
if (boot_image_spaces.empty()) {
    image_type_ = kNone;  // 不生成 image，但继续生成 oat/vdex
}
```

Android 12 在此场景会 `CHECK` 失败（crash）或返回 `kOther`（编译失败）。Android 16 降级为不生成图像，但 oat/vdex 仍正常产出——这在 ART APEX 更新后 boot image 暂时不可用期间至关重要。

### 4.6 DM 文件与 vdex 文件同时存在时不崩溃

Commit `84092814`：删除 `DCHECK(input_vdex_file_ == nullptr)`，改为选择其中一个继续。旧逻辑在 debug build 会 crash。

### 4.7 只读文件不再尝试 Flush/Erase

```cpp
if (ReadOnlyMode()) { return; }
```

用已存在的 vdex 作输出时（`use_existing_vdex_`），fd 是只读的。Android 12 在错误路径上会 `Flush`/`Erase` 只读 fd 导致 EBADF，然后级联失败。Android 16 提前 check 并跳过。

### 4.8 `ArtMethod*` well-known 方法的缓存访问

大量提交（`d3f0238f`、`addc2d15`、`b6f965d2`…）将 well-known 方法从字符串查找改为直接指针访问，避免每次编译时都要在 ClassLinker 的哈希表中查找。在并行编译场景中，这减少了各 worker 争抢 ClassLinker 哈希表锁的次数。

---

## 5. ThreadPool 重构

```
ThreadPool（Android 12）  →  AbstractThreadPool（Android 16）
  - 直接 new                       - ThreadPool::Create() 工厂方法
  - 固定线程                       - 支持 Worker 随机重启
  - 无 HasStarted()                - 新增 HasStarted() 检查
  - 单一路径                       - 支持自定义 Task 队列
```

### 关键变化

| 变更 | 说明 |
|------|------|
| `ThreadPool` → `AbstractThreadPool` | 抽象基类，支持不同的任务队列实现 |
| `ThreadPool::Create()` | 工厂方法代替 `new`，可注入平台特定实现 |
| `AddTask` 和 `RemoveAllTasks` 改为纯虚函数 | 子类可自定义排队策略 |
| `HasStarted()` 新增 | 防止给尚未 StartWorkers 的池投任务 |

**对挂死的影响**：工厂方法允许在创建线程池时做健康检查（如确保线程创建成功）；抽象基类使得未来可以替换为带超时的 `Wait` 实现（但 Android 16 尚未做这一步）。

---

## 6. linker/ 写文件阶段变化

### 6.1 OatWriter 大规模重构（~2,200 行变更）

核心变化：
- **CodeInfo 去重**：新增 `CodeInfoTableDeduper`（`code_info_table_deduper.{h,cc}`），多个方法共享相同的 CodeInfo 时只存一份，减少 oat 体积
- **写入路径分段**：`WriteRodata()` 拆分为多个子阶段，每个有独立的 TimingLogger
- **App Image 支持**：`.data.bimg.rel.ro` 重命名为 `.data.img.rel.ro`，同时支持 boot image 和 app image 类
- **Oat 校验和确定性**：非确定性字段（命令行、APEX 版本）填充到固定长度后排除出 checksum 计算

### 6.2 ImageWriter 改进（~2,800 行变更）

- **GC 前先初始化 Image Roots**（commit `c4351668`）：在触发 GC 前确保 image root 对象已就绪，避免 GC 在 image 写入过程中操作未初始化的 root 引用
- **App Image 类的重定位支持**：`HLoadClass` 对 app image 类也可以走快速路径
- **错误类的排除**：init 失败/验证失败的类不包含在 image 中

### 6.3 新增：事务性写入

**全新文件**：`dex2oat/transaction.{h,cc}`（~1,200 行）+ `transaction_test.cc`（~850 行）

提供原子替换文件的机制："先写临时文件 → 验证 → rename 覆盖"的模式，防止 dex2oat 崩溃留下损坏的 oat/vdex。这是 I/O 层面最重要的稳定性改进，但 Android 16 的 transaction 代码依赖了新的 fd 传递模型和 `ArtDexFileLoader`，直接回迁成本较高。

---

## 7. 新增基础设施

| 组件 | 文件 | 用途 |
|------|------|------|
| `SwapSpace` | `utils/swap_space.{h,cc}` | 统一管理 dex2oat 编译期间的 swap 空间，替换散落在各处的临时 fd |
| `AtomicDexRefMap` | `utils/atomic_dex_ref_map.{h,cc}` | 无锁的 dex 引用 → 编译结果映射，多线程并行写入无需 mutex |
| `DedupeSet` | `utils/dedupe_set.{h,cc}` | CodeInfo 去重的底层哈希集合 |
| `CodeInfoTableDeduper` | `linker/code_info_table_deduper.{h,cc}` | 利用 DedupeSet 实现 CodeInfo 去重 |

这些是 Android 16 架构升级的产物。它们直接回迁成本高（依赖新的类接口），但**设计思路可以借鉴**——例如用 `AtomicDexRefMap` 替换 Android 12 里靠 mutex 保护的 `compiled_methods_` 映射，消除一类锁竞争。

---

## 8. 可向 Android 12 回迁的改进（优先级排序）

### P0 — 高收益、低风险、改动小

| # | 改进项 | 预期效果 | 改动量 | 对应 A16 commit |
|---|--------|---------|--------|----------------|
| 1 | 删除 `ResolveClassFieldsAndMethodsVisitor` | 消除线程池中最主要的死锁源 | ~200 行删除 | compiler_driver 重构系列 |
| 2 | 仅验证模式下也先解析类型 | 消除 verify-only 编译的死锁 | ~5 行新增 | `should_resolve_eagerly` 条件 |
| 3 | 并行 visitor 内部删除 LOG(ERROR) | 消除 logger mutex 竞争 | ~5 行删除 | hard failure log removal |
| 4 | VerifierDeps 每线程副本条件放宽 | 减少 boot image 验证锁竞争 | ~1 行改条件 | `main_verifier_deps != nullptr` |

### P1 — 较高收益、改动中等

| # | 改进项 | 预期效果 | 改动量 | 对应 A16 commit |
|---|--------|---------|--------|----------------|
| 5 | FindClass 改为 dex_file + class_idx | 缩短并行 visitor 中的锁路径 | ~8 处调用替换 | 需确认 A12 ClassLinker API |
| 6 | OOM 改为 LOG(FATAL) | 防止低内存下的非确定性挂死 | ~3 行替换 | `CheckAndClearResolveException` |
| 7 | 验证失败类注册为不可编译 | 防止编译阶段处理坏类 | ~3 行新增 | `AddUncompilableClass` |
| 8 | app image HardFailure 后修剪错误类 | 防止运行时加载错误类 | ~3 行新增 | `UpdateImageClasses` after failure |
| 9 | 调试信息压缩 RAII 化 | 修复错误路径 use-after-free | ~10 行改动 | `PrepareDebugInfo` 返回 unique_ptr |

### P2 — 值得做但改动较大

| # | 改进项 | 预期效果 | 改动量 |
|---|--------|---------|--------|
| 10 | ResolveCatchBlock 重写（BitVector + 禁止挂起） | 消除 GC 期 ObjPtr 悬空 | ~100 行 |
| 11 | Thread State 32-bit 原子访问 | 消除挂起请求遗漏 | 需要全 Runtime 范围的 Thread state 格式变更 |
| 12 | ARM64 隐式挂起检查启用 | 更可靠的线程挂起 | 需确认 A12 生成的 arm64 代码支持 |

---

## 9. 不可回迁的改进（依赖架构变更）

以下 Android 16 改进无法直接 cherry-pick 到 Android 12，因为它们依赖新的类层次、API 或基础设施：

| 改进项 | 依赖 |
|--------|------|
| ThreadPool → AbstractThreadPool | 需要全 ART 的 ThreadPool 调用者改为使用 `Create()` 工厂 |
| Transaction 事务性写入 | 依赖 `ArtDexFileLoader`、新的 FD 传递模型 |
| CDEX/DexLayout 移除 | Android 12 仍需保留（厂商可能依赖 cdex） |
| RISC-V 支持 | 新架构，与 ARM 设备无关 |
| Cloud Compilation 确定性校验和 | 依赖大量 key-value-store 重构 |
| CodeInfoTableDeduper + DedupeSet | 依赖 OatWriter 的大规模重构 |
| AtomicDexRefMap | 需替换 `CompiledMethod` 存储模型 |
| SDK Checker | 与 Android 16 的新 public API surface 相关 |

---

## 10. 回迁实施建议

### 10.1 顺序

```
第1轮（P0，改动小，立即出包）：
  1. 删除 ResolveClassFieldsAndMethodsVisitor
  2. 加 should_resolve_eagerly 条件
  3. 删 LOG(ERROR) in visitor
  4. VerifierDeps 条件放宽
  → 这轮应该可以解决绝大多数线程池死锁

第2轮（P1，逐个验证）：
  5-9. FindClass 替换、OOM FATAL、验证失败注册等
  → 每个改动单独出包测试，确认无回归

第3轮（P2，视情况）：
  10-12. Catch block 重写、原子 Thread state、隐式挂起
  → 这些改动大会影响其他模块，需要更多验证
```

### 10.2 验证方法

对每个 backport：
1. **编译**：确保 Android 12 编译通过
2. **`art/test/testrunner/run_build_test_target.py art-standalone-dex2oat-tests`**：跑 dex2oat 单元测试
3. **实际场景**：在你们的华为设备上跑一轮批量 dexopt
4. **对比**：加 `--dump-timings` 比较回迁前后的编译时间
5. **压测**：刻意触发热控限频 + boot 后批量 dexopt，确认不再出现 9.5 分钟看门狗超时

### 10.3 注意事项

- 每个回迁 commit 单独打 patch，保留原 A16 commit hash 在 commit message 中（`Cherry-picked from: <hash>`），方便追溯。
- P0 的 #1（删除 ResolveClassFieldsAndMethodsVisitor）虽然收益最高，但改动量也最大，**建议先在其他 3 个 P0 项中挑一个最小的试刀**（比如 #4 VerifierDeps 条件一行改）。
- 回迁过程中如果发现 Android 12 缺少某个 API（如 `FindClass` 的重载），需要评估先 backport API 还是选择替代实现。

---

## 附录 A：关键 Commit 索引

| Commit Hash | 简述 | 涉及文件 |
|-------------|------|---------|
| `ba5cc5b551` | Revert² "Don't wait with mutator lock" | dex2oat.cc, class_linker.cc |
| `dfc85005d9` | Refactoring of ThreadPool | thread_pool.{h,cc}, 15 files |
| `186ee7b672` | Don't resolve dex files eagerly for verify single thread | compiler_driver.cc |
| `c435166827` | Initialize image roots before GC in ImageWriter | image_writer.cc |
| `1647f4c5ed` | Fix watchdog test that may kill dex2oat with SIGABRT | dex2oat_test.cc |
| `aface21c61` | Use enum in fatal exit from watchdog | dex2oat.cc |
| `ddf4fd3c37` | Always access Thread state as 32-bit location | thread.h, thread.cc |
| `2bac0495` | Avoid open from /proc/self/fd | dex2oat.cc |
| `fc1ba6d9` | Don't generate app image without boot image | dex2oat.cc |
| `3086bbd6` | Fix use-after-free in mini-debug-info compression | dex2oat.cc, elf_writer* |
| `f758d6a7` | Fix VerificationResults use in OatWriter | dex2oat.cc, compiler_driver.cc |
| `84092814` | Handle dm file + vdex file conflict | dex2oat.cc |
| `59edf4b8` | Don't prune dex if passed as FD | dex2oat.cc |
| `890beb0e` | Ignore checksum mismatch for multiple profiles | dex2oat.cc |
| `e7815b8c` | Add flag to optimize for JIT Zygote | dex2oat.cc |
| `826e6667` | Add --dex-fd to dex2oat | dex2oat.cc |

## 附录 B：华为设备专项回溯

本文档第 2 节列出的 Top 10 修复中，以下与**华为设备 dex2oat 挂死**最直接相关：

1. **#1 删除 ResolveClassFieldsAndMethodsVisitor** — 如果你们设备的挂死栈中出现了 `ResolveMethod` / `ResolveField` + 线程池 worker 栈，这就是直接根因。
2. **#2 验证前先解析** — 如果 `compiler-filter=verify` 场景（这在开机批量 dexopt 中常见）更容易挂死，这是锁定项。
3. **#9 并行 visitor 中删 LOG(ERROR)** — 如果挂死时 logcat 有大量 verifier failure，很可能就是这个导致的 logger 锁饥饿。
4. **#5 OOM → FATAL** — 如果设备内存压力大（华为热控 + background cgroup 限内存），OOM 静默处理后的非确定性状态可能是"看起来在跑但实际已经坏了"的原因。
