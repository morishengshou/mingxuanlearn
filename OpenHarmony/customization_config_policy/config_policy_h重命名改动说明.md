# config_policy.hpp → config_policy.h 改动说明

将头文件扩展名从 `.hpp` 改为 `.h` 涉及三处文件改动。
代码逻辑**无需任何修改**，仅改动文件保护机制、注释和 include 引用。

---

## 一、改动总览

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `config_policy.hpp` → `config_policy.h` | 重命名 + 内容修改 | 替换 `#pragma once`、更新文件注释 |
| `config_policy.cpp` | 修改 `#include` 路径 | 引用新文件名 |
| `CMakeLists.txt` | 无需修改 | CMake 不直接编译头文件 |

---

## 二、`config_policy.h`（原 `config_policy.hpp`）的改动

### 改动1：替换文件包含保护机制

将非标准的 `#pragma once` 替换为标准 `#ifndef` 守卫，
并新增 C 编译器误包含检测。

```diff
-/**
- * @file   config_policy.hpp
- * @brief  libconfig_policy_util C++ 封装
- *         命名空间：Huazi::Car::instru::cust
- *
- * 使用要求：
- *   - C++14 或以上
- *   - 链接 libconfig_policy_util.so
- *
- * 本头文件不包含任何 C 原始头文件，使用方无需关心底层实现细节。
- */
-#pragma once
+/**
+ * @file   config_policy.h
+ * @brief  libconfig_policy_util C++ 封装
+ *         命名空间：Huazi::Car::instru::cust
+ *
+ * 使用要求：
+ *   - C++14 或以上
+ *   - 链接 libconfig_policy_util.so
+ *
+ * 本头文件不包含任何 C 原始头文件，使用方无需关心底层实现细节。
+ *
+ * 注意：本文件是 C++ 头文件，不兼容 C 编译器。
+ */
+#ifndef HUAZI_CAR_INSTRU_CUST_CONFIG_POLICY_H
+#define HUAZI_CAR_INSTRU_CUST_CONFIG_POLICY_H
+
+/* 防止 C 编译器误包含本文件 */
+#ifndef __cplusplus
+#  error "config_policy.h is a C++ header; do not include it in C source files."
+#endif

 #include <string>
 #include <vector>
 #include <stdexcept>
```

### 改动2：文件末尾添加 `#endif`

在文件最后一行（原 `} // namespace Huazi` 之后）添加守卫结束标记：

```diff
 } // namespace cust
 } // namespace instru
 } // namespace Car
 } // namespace Huazi
+
+#endif /* HUAZI_CAR_INSTRU_CUST_CONFIG_POLICY_H */
```

---

## 三、`config_policy.cpp` 的改动

仅修改第一行的 `#include`：

```diff
-#include "config_policy.hpp"
+#include "config_policy.h"
```

---

## 四、修改后的完整头文件

以下是 `config_policy.h` 的完整内容，供直接使用：

```cpp
/**
 * @file   config_policy.h
 * @brief  libconfig_policy_util C++ 封装
 *         命名空间：Huazi::Car::instru::cust
 *
 * 使用要求：
 *   - C++14 或以上
 *   - 链接 libconfig_policy_util.so
 *
 * 本头文件不包含任何 C 原始头文件，使用方无需关心底层实现细节。
 *
 * 注意：本文件是 C++ 头文件，不兼容 C 编译器。
 */
#ifndef HUAZI_CAR_INSTRU_CUST_CONFIG_POLICY_H
#define HUAZI_CAR_INSTRU_CUST_CONFIG_POLICY_H

/* 防止 C 编译器误包含本文件 */
#ifndef __cplusplus
#  error "config_policy.h is a C++ header; do not include it in C source files."
#endif

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
 * 内部字符串在构造时已从 C 层急迫拷贝，与底层 libconfig_policy_util
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
     * @param relPath   配置文件相对路径，如 "etc/telephony/config.json"
     *                  - 不能为空字符串
     *                  - 不能以 '/' 开头
     *                  - 长度不能超过 MAX_PATH_LEN - 1（255 字节）
     * @param mode      Follow-X 模式，默认 FollowXMode::NoRule
     * @param extra     仅在 mode == FollowXMode::UserDefined 时有效
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
     * @param relPath   配置文件相对路径（同 getOneCfgFile 的约束）
     * @param mode      Follow-X 模式，默认 FollowXMode::NoRule
     * @param extra     自定义子目录（仅 UserDefined 模式使用）
     * @return std::vector<std::string>  各层找到的路径列表；失败时返回空 vector。
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

#endif /* HUAZI_CAR_INSTRU_CUST_CONFIG_POLICY_H */
```

---

## 五、改动点汇总

| 位置 | 原内容 | 改后内容 | 原因 |
|------|--------|---------|------|
| 头文件第1行 | `@file config_policy.hpp` | `@file config_policy.h` | 文件名与注释保持一致 |
| 头文件第8行 | `#pragma once` | `#ifndef ... #define ...` | 替换为标准守卫，提升可移植性 |
| 头文件（新增） | 无 | `#ifndef __cplusplus` / `#error` | 防止 C 编译器误包含 |
| 头文件最后一行 | 无 | `#endif /* ... */` | 守卫结束标记 |
| `config_policy.cpp` 第1行 | `#include "config_policy.hpp"` | `#include "config_policy.h"` | 引用新文件名 |

`config_policy.cpp` 的其余内容、`CMakeLists.txt`、所有业务代码的 `#include` 路径（若使用方已改为 `.h`）均无需其他修改。
