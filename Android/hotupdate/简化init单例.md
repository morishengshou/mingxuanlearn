如果 `unordered_map` 的内容在初始化完成后**只查询、不修改**，最简单的方式是使用：

- 函数内静态对象；
- 返回 `const std::unordered_map&`；
- 不提供任何修改接口；
- 查询使用 `find()`，不要使用 `operator[]`。

## 1. 头文件

### `stf_map.h`

```cpp
#pragma once

#include <string>
#include <unordered_map>

namespace android {
namespace init {

using StfMap = std::unordered_map<std::string, int>;

// 获取进程内唯一、只读的 map。
const StfMap& GetStfMap();

// 查询接口。
bool GetStfValue(const std::string& key, int* value);

}  // namespace init
}  // namespace android
```

## 2. 实现文件

### `stf_map.cpp`

```cpp
#include "stf_map.h"

namespace android {
namespace init {

const StfMap& GetStfMap() {
    // C++11 起，函数内 static 的初始化是线程安全的。
    static const StfMap map = {
            {"boot_phase", 1},
            {"system_server", 2},
            {"surfaceflinger", 3},
            {"zygote", 4},
    };

    return map;
}

bool GetStfValue(const std::string& key, int* value) {
    if (value == nullptr) {
        return false;
    }

    const auto& map = GetStfMap();
    const auto it = map.find(key);

    if (it == map.end()) {
        return false;
    }

    *value = it->second;
    return true;
}

}  // namespace init
}  // namespace android
```

这种实现中：

```cpp
static const StfMap map
```

只会在当前进程中第一次调用 `GetStfMap()` 时初始化一次。初始化完成后，由于只能获取 `const` 引用，调用方无法正常修改它。

---

## 3. 使用样例

```cpp
#include "stf_map.h"

#include <android-base/logging.h>

namespace android {
namespace init {

void TestStfMap() {
    int value = 0;

    if (GetStfValue("zygote", &value)) {
        LOG(INFO) << "zygote value=" << value;
    } else {
        LOG(WARNING) << "zygote not found";
    }

    if (GetStfValue("unknown_service", &value)) {
        LOG(INFO) << "unknown_service value=" << value;
    } else {
        LOG(WARNING) << "unknown_service not found";
    }
}

}  // namespace init
}  // namespace android
```

也可以直接获取 map 查询：

```cpp
const auto& map = GetStfMap();

const auto it = map.find("surfaceflinger");
if (it != map.end()) {
    LOG(INFO) << "surfaceflinger value=" << it->second;
}
```

---

## 4. 在 init builtin 中使用

例如在 `builtins.cpp` 中增加一个查询命令：

```cpp
#include "stf_map.h"

#include <android-base/logging.h>
```

实现 builtin：

```cpp
static Result<void> do_stf_query(const BuiltinArguments& args) {
    int value = 0;

    if (!GetStfValue(args[1], &value)) {
        return Error() << "STF key not found: " << args[1];
    }

    LOG(INFO) << "STF query: key=" << args[1]
              << ", value=" << value;

    return {};
}
```

在 builtin 表中注册：

```cpp
{"stf_query", {1, 1, {false, do_stf_query}}},
```

然后在 `.rc` 文件中使用：

```rc
on boot
    stf_query zygote
    stf_query surfaceflinger
```

这里建议保持：

```cpp
run_in_subcontext = false
```

也就是：

```cpp
{false, do_stf_query}
```

这样命令会在主 init 进程中执行。

---

## 5. 如果初始化内容比较复杂

可以通过 lambda 初始化：

```cpp
const StfMap& GetStfMap() {
    static const StfMap map = [] {
        StfMap result;

        result.emplace("boot_phase", 1);
        result.emplace("system_server", 2);
        result.emplace("surfaceflinger", 3);
        result.emplace("zygote", 4);

        return result;
    }();

    return map;
}
```

这仍然只会初始化一次，之后只读。

---

## 6. 注意事项

### 不要使用 `operator[]`

查询时不要写：

```cpp
auto value = map["zygote"];
```

因为非 `const` map 的 `operator[]` 在 key 不存在时会插入新元素。应使用：

```cpp
const auto it = map.find("zygote");
if (it != map.end()) {
    int value = it->second;
}
```

或者使用前面的：

```cpp
int value;
if (GetStfValue("zygote", &value)) {
    // 查询成功
}
```

### 不需要加锁

满足以下条件时，不需要额外的 `mutex`：

1. map 通过函数内 `static` 初始化；
2. 初始化后绝不修改；
3. 不向外返回非 `const` 引用或指针；
4. 所有线程只调用只读查询操作。

函数内静态变量的首次初始化本身是线程安全的，初始化完成后的并发只读查询也不需要加锁。

### 仍然只是进程内单例

该 map 只在当前进程中唯一：

- 主 init 进程有自己的 map；
- `vendor_init` subcontext 有自己的 map；
- fork 后的子进程得到父进程内存快照；
- first-stage 到 second-stage 发生 `exec` 后会重新初始化。

如果数据只用于 Android init 的 second-stage 主进程，上面的简单实现就足够了。