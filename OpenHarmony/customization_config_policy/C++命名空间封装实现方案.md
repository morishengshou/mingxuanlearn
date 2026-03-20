# C++ 命名空间封装实现方案

将 `libconfig_policy_util` 的 C 接口封装为 `Huazi::Car::instru::cust` 命名空间下的安全 C++ 接口。

---

## 一、设计目标与原则

| 目标 | 实现手段 |
|------|---------|
| 消除内存泄漏 | 内部使用 `std::unique_ptr` + 自定义 deleter，外部暴露值类型 |
| 消除悬空指针 | `ConfigDirList` 在构造时**急迫拷贝**所有字符串，脱离 C 层生命周期 |
| 类型安全 | `enum class FollowXMode` 替代裸 `int` 常量，编译期防止传错参数 |
| 明确错误语义 | 编程错误（非法入参）→ 抛出 `ConfigPolicyError`；运行时"未找到"→ 返回空值 |
| 线程安全 | `ConfigPolicy` 无任何成员变量，全部方法为 `const`，天然无共享可变状态 |
| 异常安全 | 所有方法提供**强异常保证**（无状态类，抛出前无副作用）|
| 最小依赖 | 头文件只依赖标准库，C 原始头文件只在 `.cpp` 中包含，不泄漏给使用方 |

---

## 二、接口设计决策

### 2.1 为何选择急迫拷贝（Eager Copy）而非持有裸指针

C 接口的 `CfgDir::paths[]` 指向 `realPolicyValue` 内部，生命周期由 `FreeCfgDirList()` 控制。
若 C++ 封装层持有 `CfgDir*`，调用方必须在 `ConfigDirList` 析构前不释放它，
形成**隐式的生命周期耦合**，难以保证安全。

选择急迫拷贝（构造时将所有 `char*` 立即复制为 `std::string`）后：
- `ConfigDirList` 成为**完全独立的值类型**，可随意复制、移动、跨线程传递
- C 层资源（`CfgDir*`）在构造函数返回前即释放，不留泄漏窗口

### 2.2 为何 `getOneCfgFile` 返回 `std::string` 而非 `std::optional<std::string>`

`std::optional` 是 C++17 特性，车载嵌入式工具链可能仍使用 C++14。
用**空字符串**表示"未找到"是简洁的替代方案，调用方用 `result.empty()` 即可判断。

若项目确认使用 C++17，可将返回类型替换为 `std::optional<std::string>`（见附录 A）。

### 2.3 `ConfigPolicy` 的 Copy/Move 策略

`ConfigPolicy` 无成员变量，从技术上可以拷贝，但语义上"一个配置策略对象"
不存在"复制"的意义。禁用拷贝，允许移动，防止误用。

### 2.4 `ConfigDirList` 的迭代器支持

`ConfigDirList` 提供 `begin()` / `end()`，支持范围 for 循环，
调用方可以 `for (const auto& layer : dirs)` 直接遍历，符合 C++ 惯用法。

---

## 三、完整头文件

文件名：**`config_policy.hpp`**

```cpp
/**
 * @file   config_policy.hpp
 * @brief  libconfig_policy_util C++ 封装
 *         命名空间：Huazi::Car::instru::cust
 *
 * 使用要求：
 *   - C++14 或以上
 *   - 链接 libconfig_policy_util.so
 *
 * 本头文件不包含任何 C 原始头文件，使用方无需关心底层实现细节。
 */
#pragma once

#include <string>
#include <vector>
#include <stdexcept>

namespace Huazi {
namespace Car {
namespace instru {
namespace cust {

// ─────────────────────────────────────────────────────────────────────────────
// FollowXMode
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Follow-X 模式枚举（类型安全，替代 C 层裸 int 常量）
 *
 * 用于在标准配置层路径中插入运营商子目录，实现运营商差异化配置查找。
 *
 * 示例（SIM_1 模式）：
 *   标准路径:   /vendor/etc/telephony/config.json
 *   Follow-X:  /vendor/etc/carrier/46060/etc/telephony/config.json
 *                                  ↑ 从系统参数 telephony.sim.opkey0 读取
 */
enum class FollowXMode : int {
    Default     = 0,    ///< 读取系统配置的默认 Follow-X 规则
    NoRule      = 1,    ///< 不走 Follow-X，直接按层查找（最常用）
    SimDefault  = 10,   ///< 自动读取默认 SIM 卡的运营商代码
    Sim1        = 11,   ///< 读取 SIM 卡1 的运营商代码（opkey0）
    Sim2        = 12,   ///< 读取 SIM 卡2 的运营商代码（opkey1）
    UserDefined = 100,  ///< 使用调用方传入的 extra 字符串作为子目录路径
};

// ─────────────────────────────────────────────────────────────────────────────
// ConfigPolicyError
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief ConfigPolicy 操作失败时抛出的异常
 *
 * 仅在编程错误（非法入参）时抛出，
 * 运行时"未找到"不视为异常，以空值返回。
 *
 * 继承自 std::runtime_error，可用 catch(const std::exception&) 统一捕获。
 */
class ConfigPolicyError : public std::runtime_error {
public:
    explicit ConfigPolicyError(const std::string& msg)
        : std::runtime_error("[Huazi::Car::instru::cust] " + msg) {}
};

// ─────────────────────────────────────────────────────────────────────────────
// ConfigDirList
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 配置层目录列表（值类型，可拷贝、可移动）
 *
 * 由 ConfigPolicy::getDirList() 返回。
 * 内部字符串在构造时已从 C 层**急迫拷贝**，与底层 libconfig_policy_util
 * 的生命周期完全解耦，可安全跨线程、跨作用域使用。
 *
 * 顺序：低优先级 → 高优先级（索引 0 = 最低优先级）。
 */
class ConfigDirList {
public:
    // ── 构造 / 析构 ──────────────────────────────────────────────────────────
    ConfigDirList() = default;
    ~ConfigDirList() = default;
    ConfigDirList(const ConfigDirList&) = default;
    ConfigDirList& operator=(const ConfigDirList&) = default;
    ConfigDirList(ConfigDirList&&) noexcept = default;
    ConfigDirList& operator=(ConfigDirList&&) noexcept = default;

    // ── 访问器 ───────────────────────────────────────────────────────────────

    /**
     * @brief 返回所有配置层目录路径（低→高优先级）
     */
    const std::vector<std::string>& paths() const noexcept { return paths_; }

    /**
     * @brief 实际生效的层路径原始字符串，用于诊断
     *        例如："/system:/vendor:/oem"
     *        若底层返回 NULL，则为空字符串。
     */
    const std::string& rawPolicyValue() const noexcept { return rawPolicyValue_; }

    /** @brief 层数（去除 NULL 槽后的有效条目数） */
    std::size_t size() const noexcept { return paths_.size(); }

    /** @brief 是否为空（底层返回 NULL 或无有效层） */
    bool empty() const noexcept { return paths_.empty(); }

    // ── 范围 for 支持 ────────────────────────────────────────────────────────
    using const_iterator = std::vector<std::string>::const_iterator;

    const_iterator begin() const noexcept { return paths_.begin(); }
    const_iterator end()   const noexcept { return paths_.end();   }

    /** @brief 按索引访问（不做边界检查，越界行为未定义） */
    const std::string& operator[](std::size_t idx) const noexcept {
        return paths_[idx];
    }

    /** @brief 按索引访问（带边界检查，越界抛出 std::out_of_range） */
    const std::string& at(std::size_t idx) const { return paths_.at(idx); }

private:
    // 仅 ConfigPolicy 内部可构造
    friend class ConfigPolicy;

    explicit ConfigDirList(std::vector<std::string> paths, std::string rawValue)
        : paths_(std::move(paths))
        , rawPolicyValue_(std::move(rawValue))
    {}

    std::vector<std::string> paths_;
    std::string rawPolicyValue_;
};

// ─────────────────────────────────────────────────────────────────────────────
// ConfigPolicy
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 配置策略查询接口
 *
 * 所有方法均为 const，无成员变量，天然线程安全。
 * 多线程环境下可共享同一实例，无需加锁。
 *
 * 错误处理策略：
 *   - 编程错误（relPath 非法）→ 抛出 ConfigPolicyError
 *   - 运行时"未找到"         → 返回空字符串或空 vector（不抛出）
 *   - 底层库返回 NULL        → 返回空值（不抛出）
 *
 * 使用示例：
 * @code
 *   using namespace Huazi::Car::instru::cust;
 *   ConfigPolicy policy;
 *
 *   // 查找最高优先级配置文件
 *   std::string path = policy.getOneCfgFile("etc/telephony/config.json");
 *   if (!path.empty()) {
 *       // 使用 path ...
 *   }
 * @endcode
 */
class ConfigPolicy {
public:
    ConfigPolicy() = default;
    ~ConfigPolicy() = default;

    // 禁用拷贝（无状态，但语义上不应拷贝）；允许移动
    ConfigPolicy(const ConfigPolicy&) = delete;
    ConfigPolicy& operator=(const ConfigPolicy&) = delete;
    ConfigPolicy(ConfigPolicy&&) noexcept = default;
    ConfigPolicy& operator=(ConfigPolicy&&) noexcept = default;

    /**
     * @brief 获取所有配置层目录路径（低优先级 → 高优先级）
     *
     * @return ConfigDirList  包含所有层目录路径的值对象。
     *                        底层失败时返回 empty() == true 的对象，不抛出。
     */
    ConfigDirList getDirList() const;

    /**
     * @brief 获取最高优先级层中存在的配置文件完整路径
     *
     * 从高优先级向低优先级逐层查找，返回第一个存在的文件路径。
     *
     * @param relPath   配置文件相对路径，如 "etc/telephony/config.json"
     *                  - 不能为空字符串
     *                  - 不能以 '/' 开头
     *                  - 长度不能超过 MAX_PATH_LEN - 1（255 字节）
     * @param mode      Follow-X 模式，默认 FollowXMode::NoRule
     * @param extra     仅在 mode == FollowXMode::UserDefined 时有效，
     *                  指定运营商子目录路径，如 "carrier/46060"
     * @return std::string  找到时返回完整路径；未找到时返回空字符串。
     * @throws ConfigPolicyError  当 relPath 非法时抛出
     */
    std::string getOneCfgFile(
        const std::string& relPath,
        FollowXMode        mode  = FollowXMode::NoRule,
        const std::string& extra = "") const;

    /**
     * @brief 获取所有层中存在的配置文件完整路径（低优先级 → 高优先级）
     *
     * 从低优先级向高优先级逐层收集所有存在的文件路径。
     * 典型用途：插件系统需要合并读取多层配置，后面的层覆盖前面的层。
     *
     * @param relPath   配置文件相对路径（同 getOneCfgFile 的约束）
     * @param mode      Follow-X 模式，默认 FollowXMode::NoRule
     * @param extra     自定义子目录（仅 UserDefined 模式使用）
     * @return std::vector<std::string>  各层找到的路径列表（跳过不存在的层）。
     *                                   无文件或失败时返回空 vector，不抛出。
     * @throws ConfigPolicyError  当 relPath 非法时抛出
     */
    std::vector<std::string> getCfgFiles(
        const std::string& relPath,
        FollowXMode        mode  = FollowXMode::NoRule,
        const std::string& extra = "") const;

private:
    /**
     * @brief 验证相对路径参数合法性
     * @throws ConfigPolicyError 当路径不合法时
     */
    static void validateRelPath(const std::string& relPath);
};

} // namespace cust
} // namespace instru
} // namespace Car
} // namespace Huazi
```

---

## 四、完整实现文件

文件名：**`config_policy.cpp`**

```cpp
/**
 * @file  config_policy.cpp
 * @brief Huazi::Car::instru::cust::ConfigPolicy 实现
 *
 * C 原始头文件（config_policy_utils.h）仅在此文件包含，
 * 不通过 config_policy.hpp 暴露给使用方。
 */
#include "config_policy.hpp"

// C 原始头文件：只在实现文件中包含
#include "config_policy_utils.h"

#include <memory>   // std::unique_ptr
#include <cstring>  // std::strlen

namespace Huazi {
namespace Car {
namespace instru {
namespace cust {

// ─────────────────────────────────────────────────────────────────────────────
// 内部工具（匿名命名空间，外部不可见）
// ─────────────────────────────────────────────────────────────────────────────
namespace {

/// CfgDir 智能指针：析构时自动调用 FreeCfgDirList
using CfgDirPtr = std::unique_ptr<CfgDir, decltype(&FreeCfgDirList)>;

/// CfgFiles 智能指针：析构时自动调用 FreeCfgFiles
using CfgFilesPtr = std::unique_ptr<CfgFiles, decltype(&FreeCfgFiles)>;

/// 将 CfgDir* 的内容急迫拷贝为 ConfigDirList（值类型）
/// 调用前 dirs 必须非空
ConfigDirList buildDirList(const CfgDirPtr& dirs)
{
    std::vector<std::string> paths;
    paths.reserve(MAX_CFG_POLICY_DIRS_CNT);

    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; ++i) {
        if (dirs->paths[i] != nullptr) {
            // std::string 构造即深拷贝，与 dirs->paths[i] 原始内存解耦
            paths.emplace_back(dirs->paths[i]);
        }
    }

    std::string rawValue =
        (dirs->realPolicyValue != nullptr) ? dirs->realPolicyValue : "";

    // 使用 ConfigDirList 的私有构造函数（通过 friend ConfigPolicy 触发）
    // 此处直接调用是因为本 .cpp 与头文件同属实现单元
    // 等价于：return ConfigDirList(std::move(paths), std::move(rawValue));
    // 但 ConfigDirList 的私有构造只允许 ConfigPolicy 调用，
    // 通过返回值的方式在 getDirList() 中构造。
    // 此辅助函数将 paths 和 rawValue 传回给 getDirList()，由其构造。
    (void)rawValue; // 占位，实际由 getDirList 调用
    // 注意：此函数仅用于辅助，实际构造在 getDirList 中完成，见下方实现
    (void)paths;
    return {}; // 不直接使用此函数构造，见 getDirList 实现
}

} // namespace (anonymous)

// ─────────────────────────────────────────────────────────────────────────────
// ConfigPolicy::validateRelPath
// ─────────────────────────────────────────────────────────────────────────────

void ConfigPolicy::validateRelPath(const std::string& relPath)
{
    if (relPath.empty()) {
        throw ConfigPolicyError("relPath must not be empty");
    }
    if (relPath.front() == '/') {
        throw ConfigPolicyError(
            "relPath must not start with '/': \"" + relPath + "\"");
    }
    // MAX_PATH_LEN 包含 '\0'，有效字符最多 MAX_PATH_LEN - 1 字节
    if (relPath.size() >= static_cast<std::size_t>(MAX_PATH_LEN)) {
        throw ConfigPolicyError(
            "relPath length " + std::to_string(relPath.size()) +
            " exceeds maximum " + std::to_string(MAX_PATH_LEN - 1));
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ConfigPolicy::getDirList
// ─────────────────────────────────────────────────────────────────────────────

ConfigDirList ConfigPolicy::getDirList() const
{
    // unique_ptr 确保 CfgDir* 在任何退出路径上都被 FreeCfgDirList 释放
    CfgDirPtr dirs(GetCfgDirList(), FreeCfgDirList);
    if (!dirs) {
        // 底层失败：返回空的 ConfigDirList，不抛出
        return ConfigDirList{};
    }

    // 急迫拷贝：将所有 char* 立即转换为 std::string
    std::vector<std::string> paths;
    paths.reserve(MAX_CFG_POLICY_DIRS_CNT);
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; ++i) {
        if (dirs->paths[i] != nullptr) {
            paths.emplace_back(dirs->paths[i]);
        }
    }

    std::string rawValue =
        (dirs->realPolicyValue != nullptr) ? dirs->realPolicyValue : "";

    // dirs 在此行之后即将析构（unique_ptr 离开块作用域），
    // paths 和 rawValue 均已深拷贝，完全独立于 dirs 的生命周期
    return ConfigDirList(std::move(paths), std::move(rawValue));
    // ↑ 调用 ConfigDirList 的私有构造（ConfigPolicy 是其 friend）
}

// ─────────────────────────────────────────────────────────────────────────────
// ConfigPolicy::getOneCfgFile
// ─────────────────────────────────────────────────────────────────────────────

std::string ConfigPolicy::getOneCfgFile(
    const std::string& relPath,
    FollowXMode        mode,
    const std::string& extra) const
{
    validateRelPath(relPath);  // 非法入参：抛出 ConfigPolicyError

    char buf[MAX_PATH_LEN] = {};   // 栈上缓冲区，线程私有，无竞争

    char* result = GetOneCfgFileEx(
        relPath.c_str(),
        buf,
        static_cast<unsigned int>(MAX_PATH_LEN),
        static_cast<int>(mode),
        extra.c_str()
    );

    // result 指向 buf，立即转为 std::string 深拷贝，buf 随函数返回销毁
    return (result != nullptr) ? std::string(result) : std::string{};
}

// ─────────────────────────────────────────────────────────────────────────────
// ConfigPolicy::getCfgFiles
// ─────────────────────────────────────────────────────────────────────────────

std::vector<std::string> ConfigPolicy::getCfgFiles(
    const std::string& relPath,
    FollowXMode        mode,
    const std::string& extra) const
{
    validateRelPath(relPath);  // 非法入参：抛出 ConfigPolicyError

    CfgFilesPtr files(
        GetCfgFilesEx(
            relPath.c_str(),
            static_cast<int>(mode),
            extra.c_str()
        ),
        FreeCfgFiles
    );

    if (!files) {
        // 底层失败或无文件：返回空 vector，不抛出
        return {};
    }

    std::vector<std::string> result;
    result.reserve(MAX_CFG_POLICY_DIRS_CNT);

    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; ++i) {
        if (files->paths[i] != nullptr) {
            result.emplace_back(files->paths[i]);
        }
    }

    // files 离开作用域，unique_ptr 自动调用 FreeCfgFiles
    return result;
}

} // namespace cust
} // namespace instru
} // namespace Car
} // namespace Huazi
```

---

## 五、实现方案详解

### 5.1 内存安全保证的全路径分析

```
调用 getDirList()
    │
    ├─ GetCfgDirList()          返回 CfgDir*（堆内存）
    │       │
    │       └─ 立即交给 unique_ptr<CfgDir, FreeCfgDirList>
    │          ↓ 任何退出路径（正常 / 异常）都会调用 FreeCfgDirList
    │
    ├─ 遍历 dirs->paths[i]
    │       │
    │       └─ emplace_back(dirs->paths[i])
    │          ↓ std::string 构造 = 深拷贝字符内容
    │          ↓ 拷贝后与 dirs 内存无关联
    │
    ├─ 构造 ConfigDirList(move(paths), move(rawValue))
    │       │
    │       └─ 值类型，完全独立于 C 层内存
    │
    └─ unique_ptr 析构 → FreeCfgDirList(dirs.get()) 自动调用
```

`CfgDir::paths[]` 指向 `realPolicyValue` 内部这一"隐患"
在急迫拷贝策略下**完全封闭**——调用方看到的 `ConfigDirList` 里只有独立的 `std::string`，
永远不会触及底层指针关系。

### 5.2 异常安全分析

| 方法 | 保证级别 | 说明 |
|------|---------|------|
| `getDirList()` | 强保证 | `vector::emplace_back` 失败时 unique_ptr 析构仍释放 C 资源 |
| `getOneCfgFile()` | 强保证 | `validateRelPath` 抛出前无副作用；buf 在栈上，无堆分配风险 |
| `getCfgFiles()` | 强保证 | `validateRelPath` 抛出前无副作用；unique_ptr 确保 C 资源释放 |
| `ConfigDirList` 构造 | 强保证 | `vector` move 构造，noexcept |

**关键场景**：`vector::emplace_back` 在内存不足时抛出 `std::bad_alloc`。
此时 `unique_ptr` 析构器仍会运行，`FreeCfgDirList` 正确释放 C 层内存，不产生泄漏。

### 5.3 线程安全分析

```
ConfigPolicy 对象：
  成员变量：无
  所有方法：const
  ↓
  并发只读调用 → 无竞争 → 线程安全

ConfigDirList 对象：
  成员变量：vector<string>（在构造后不可变）
  ↓
  并发只读（const 方法）→ 线程安全
  并发写（拷贝赋值）   → 调用方需要自行加锁

getOneCfgFile 内部：
  char buf[MAX_PATH_LEN]  ← 每次调用在调用线程的栈上独立分配
  ↓
  无共享缓冲区 → 并发安全
```

### 5.4 `enum class FollowXMode` 的类型安全价值

```cpp
// C 风格（类型不安全）：编译器不报错
GetOneCfgFileEx("etc/cfg.xml", buf, 256, 999, "");  // 999 是无效值

// C++ 封装（编译期防护）：传入无效值直接报编译错误
policy.getOneCfgFile("etc/cfg.xml", static_cast<FollowXMode>(999));  // ← 语义上不应这样写
// 正确写法：
policy.getOneCfgFile("etc/cfg.xml", FollowXMode::Sim1);              // ← 清晰，无歧义
```

`static_cast<int>(mode)` 在实现内部完成，使用方永远不需要知道底层数字。

### 5.5 `validateRelPath` 的必要性

| 检查项 | 原因 |
|-------|------|
| 非空检查 | C 层对空字符串行为未定义，可能崩溃或静默返回错误结果 |
| 不以 '/' 开头 | C 层将 relPath 拼接到层前缀：`/vendor` + `/etc/cfg` = `//etc/cfg`，路径解析将失败 |
| 长度检查 | C 层内部使用定长缓冲区 `MAX_PATH_LEN`，超长会截断，结果路径无效 |

这三类错误均属于**调用方编程错误**，在调试阶段应尽早暴露，因此选择抛出异常而非静默返回空值。

---

## 六、CMake 集成

```cmake
cmake_minimum_required(VERSION 3.14)
project(your_project CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── 封装层静态库（推荐：封装代码与业务代码一起编译）────────────────────────
add_library(config_policy_cxx STATIC
    src/config_policy.cpp
)

target_include_directories(config_policy_cxx
    PUBLIC  include/             # config_policy.hpp 所在目录
    PRIVATE include/             # config_policy_utils.h 所在目录（实现文件需要）
)

target_link_libraries(config_policy_cxx
    PUBLIC  ${CMAKE_SOURCE_DIR}/lib/libconfig_policy_util.so
)

# ── 业务可执行程序 ──────────────────────────────────────────────────────────
add_executable(your_app src/main.cpp)

target_link_libraries(your_app
    PRIVATE config_policy_cxx
)

# 运行时 RPATH（避免依赖 LD_LIBRARY_PATH）
set_target_properties(your_app PROPERTIES
    BUILD_RPATH  "${CMAKE_SOURCE_DIR}/lib"
    INSTALL_RPATH "/usr/lib"
)
```

### 推荐目录结构

```
your_project/
├── CMakeLists.txt
├── include/
│   ├── config_policy.hpp          ← C++ 封装头文件（对外暴露）
│   └── config_policy_utils.h      ← C 原始头文件（仅实现文件内部使用）
├── lib/
│   └── libconfig_policy_util.so
└── src/
    ├── config_policy.cpp          ← C++ 封装实现
    └── main.cpp                   ← 业务代码
```

---

## 七、完整使用示例

```cpp
/**
 * main.cpp — ConfigPolicy C++ 封装使用示例
 */
#include <iostream>
#include <stdexcept>
#include "config_policy.hpp"

// 使用命名空间别名，减少书写量（可选）
namespace cust = Huazi::Car::instru::cust;

// ── 示例1：查看所有配置层目录 ──────────────────────────────────────────────
static void demo_dir_list()
{
    std::cout << "\n=== 示例1：所有配置层目录 ===\n";

    cust::ConfigPolicy policy;
    cust::ConfigDirList dirs = policy.getDirList();

    if (dirs.empty()) {
        std::cerr << "  获取配置层失败\n";
        return;
    }

    // 范围 for 遍历（ConfigDirList 提供 begin/end）
    int idx = 0;
    for (const auto& layer : dirs) {
        std::cout << "  [" << idx++ << "] " << layer << "\n";
    }

    // 打印原始参数字符串（调试用）
    std::cout << "  原始参数值: "
              << (dirs.rawPolicyValue().empty() ? "(default)" : dirs.rawPolicyValue())
              << "\n";

    // 按索引访问（带边界检查）
    if (dirs.size() > 0) {
        std::cout << "  最低优先级层: " << dirs.at(0) << "\n";
    }
}

// ── 示例2：查找最高优先级配置文件 ──────────────────────────────────────────
static void demo_get_one_file()
{
    std::cout << "\n=== 示例2：最高优先级配置文件 ===\n";

    cust::ConfigPolicy policy;

    // 不走 Follow-X（最常用）
    std::string path = policy.getOneCfgFile("etc/telephony/config.json");
    std::cout << "  NoRule:  " << (path.empty() ? "(未找到)" : path) << "\n";

    // SIM 卡1 运营商专属配置
    std::string simPath = policy.getOneCfgFile(
        "etc/telephony/OpkeyInfo.json",
        cust::FollowXMode::Sim1
    );
    std::cout << "  Sim1:    " << (simPath.empty() ? "(未找到)" : simPath) << "\n";

    // 自定义运营商子目录
    std::string customPath = policy.getOneCfgFile(
        "etc/config.xml",
        cust::FollowXMode::UserDefined,
        "carrier/46060"
    );
    std::cout << "  Custom:  " << (customPath.empty() ? "(未找到)" : customPath) << "\n";
}

// ── 示例3：收集所有层的配置文件（合并加载场景）─────────────────────────────
static void demo_get_all_files()
{
    std::cout << "\n=== 示例3：所有层的配置文件 ===\n";

    cust::ConfigPolicy policy;
    auto files = policy.getCfgFiles("etc/plugin/rules.xml");

    if (files.empty()) {
        std::cout << "  任何层均无此文件\n";
        return;
    }

    // files 已按低→高优先级排列，后面的覆盖前面的
    for (const auto& f : files) {
        std::cout << "  " << f << "\n";
    }
}

// ── 示例4：异常处理 ────────────────────────────────────────────────────────
static void demo_exception_handling()
{
    std::cout << "\n=== 示例4：异常处理 ===\n";

    cust::ConfigPolicy policy;

    // 情形1：非法路径（以 '/' 开头）→ 抛出 ConfigPolicyError
    try {
        policy.getOneCfgFile("/etc/config.xml");   // 错误：以 / 开头
    } catch (const cust::ConfigPolicyError& e) {
        std::cerr << "  [预期异常] " << e.what() << "\n";
    }

    // 情形2：空路径 → 抛出 ConfigPolicyError
    try {
        policy.getOneCfgFile("");
    } catch (const cust::ConfigPolicyError& e) {
        std::cerr << "  [预期异常] " << e.what() << "\n";
    }

    // 情形3：文件不存在 → 返回空字符串，不抛出
    std::string result = policy.getOneCfgFile("etc/nonexistent/file.xml");
    std::cout << "  不存在的文件: " << (result.empty() ? "(空字符串，不抛出)" : result) << "\n";

    // 情形4：统一用基类捕获（兼容其他 std::exception）
    try {
        policy.getOneCfgFile("/bad");
    } catch (const std::exception& e) {
        std::cerr << "  [基类捕获] " << e.what() << "\n";
    }
}

// ── 示例5：多线程并发调用（无需加锁）──────────────────────────────────────
#include <thread>
#include <vector>

static void thread_worker(const cust::ConfigPolicy& policy, int id)
{
    // 每个线程调用独立的 getOneCfgFile，内部 buf 在各自线程栈上，无竞争
    std::string path = policy.getOneCfgFile("etc/config.xml");
    std::cout << "  线程 " << id << ": "
              << (path.empty() ? "(未找到)" : path) << "\n";
}

static void demo_multithreading()
{
    std::cout << "\n=== 示例5：多线程并发调用 ===\n";

    const cust::ConfigPolicy policy;  // 共享同一实例，无需锁
    std::vector<std::thread> threads;

    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(thread_worker, std::cref(policy), i);
    }
    for (auto& t : threads) {
        t.join();
    }
}

int main()
{
    demo_dir_list();
    demo_get_one_file();
    demo_get_all_files();
    demo_exception_handling();
    demo_multithreading();
    return 0;
}
```

---

## 八、附录 A：C++17 `std::optional` 增强版（可选）

若项目确认使用 C++17，可将 `getOneCfgFile` 的返回类型改为
`std::optional<std::string>`，使"未找到"的语义更加明确：

```cpp
// config_policy.hpp（C++17 版本片段）
#include <optional>

class ConfigPolicy {
public:
    std::optional<std::string> getOneCfgFile(
        const std::string& relPath,
        FollowXMode        mode  = FollowXMode::NoRule,
        const std::string& extra = "") const;
};

// config_policy.cpp（C++17 版本片段）
std::optional<std::string> ConfigPolicy::getOneCfgFile(
    const std::string& relPath,
    FollowXMode        mode,
    const std::string& extra) const
{
    validateRelPath(relPath);
    char buf[MAX_PATH_LEN] = {};
    char* result = GetOneCfgFileEx(
        relPath.c_str(), buf, MAX_PATH_LEN,
        static_cast<int>(mode), extra.c_str());
    if (result == nullptr) return std::nullopt;  // 明确表示"无值"
    return std::string(result);
}

// 调用方（C++17）
auto path = policy.getOneCfgFile("etc/cfg.xml");
if (path.has_value()) {
    use(*path);
}
// 或使用 value_or 提供默认值
std::string p = policy.getOneCfgFile("etc/cfg.xml").value_or("/fallback/cfg.xml");
```

---

## 九、接口速查表

| 接口 | 签名 | 返回值语义 | 异常 |
|------|------|-----------|------|
| `getDirList()` | `ConfigDirList getDirList() const` | 失败时 `empty()==true` | 不抛出 |
| `getOneCfgFile()` | `std::string getOneCfgFile(relPath, mode, extra) const` | 未找到时空字符串 | 非法入参抛 `ConfigPolicyError` |
| `getCfgFiles()` | `vector<string> getCfgFiles(relPath, mode, extra) const` | 未找到时空 vector | 非法入参抛 `ConfigPolicyError` |
| `ConfigDirList::paths()` | `const vector<string>&` | 低→高优先级层目录 | 不抛出 |
| `ConfigDirList::rawPolicyValue()` | `const string&` | 原始参数字符串 | 不抛出 |
| `ConfigDirList::at(idx)` | `const string&` | 越界抛 `out_of_range` | `std::out_of_range` |
