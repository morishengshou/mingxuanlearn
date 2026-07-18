*Thinking...*

> **Clarifying terminology**
> 
> I need to clarify what "stf" means because it seems like a typo. I'm guessing it might refer to "std::unordered_map." Also, there's something about Android 12 sources—those should be from official primary sources. It looks like I should search for more information to clear this up. There’s a lot going on here, so I’ll make sure to gather the right details for a better understanding!
> 
> **Searching for patterns**
> 
> I need to find out more about initializing specific sources, main threading, and fork implementations. It seems like I should also look into singleton patterns. I'll start by searching for relevant code examples that explain these concepts. It’s important to gather clear, practical information on how to implement these techniques. I'll make sure to document my findings as I go along! Let's see what I can uncover.
> 
> **Explaining subcontext commands**
> 
> I’m considering how commands operate within the vendor_init subcontext process, which keeps singletons separate for each process. If I want a custom command to alter the main init map, I actually need to set run_in_subcontext to false. It’s important to clarify why that false setting is necessary. I’ll search for official sources to get accurate information about how subcontext works, so I can explain it effectively!

下面按你写的是 **`std::unordered_map<std::string, int>`** 来实现；如果 `stf` 是你们自己的命名空间，把 `std` 替换掉即可。

## 一、推荐的单例实现

不建议直接向外暴露 `unordered_map&`，否则调用方很容易绕过锁。更安全的方式是用类封装读写接口。

### 1. `stf_registry.h`

```cpp
#pragma once

#include <cstddef>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>

namespace android {
namespace init {

class StfRegistry final {
  public:
    static StfRegistry& GetInstance();

    StfRegistry(const StfRegistry&) = delete;
    StfRegistry& operator=(const StfRegistry&) = delete;
    StfRegistry(StfRegistry&&) = delete;
    StfRegistry& operator=(StfRegistry&&) = delete;

    // 新增或覆盖。
    void Put(std::string key, int value);

    // 查询。返回副本，避免返回引用后的并发失效问题。
    std::optional<int> Get(const std::string& key) const;

    bool Contains(const std::string& key) const;
    bool Erase(const std::string& key);

    void Clear();
    std::size_t Size() const;

    // 用于 dump/debug。返回快照，不向外暴露内部容器。
    std::unordered_map<std::string, int> Snapshot() const;

  private:
    StfRegistry() = default;
    ~StfRegistry() = default;

    mutable std::mutex mutex_;
    std::unordered_map<std::string, int> values_;
};

}  // namespace init
}  // namespace android
```

### 2. `stf_registry.cpp`

```cpp
#include "stf_registry.h"

#include <utility>

namespace android {
namespace init {

StfRegistry& StfRegistry::GetInstance() {
    // 这里故意让对象具有进程级生命周期，不在退出阶段析构。
    //
    // 对 init/PID 1 来说：
    // 1. 正常情况下进程不会普通退出；
    // 2. 可以规避不同翻译单元之间的静态析构顺序问题。
    static StfRegistry* const instance = new StfRegistry();
    return *instance;
}

void StfRegistry::Put(std::string key, int value) {
    std::lock_guard<std::mutex> lock(mutex_);
    values_[std::move(key)] = value;
}

std::optional<int> StfRegistry::Get(const std::string& key) const {
    std::lock_guard<std::mutex> lock(mutex_);

    const auto it = values_.find(key);
    if (it == values_.end()) {
        return std::nullopt;
    }

    return it->second;
}

bool StfRegistry::Contains(const std::string& key) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return values_.find(key) != values_.end();
}

bool StfRegistry::Erase(const std::string& key) {
    std::lock_guard<std::mutex> lock(mutex_);
    return values_.erase(key) != 0;
}

void StfRegistry::Clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    values_.clear();
}

std::size_t StfRegistry::Size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return values_.size();
}

std::unordered_map<std::string, int> StfRegistry::Snapshot() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return values_;
}

}  // namespace init
}  // namespace android
```

这里使用“函数内静态指针”实现延迟初始化。AOSP 自身的 `ServiceList::GetInstance()` 也使用了类似的进程寿命单例设计。([android.googlesource.com](https://android.googlesource.com/platform/system/core/%2B/refs/heads/main/init/service_list.cpp?utm_source=openai))

---

## 二、普通调用示例

```cpp
#include "stf_registry.h"

#include <android-base/logging.h>

namespace android {
namespace init {

void DemoRegistry() {
    StfRegistry& registry = StfRegistry::GetInstance();

    registry.Put("boot_count", 1);
    registry.Put("service_count", 10);

    if (auto value = registry.Get("boot_count"); value.has_value()) {
        LOG(INFO) << "boot_count=" << *value;
    }

    registry.Erase("service_count");

    for (const auto& [key, value] : registry.Snapshot()) {
        LOG(INFO) << "registry: " << key << "=" << value;
    }
}

}  // namespace init
}  // namespace android
```

如果能保证所有访问都发生在 init 主事件循环线程，也可以去掉锁。但 init 扩展代码未来可能被属性处理、异步任务或其他线程调用，保留锁通常更稳妥。

---

## 三、扩展成 Android init builtin 命令

假设你希望在 `.rc` 文件中支持：

```rc
on boot
    stf_set boot_phase 100
    stf_dump
```

### 1. 在 `builtins.cpp` 中增加实现

```cpp
#include "stf_registry.h"

#include <android-base/logging.h>
#include <android-base/parseint.h>
```

增加 builtin 函数：

```cpp
static Result<void> do_stf_set(const BuiltinArguments& args) {
    int value = 0;
    if (!android::base::ParseInt(args[2], &value)) {
        return Error() << "Invalid integer value: " << args[2];
    }

    // 可根据实际需求限制 key 的长度。
    if (args[1].empty() || args[1].size() > 128) {
        return Error() << "Invalid key length";
    }

    StfRegistry::GetInstance().Put(args[1], value);

    LOG(INFO) << "stf_set: " << args[1] << "=" << value;
    return {};
}

static Result<void> do_stf_erase(const BuiltinArguments& args) {
    const bool erased = StfRegistry::GetInstance().Erase(args[1]);

    LOG(INFO) << "stf_erase: key=" << args[1]
              << ", erased=" << erased;
    return {};
}

static Result<void> do_stf_clear(const BuiltinArguments&) {
    StfRegistry::GetInstance().Clear();
    LOG(INFO) << "stf registry cleared";
    return {};
}

static Result<void> do_stf_dump(const BuiltinArguments&) {
    const auto snapshot = StfRegistry::GetInstance().Snapshot();

    LOG(INFO) << "stf registry size=" << snapshot.size();

    for (const auto& [key, value] : snapshot) {
        LOG(INFO) << "stf registry: " << key << "=" << value;
    }

    return {};
}
```

### 2. 注册 builtin 命令

在 `GetBuiltinFunctionMap()` 的表中加入：

```cpp
{"stf_set",   {2, 2, {false, do_stf_set}}},
{"stf_erase", {1, 1, {false, do_stf_erase}}},
{"stf_clear", {0, 0, {false, do_stf_clear}}},
{"stf_dump",  {0, 0, {false, do_stf_dump}}},
```

例如：

```cpp
const BuiltinFunctionMap& GetBuiltinFunctionMap() {
    constexpr std::size_t kMax =
            std::numeric_limits<std::size_t>::max();

    static const BuiltinFunctionMap builtin_functions = {
        // 原有命令……
        {"setprop",   {2, 2, {true,  do_setprop}}},
        {"start",     {1, 1, {false, do_start}}},
        {"stop",      {1, 1, {false, do_stop}}},

        // 自定义命令。
        {"stf_set",   {2, 2, {false, do_stf_set}}},
        {"stf_erase", {1, 1, {false, do_stf_erase}}},
        {"stf_clear", {0, 0, {false, do_stf_clear}}},
        {"stf_dump",  {0, 0, {false, do_stf_dump}}},
    };

    return builtin_functions;
}
```

Android init 的 builtin 表包含最小参数数、最大参数数、是否在 subcontext 中运行以及对应的处理函数；Android 12 使用的整体形式与上面一致。([android.googlesource.com](https://android.googlesource.com/platform/system/core/%2B/f7a6c4587f06bc7e79748acd97dc4dd5b741f328/init/builtins.cpp?utm_source=openai))

这里的 `false` 很重要，表示命令在主 init 进程中执行，而不是转发给 `vendor_init` subcontext。

### 3. `.rc` 使用示例

```rc
on early-init
    stf_set boot_phase 1

on init
    stf_set boot_phase 2

on post-fs
    stf_set boot_phase 3

on boot
    stf_set boot_completed 1
    stf_dump
```

---

## 四、Android.bp

需要将新增源文件加入实际承载 init 公共源码的模块或 defaults 中，例如：

```bp
srcs: [
    // 原有文件……
    "builtins.cpp",
    "service.cpp",

    // 新增文件。
    "stf_registry.cpp",
],
```

具体放到哪个 `srcs` 要看你的 Android 12 分支如何拆分 `init`、`libinit` 和 host 侧目标。

如果 `builtins.cpp` 同时被 `host_init_verifier` 使用，那么 `stf_registry.cpp` 也必须被对应 host 目标编译或链接，否则 host 构建时会出现未定义符号。Android 的 init 脚本会在构建期间由 host verifier 检查 builtin 名称和参数数量。([android.googlesource.com](https://android.googlesource.com/platform/system/core/%2B/refs/heads/android12-qpr3-s2-release/init/))

---

# 五、在 Android 12 init 中使用单例的主要注意事项

## 1. 单例是“进程内单例”，不是系统全局单例

它只保证当前地址空间中有一份对象：

- 主 init 进程有一份；
- `vendor_init` subcontext 进程可能有另一份；
- init fork 出来的子进程会得到一份写时复制的快照；
- 其他 daemon 无法直接访问这份 map。

因此，这个单例适合保存 **init 自身的运行期状态**，不适合用作跨进程数据库。

如果其他进程也需要访问，应该考虑：

- Android system property；
- Binder/AIDL 服务；
- 共享内存；
- 文件或持久化数据库；
- Unix domain socket。

---

## 2. first-stage、SELinux stage 和 second-stage 之间有 `exec`

Android 12 的 init 启动分为：

1. first-stage init；
2. SELinux setup；
3. second-stage init。

阶段之间会重新 `exec /system/bin/init`。因此，在 first-stage 创建的 C++ 单例不会自动保留到 second-stage。主要业务状态应当在 `second_stage` 之后初始化。([android.googlesource.com](https://android.googlesource.com/platform/system/core/%2B/refs/heads/android12-qpr3-s2-release/init/))

也就是说，下面这种认知是错误的：

```text
first-stage 写入 map
    ↓
second-stage 仍能读取
```

实际上 `exec` 后地址空间会被替换，原 map 已经不存在。

---

## 3. 特别注意 fork 后的行为

init 启动 service、执行 `exec`/`exec_background` 等操作时会创建子进程。AOSP 文档也明确说明这些命令涉及 fork 和执行外部程序。([android.googlesource.com](https://android.googlesource.com/platform/system/core/%2B/refs/heads/android12-qpr3-s2-release/init/))

fork 后：

```text
主 init map
    |
    +-- fork --> 子进程获得 map 的内存快照
```

父子进程之后修改的是各自的数据，不会互相同步。

例如：

```cpp
auto& registry = StfRegistry::GetInstance();
registry.Put("value", 1);

pid_t pid = fork();

if (pid == 0) {
    registry.Put("value", 2);
    // 这里只修改子进程副本。
    _exit(0);
}

// 父进程中仍然是 1。
```

### 更重要的是 mutex

如果 init 已经是多线程进程，fork 时另一个线程刚好持有 `mutex_`，子进程中这个锁可能永久保持“已加锁”状态，因为持锁线程不会出现在子进程中。

因此：

> **不要在 fork 后、exec 前的子进程路径中访问这个单例。**

尤其不要做下面这些操作：

```cpp
// 子进程 fork 后、exec 前：不推荐。
StfRegistry::GetInstance().Put("child", 1);
StfRegistry::GetInstance().Snapshot();
LOG(INFO) << StfRegistry::GetInstance().Size();
```

它们可能涉及：

- `std::mutex`；
- 堆内存分配；
- `unordered_map` 扩容；
- C++运行库内部锁；
- 日志系统内部锁。

Bionic 提供 `pthread_atfork` 机制处理特定 fork 锁状态，但不应该依赖它自动处理你自定义单例中的 mutex。([android.googlesource.com](https://android.googlesource.com/platform/bionic/%2B/97d1c75ca5125f8e1dc6db32af1d22807fca1950/libc/arch-common/bionic/pthread_atfork.h?utm_source=openai))

---

## 4. `run_in_subcontext` 必须根据状态归属选择

builtin 表中的：

```cpp
{"stf_set", {2, 2, {false, do_stf_set}}},
```

其中：

```cpp
false
```

表示不在 vendor subcontext 中执行。

如果写成：

```cpp
{"stf_set", {2, 2, {true, do_stf_set}}},
```

来自 `/vendor` 或 `/odm` 的命令可能由 `vendor_init` subcontext 进程执行，那么写入的是 **vendor_init 进程里的单例**，主 init 进程之后可能读不到。Android init 的 subcontext 本身是独立进程，并运行在 `vendor_init` SELinux context。([android.googlesource.com](https://android.googlesource.com/platform/system/core/%2B/73f5b65ed439a2484f408ee426dcdff3c538706b/init/subcontext.cpp?utm_source=openai))

如果这张 map 明确属于主 init，建议始终使用：

```cpp
{false, do_stf_set}
```

---

## 5. 不要返回容器内部引用或迭代器

以下接口不安全：

```cpp
// 不推荐。
std::unordered_map<std::string, int>& GetMap();

// 不推荐。
const int& Get(const std::string& key);
```

原因是锁释放后：

- 其他线程可能执行 `erase()`；
- 插入可能触发 rehash；
- 引用或迭代器可能失效；
- 调用方可以不加锁修改容器。

因此 demo 中使用：

```cpp
std::optional<int> Get(...);       // 返回值副本
std::unordered_map<...> Snapshot(); // 返回整体快照
```

如果 map 很大，不适合频繁复制，可以改为回调方式：

```cpp
template <typename Callback>
void ForEach(Callback callback) const {
    std::lock_guard<std::mutex> lock(mutex_);

    for (const auto& [key, value] : values_) {
        callback(key, value);
    }
}
```

但回调执行期间会一直持锁，所以回调内部不能再次访问该单例，也不要进行耗时操作。

---

## 6. 控制 map 大小和输入来源

init 是 PID 1，稳定性要求非常高。不要允许未经限制的 key 不断写入：

```cpp
stf_set arbitrary_key_xxx 1
```

建议至少限制：

- key 最大长度；
- key 字符集；
- map 最大条目数；
- 是否允许覆盖；
- value 的有效范围；
- 哪些 `.rc` 来源可以调用；
- 是否允许 vendor/odm 脚本调用。

例如：

```cpp
constexpr std::size_t kMaxEntryCount = 1024;
constexpr std::size_t kMaxKeyLength = 128;
```

可以把 `Put()` 改成返回 `bool`：

```cpp
bool StfRegistry::Put(std::string key, int value) {
    if (key.empty() || key.size() > kMaxKeyLength) {
        return false;
    }

    std::lock_guard<std::mutex> lock(mutex_);

    const bool already_exists = values_.find(key) != values_.end();
    if (!already_exists && values_.size() >= kMaxEntryCount) {
        return false;
    }

    values_[std::move(key)] = value;
    return true;
}
```

---

## 7. 避免静态初始化顺序问题

不推荐定义文件级全局对象：

```cpp
// 不推荐。
static std::unordered_map<std::string, int> g_values;
static std::mutex g_mutex;
```

如果其他全局对象的构造函数依赖它，容易出现跨编译单元初始化顺序问题。

推荐：

```cpp
StfRegistry& StfRegistry::GetInstance() {
    static StfRegistry* const instance = new StfRegistry();
    return *instance;
}
```

并且不要在其他全局对象的构造函数中调用它，尽量在 second-stage 运行流程中显式首次访问。

---

## 8. 不要在 signal handler 中访问

`unordered_map`、`std::mutex` 和堆分配都不适合在信号处理函数中调用：

```cpp
void SignalHandler(int) {
    // 禁止这样做。
    StfRegistry::GetInstance().Put("signal", 1);
}
```

signal handler 应只做异步信号安全的最小操作，例如写 pipe/eventfd，再由主事件循环处理。

---

## 9. 明确状态清理时机

你需要预先定义以下语义：

- service restart 时是否清除；
- class reset 时是否清除；
- userspace reboot 时是否清除；
- shutdown 开始时是否冻结写入；
- 同一个 init action 重复触发时是覆盖还是累加。

可以显式增加初始化和清理函数：

```cpp
void InitializeStfRegistry() {
    auto& registry = StfRegistry::GetInstance();
    registry.Clear();
    registry.Put("boot_phase", 0);
}
```

然后在 second-stage 初始化位置调用，而不是依赖第一次 `.rc` 命令隐式创建。

---

## 六、最终建议

对于 Android 12 init，推荐采用以下原则：

1. **用封装类，不直接暴露 `unordered_map&`。**
2. **在 second-stage 中初始化。**
3. **builtin 设置为 `run_in_subcontext=false`，确保状态位于主 init。**
4. **不要在 fork 后、exec 前访问。**
5. **即使当前单线程，也保留 mutex，为后续扩展留出安全余量。**
6. **限制 key 长度和总条目数，防止 PID 1 内存无限增长。**
7. **如果需要跨进程共享，不要使用进程内单例，改用 property/Binder/共享内存。**
8. **如果扩展了 init builtin，确保 `host_init_verifier` 也能链接并识别新增命令。**