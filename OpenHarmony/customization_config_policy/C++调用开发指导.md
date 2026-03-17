# libconfig_policy_util C++ 调用开发指导

本文档面向使用 **C++** 接入 `libconfig_policy_util.so` 的开发者，
说明头文件兼容性、RAII 资源管理、封装模式，以及各接口的 C++ 惯用写法。

> 若使用 C 语言接入，请参阅《API调用开发指导.md》。

---

## 一、头文件兼容性

`config_policy_utils.h` 已在内部包含 `extern "C"` 保护，
C++ 源文件可**直接 `#include`，无需任何额外包装**：

```cpp
#include "config_policy_utils.h"   // ← 直接包含，不需要 extern "C" { }
```

头文件中的保护形式（供参考，不需要手动添加）：

```c
#ifdef __cplusplus
extern "C" {
#endif

// ... C 类型和函数声明 ...

#ifdef __cplusplus
}
#endif
```

---

## 二、编译接入

### 2.1 目录结构建议

```
your_project/
├── lib/
│   └── libconfig_policy_util.so
├── include/
│   └── config_policy_utils.h
└── src/
    └── your_code.cpp
```

### 2.2 CMake 接入（推荐）

```cmake
cmake_minimum_required(VERSION 3.14)
project(your_app CXX)

# 要求 C++14 或以上（unique_ptr 自定义 deleter 需要 C++11，lambda deleter 需要 C++14）
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(your_app src/your_code.cpp)

target_include_directories(your_app PRIVATE include/)

target_link_libraries(your_app
    ${CMAKE_SOURCE_DIR}/lib/libconfig_policy_util.so
)

# 运行时 RPATH，避免依赖 LD_LIBRARY_PATH
set_target_properties(your_app PROPERTIES
    BUILD_RPATH  "${CMAKE_SOURCE_DIR}/lib"
    INSTALL_RPATH "/usr/lib"
)
```

### 2.3 g++ 直接编译

```bash
g++ -std=c++14 your_code.cpp \
    -I include/ \
    -L lib/ -lconfig_policy_util \
    -Wl,-rpath,'$ORIGIN/lib' \
    -o your_app
```

---

## 三、C 接口的 C++ 原始调用方式

最直接的方式：与 C 调用完全相同，手动管理内存。
适合迁移现有 C 代码，或对性能极度敏感的热点路径。

```cpp
#include <cstdio>
#include <cstring>
#include "config_policy_utils.h"

void raw_example()
{
    // GetCfgDirList：必须配对调用 FreeCfgDirList
    CfgDir *dirs = GetCfgDirList();
    if (dirs) {
        for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
            if (dirs->paths[i]) {
                printf("[%d] %s\n", i, dirs->paths[i]);
            }
        }
        FreeCfgDirList(dirs);   // 手动释放
    }

    // GetOneCfgFile：返回值指向 buf，无需释放
    char buf[MAX_PATH_LEN] = {};
    char *found = GetOneCfgFile("etc/config.xml", buf, MAX_PATH_LEN);
    if (found) {
        printf("found: %s\n", found);
    }
}
```

---

## 四、使用 `std::unique_ptr` 自动管理生命周期（推荐）

C++11 起可用 `std::unique_ptr` 配合自定义 deleter，
在作用域结束时自动调用对应的 Free 函数，彻底消除手动释放的遗漏风险。

### 4.1 包装 `CfgDir*`

```cpp
#include <memory>
#include "config_policy_utils.h"

// 定义 CfgDir 的智能指针类型
using CfgDirPtr = std::unique_ptr<CfgDir, decltype(&FreeCfgDirList)>;

// 工厂函数：返回带自动释放的智能指针
CfgDirPtr make_cfg_dir()
{
    return CfgDirPtr(GetCfgDirList(), FreeCfgDirList);
    //                ↑ 原始指针        ↑ deleter 函数
}

void example_unique_ptr_dir()
{
    auto dirs = make_cfg_dir();
    if (!dirs) {
        return;   // GetCfgDirList() 失败
    }

    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (dirs->paths[i]) {
            printf("[%d] %s\n", i, dirs->paths[i]);
        }
    }
    // 作用域结束时自动调用 FreeCfgDirList(dirs.get())，无需手动释放
}
```

### 4.2 包装 `CfgFiles*`

```cpp
using CfgFilesPtr = std::unique_ptr<CfgFiles, decltype(&FreeCfgFiles)>;

CfgFilesPtr make_cfg_files(const char *relPath)
{
    return CfgFilesPtr(GetCfgFiles(relPath), FreeCfgFiles);
}

CfgFilesPtr make_cfg_files_ex(const char *relPath, int mode, const char *extra = "")
{
    return CfgFilesPtr(GetCfgFilesEx(relPath, mode, extra), FreeCfgFiles);
}

void example_unique_ptr_files()
{
    auto files = make_cfg_files("etc/plugin/config.xml");
    if (!files) return;

    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (files->paths[i]) {
            printf("  %s\n", files->paths[i]);
        }
    }
    // 自动释放
}
```

### 4.3 C++14 lambda deleter（更简洁的写法）

```cpp
// C++14：用 lambda 作为 deleter，不需要预定义类型别名
auto dirs = std::unique_ptr<CfgDir, void(*)(CfgDir*)>(
    GetCfgDirList(),
    [](CfgDir *p) { FreeCfgDirList(p); }
);
```

---

## 五、C++ 封装类（ConfigPolicy）

对于需要多次调用、希望屏蔽 C 接口细节的场景，
可封装一个 `ConfigPolicy` 类，对外只暴露 `std::string` 和 `std::vector`。

### 5.1 头文件（config_policy.h）

```cpp
#pragma once

#include <string>
#include <vector>
#include "config_policy_utils.h"

/**
 * ConfigPolicy — libconfig_policy_util C++ 封装
 *
 * 所有方法以 std::string / std::vector 返回结果，
 * 内部自动管理 CfgDir / CfgFiles 的内存。
 */
class ConfigPolicy {
public:
    ConfigPolicy() = default;
    ~ConfigPolicy() = default;

    // 禁用拷贝（无状态类，实际上可拷贝，但语义上不需要）
    ConfigPolicy(const ConfigPolicy&) = delete;
    ConfigPolicy& operator=(const ConfigPolicy&) = delete;

    /**
     * 获取所有配置层目录路径（低优先级 → 高优先级）。
     * @return 非空路径的字符串列表；失败时返回空 vector。
     */
    std::vector<std::string> getDirList() const;

    /**
     * 获取最高优先级层中存在的文件路径。
     * @param relPath   配置文件相对路径，如 "etc/telephony/config.json"
     * @param followMode Follow-X 模式，默认不走 Follow-X
     * @param extra      followMode == FOLLOWX_MODE_USER_DEFINED 时的子目录
     * @return 找到的完整路径；未找到返回空字符串。
     */
    std::string getOneCfgFile(const std::string& relPath,
                               int followMode = FOLLOWX_MODE_NO_RULE_FOLLOWED,
                               const std::string& extra = "") const;

    /**
     * 获取所有层中存在的文件路径（低优先级 → 高优先级）。
     * @param relPath    配置文件相对路径
     * @param followMode Follow-X 模式
     * @param extra      自定义子目录（仅 USER_DEFINED 模式使用）
     * @return 各层找到的路径列表（跳过不存在的层）；失败返回空 vector。
     */
    std::vector<std::string> getCfgFiles(const std::string& relPath,
                                          int followMode = FOLLOWX_MODE_NO_RULE_FOLLOWED,
                                          const std::string& extra = "") const;

    /**
     * 获取实际生效的配置层原始字符串（调试用）。
     * 例如："/system:/vendor:/oem"
     * @return 原始层路径字符串；失败返回空字符串。
     */
    std::string getRealPolicyValue() const;
};
```

### 5.2 实现文件（config_policy.cpp）

```cpp
#include "config_policy.h"
#include <memory>

// 内部类型别名
using CfgDirPtr   = std::unique_ptr<CfgDir,   decltype(&FreeCfgDirList)>;
using CfgFilesPtr = std::unique_ptr<CfgFiles,  decltype(&FreeCfgFiles)>;

std::vector<std::string> ConfigPolicy::getDirList() const
{
    CfgDirPtr dirs(GetCfgDirList(), FreeCfgDirList);
    if (!dirs) return {};

    std::vector<std::string> result;
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (dirs->paths[i]) {
            result.emplace_back(dirs->paths[i]);
        }
    }
    return result;
}

std::string ConfigPolicy::getOneCfgFile(const std::string& relPath,
                                         int followMode,
                                         const std::string& extra) const
{
    char buf[MAX_PATH_LEN] = {};
    char *found = GetOneCfgFileEx(relPath.c_str(), buf, MAX_PATH_LEN,
                                   followMode, extra.c_str());
    return found ? std::string(found) : std::string();
}

std::vector<std::string> ConfigPolicy::getCfgFiles(const std::string& relPath,
                                                     int followMode,
                                                     const std::string& extra) const
{
    CfgFilesPtr files(
        GetCfgFilesEx(relPath.c_str(), followMode, extra.c_str()),
        FreeCfgFiles
    );
    if (!files) return {};

    std::vector<std::string> result;
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (files->paths[i]) {
            result.emplace_back(files->paths[i]);
        }
    }
    return result;
}

std::string ConfigPolicy::getRealPolicyValue() const
{
    CfgDirPtr dirs(GetCfgDirList(), FreeCfgDirList);
    if (!dirs || !dirs->realPolicyValue) return {};
    return std::string(dirs->realPolicyValue);
}
```

---

## 六、各接口的 C++ 用法示例

### 6.1 GetCfgDirList — 获取所有配置层目录

**方式A：原始 C 风格（手动管理）**

```cpp
CfgDir *dirs = GetCfgDirList();
if (dirs) {
    // ... 使用 ...
    FreeCfgDirList(dirs);
}
```

**方式B：`unique_ptr` 自动管理（推荐）**

```cpp
#include <memory>

CfgDirPtr dirs(GetCfgDirList(), FreeCfgDirList);
if (!dirs) {
    std::cerr << "GetCfgDirList failed\n";
    return;
}

for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
    if (dirs->paths[i]) {
        std::cout << "[" << i << "] " << dirs->paths[i] << "\n";
    }
}
// 自动释放，无需手动调用 FreeCfgDirList
```

**方式C：封装类**

```cpp
ConfigPolicy policy;
auto layers = policy.getDirList();   // 返回 std::vector<std::string>
for (const auto& layer : layers) {
    std::cout << layer << "\n";
}
```

---

### 6.2 GetOneCfgFile / GetOneCfgFileEx — 最高优先级文件路径

**原始调用**

```cpp
char buf[MAX_PATH_LEN] = {};
// 不走 Follow-X
char *p = GetOneCfgFileEx("etc/telephony/config.json",
                            buf, MAX_PATH_LEN,
                            FOLLOWX_MODE_NO_RULE_FOLLOWED, "");
if (p) {
    // p == buf，指向同一缓冲区
    std::string path(p);           // 需要持久保存时，构造 std::string
    // 注意：buf 必须在使用 path 之前有效（这里 path 已拷贝，buf 可释放）
}
// 无需 free(p)
```

**封装类调用**

```cpp
ConfigPolicy policy;

// 不走 Follow-X
std::string path = policy.getOneCfgFile("etc/telephony/config.json");

// SIM 卡1 运营商专属配置
std::string simPath = policy.getOneCfgFile(
    "etc/telephony/OpkeyInfo.json",
    FOLLOWX_MODE_SIM_1
);

// 自定义运营商子目录
std::string customPath = policy.getOneCfgFile(
    "etc/config.xml",
    FOLLOWX_MODE_USER_DEFINED,
    "carrier/46060"
);

if (path.empty()) {
    std::cerr << "配置文件不存在\n";
}
```

---

### 6.3 GetCfgFiles / GetCfgFilesEx — 所有层的文件路径

**原始调用**

```cpp
CfgFilesPtr files(
    GetCfgFilesEx("etc/plugin/rules.xml",
                   FOLLOWX_MODE_NO_RULE_FOLLOWED, ""),
    FreeCfgFiles
);

if (files) {
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (files->paths[i]) {
            std::cout << files->paths[i] << "\n";
        }
    }
}
// 自动释放
```

**封装类调用**

```cpp
ConfigPolicy policy;
auto allFiles = policy.getCfgFiles("etc/plugin/rules.xml");

// 按低→高优先级顺序合并（后面的层覆盖前面的）
for (const auto& f : allFiles) {
    load_and_merge(f);
}
```

---

### 6.4 Follow-X 模式的 C++ 常量

```cpp
// 以下常量定义在 config_policy_utils.h 中，C++ 中直接使用
constexpr int NO_FOLLOW    = FOLLOWX_MODE_NO_RULE_FOLLOWED;  // 1
constexpr int FOLLOW_SIM1  = FOLLOWX_MODE_SIM_1;             // 11
constexpr int FOLLOW_SIM2  = FOLLOWX_MODE_SIM_2;             // 12
constexpr int FOLLOW_UDEF  = FOLLOWX_MODE_USER_DEFINED;      // 100
```

---

## 七、内存管理规则（C++ 视角）

### 7.1 CfgDir 的注意事项

`CfgDir::paths[]` 指向 `realPolicyValue` 字符串内部，**不是独立分配**：

```cpp
// ✗ 错误：不能将 paths[i] 赋给 unique_ptr 管理
std::unique_ptr<char> p(dirs->paths[0]);  // 导致 double-free

// ✓ 正确：直接构造 std::string（深拷贝）
std::string layer(dirs->paths[0]);        // 已拷贝，与原指针独立
```

**用 unique_ptr 管理 CfgDir 本身（整体），不要管理其内部的 paths 元素：**

```cpp
CfgDirPtr dirs(GetCfgDirList(), FreeCfgDirList);  // ✓ 管理整个 CfgDir
// dirs->paths[i] 在 dirs 存活期间使用，不要单独管理
```

### 7.2 CfgFiles 的注意事项

`CfgFiles::paths[]` 各元素是独立 `strdup()` 分配，可安全拷贝到 `std::string`：

```cpp
CfgFilesPtr files(GetCfgFiles("etc/cfg.xml"), FreeCfgFiles);
if (files) {
    // ✓ 将需要的路径拷贝到 std::string，之后 files 随时可释放
    std::string saved;
    if (files->paths[2]) {
        saved = files->paths[2];  // std::string 构造即深拷贝
    }
    // files 超出作用域后自动释放，saved 仍然有效
}
```

### 7.3 GetOneCfgFile 返回值的作用域

返回值指向栈上 `buf`，**必须在 `buf` 的作用域内使用，或立即转为 `std::string`**：

```cpp
// ✗ 危险：返回指向局部变量的指针
const char* get_path_bad() {
    char buf[MAX_PATH_LEN] = {};
    return GetOneCfgFile("etc/cfg.xml", buf, MAX_PATH_LEN);
    // buf 已销毁，返回悬空指针
}

// ✓ 正确：转为 std::string 再返回
std::string get_path_good() {
    char buf[MAX_PATH_LEN] = {};
    char *p = GetOneCfgFile("etc/cfg.xml", buf, MAX_PATH_LEN);
    return p ? std::string(p) : std::string();  // 深拷贝
}
```

---

## 八、完整示例程序

```cpp
/*
 * example.cpp — libconfig_policy_util C++ 接入示例
 *
 * 编译：
 *   g++ -std=c++14 example.cpp config_policy.cpp \
 *       -I include/ -L lib/ -lconfig_policy_util \
 *       -Wl,-rpath,'$ORIGIN/lib' -o example
 */
#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include "config_policy_utils.h"
#include "config_policy.h"   // 封装类（可选）

// ── 类型别名 ─────────────────────────────────────────────────────────
using CfgDirPtr   = std::unique_ptr<CfgDir,   decltype(&FreeCfgDirList)>;
using CfgFilesPtr = std::unique_ptr<CfgFiles,  decltype(&FreeCfgFiles)>;

// ── 示例1：使用封装类查看配置层 ──────────────────────────────────────
static void demo_wrapper_class()
{
    std::cout << "\n=== 示例1：封装类接口 ===\n";

    ConfigPolicy policy;

    // 获取所有层目录
    auto layers = policy.getDirList();
    std::cout << "配置层目录（低→高优先级）:\n";
    for (const auto& layer : layers) {
        std::cout << "  " << layer << "\n";
    }

    // 调试：查看原始参数字符串
    std::string raw = policy.getRealPolicyValue();
    std::cout << "原始参数值: " << (raw.empty() ? "(default)" : raw) << "\n";
}

// ── 示例2：使用 unique_ptr 直接调用 C 接口 ──────────────────────────
static void demo_unique_ptr()
{
    std::cout << "\n=== 示例2：unique_ptr 自动管理 CfgDir ===\n";

    CfgDirPtr dirs(GetCfgDirList(), FreeCfgDirList);
    if (!dirs) {
        std::cerr << "GetCfgDirList() failed\n";
        return;
    }

    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (dirs->paths[i]) {
            std::cout << "  [" << i << "] " << dirs->paths[i] << "\n";
        }
    }
    // 作用域结束，自动调用 FreeCfgDirList
}

// ── 示例3：最高优先级文件查找 ────────────────────────────────────────
static void demo_get_one_file()
{
    std::cout << "\n=== 示例3：最高优先级文件查找 ===\n";

    ConfigPolicy policy;

    // 不走 Follow-X
    std::string path = policy.getOneCfgFile("etc/telephony/config.json");
    if (path.empty()) {
        std::cout << "  文件不存在于任何层\n";
    } else {
        std::cout << "  找到: " << path << "\n";
    }

    // SIM 卡1 运营商专属配置
    std::string simPath = policy.getOneCfgFile(
        "etc/telephony/OpkeyInfo.json",
        FOLLOWX_MODE_SIM_1
    );
    std::cout << "  SIM1 专属: " << (simPath.empty() ? "(不存在)" : simPath) << "\n";
}

// ── 示例4：收集所有层的配置文件 ─────────────────────────────────────
static void demo_get_all_files()
{
    std::cout << "\n=== 示例4：所有层的配置文件 ===\n";

    // 方式A：封装类（最简洁）
    ConfigPolicy policy;
    auto files = policy.getCfgFiles("etc/plugin/rules.xml");
    if (files.empty()) {
        std::cout << "  任何层均无此文件\n";
        return;
    }
    for (const auto& f : files) {
        std::cout << "  " << f << "\n";
    }

    // 方式B：直接调用 + unique_ptr
    CfgFilesPtr raw(
        GetCfgFilesEx("etc/plugin/rules.xml",
                       FOLLOWX_MODE_NO_RULE_FOLLOWED, ""),
        FreeCfgFiles
    );
    if (raw) {
        for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
            if (raw->paths[i]) {
                std::string p(raw->paths[i]);  // 立即深拷贝，脱离 raw 的生命周期
                // ... 使用 p ...
            }
        }
    }
    // raw 超出作用域，自动调用 FreeCfgFiles
}

// ── 示例5：GetOneCfgFile 返回值的正确处理 ────────────────────────────
static std::string get_config_path(const std::string& relPath)
{
    char buf[MAX_PATH_LEN] = {};
    char *p = GetOneCfgFile(relPath.c_str(), buf, MAX_PATH_LEN);
    // 转为 std::string 再返回，buf 栈内存安全离开作用域
    return p ? std::string(p) : std::string();
}

static void demo_buf_safety()
{
    std::cout << "\n=== 示例5：GetOneCfgFile 返回值安全处理 ===\n";

    std::string path = get_config_path("etc/config.xml");
    // path 是独立的 std::string，buf 已销毁但 path 完全有效
    std::cout << "  " << (path.empty() ? "(未找到)" : path) << "\n";
}

int main()
{
    demo_wrapper_class();
    demo_unique_ptr();
    demo_get_one_file();
    demo_get_all_files();
    demo_buf_safety();
    return 0;
}
```

---

## 九、常见问题（C++ 特有）

### Q1：能否用 `std::shared_ptr` 代替 `unique_ptr`？

可以，但语义上 `unique_ptr` 更准确（每个查询结果独占资源）：

```cpp
// unique_ptr（推荐）
std::unique_ptr<CfgDir, decltype(&FreeCfgDirList)>
    dirs(GetCfgDirList(), FreeCfgDirList);

// shared_ptr（可用，但有额外引用计数开销）
std::shared_ptr<CfgDir>
    dirs(GetCfgDirList(), FreeCfgDirList);
```

---

### Q2：能否在 `std::string` 构造之前检查路径长度？

```cpp
char buf[MAX_PATH_LEN] = {};
char *p = GetOneCfgFile("etc/cfg.xml", buf, MAX_PATH_LEN);
if (p) {
    size_t len = std::strlen(p);
    if (len >= MAX_PATH_LEN - 1) {
        // 路径可能被截断（实际长度 >= 255 字节，极少见）
        std::cerr << "warning: path may be truncated\n";
    }
    std::string path(p, len);
}
```

---

### Q3：能否把 `CfgDir*` 存入 `std::vector`？

不建议直接存裸指针。用 `unique_ptr` 或提前转为 `std::vector<std::string>`：

```cpp
// ✗ 危险：裸指针语义不明确，容易忘记释放
std::vector<CfgDir*> v;
v.push_back(GetCfgDirList());

// ✓ 方式1：unique_ptr 存入 vector（C++14）
using CfgDirPtr = std::unique_ptr<CfgDir, decltype(&FreeCfgDirList)>;
std::vector<CfgDirPtr> safe_vec;
safe_vec.emplace_back(GetCfgDirList(), FreeCfgDirList);

// ✓ 方式2：立即转为字符串 vector，最简洁
ConfigPolicy policy;
std::vector<std::string> layers = policy.getDirList();
```

---

### Q4：多线程下能否共用一个 `ConfigPolicy` 实例？

`ConfigPolicy` 本身无成员变量，所有方法都是无状态调用。
多线程并发调用是安全的，但每次查询内部使用的 `buf` 是**方法内的局部变量**，
天然线程隔离，无需外部加锁：

```cpp
// 同一 ConfigPolicy 实例可在多线程中并发使用
ConfigPolicy policy;   // 全局或共享

void thread_func() {
    // 每次调用在栈上分配独立 buf，无竞争
    std::string p = policy.getOneCfgFile("etc/cfg.xml");
}
```

---

## 十、接口速查表（C++ 视角）

| C 接口 | C++ 推荐用法 | 返回类型 | 释放方式 |
|--------|-------------|---------|---------|
| `GetCfgDirList()` | `CfgDirPtr` / `policy.getDirList()` | `unique_ptr` / `vector<string>` | 自动 |
| `GetOneCfgFile()` | `policy.getOneCfgFile()` | `string`（空串表示未找到） | 无需 |
| `GetOneCfgFileEx()` | `policy.getOneCfgFile(path, mode)` | `string` | 无需 |
| `GetCfgFiles()` | `CfgFilesPtr` / `policy.getCfgFiles()` | `unique_ptr` / `vector<string>` | 自动 |
| `GetCfgFilesEx()` | `policy.getCfgFiles(path, mode)` | `vector<string>` | 无需 |
| `FreeCfgDirList()` | 由 `unique_ptr` deleter 自动调用 | — | — |
| `FreeCfgFiles()` | 由 `unique_ptr` deleter 自动调用 | — | — |
