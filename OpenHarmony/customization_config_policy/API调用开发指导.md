# libconfig_policy_util 开发接入指导

本文档面向**首次使用 `libconfig_policy_util.so`** 的开发者，
说明如何接入该库、调用各接口，以及使用时必须遵守的内存管理规则。

---

## 一、库的用途

`libconfig_policy_util` 提供**多层配置文件路径查找**能力。

系统中的配置文件按"层"组织，不同层对应不同的存储分区
（如 `/system`、`/vendor`、`/oem`），层与层之间有明确的优先级顺序。
应用程序只需提供配置文件的**相对路径**（如 `etc/telephony/config.json`），
库负责按优先级从高到低搜索各层目录，返回实际存在的文件路径。

```
调用方只知道：  etc/telephony/config.json

库自动查找：
  /oem/etc/telephony/config.json    ← 最高优先级，优先命中
  /vendor/etc/telephony/config.json
  /system/etc/telephony/config.json ← 最低优先级

返回：命中的最高优先级路径（或全部命中路径）
```

---

## 二、接入前提

### 2.1 获取的文件

向库提供方索取以下两个文件：

| 文件 | 说明 |
|------|------|
| `libconfig_policy_util.so` | 动态链接库（运行时加载） |
| `config_policy_utils.h` | 头文件（编译时使用，包含所有类型和函数声明） |

### 2.2 运行时环境要求

**库依赖一个参数文件在运行前存在**：`/run/config_policy/params`

该文件由系统启动时的 `cust_init` 程序写入，内容是配置层路径等参数。
若文件不存在，库会自动回落到编译期默认层级
（`/system:/chipset:/sys_prod:/chip_prod`），不会崩溃，
但层路径可能与你所在系统的实际分区不符。

**请向系统集成方确认 `cust_init` 已在设备启动序列中正确配置。**

### 2.3 头文件中的重要常量

```c
#define MAX_CFG_POLICY_DIRS_CNT  32   /* 最多支持 32 个层目录 */
#define MAX_PATH_LEN             256  /* 路径字符串最大长度（含 '\0'） */
```

---

## 三、编译接入

### 3.1 目录结构建议

```
your_project/
├── lib/
│   └── libconfig_policy_util.so   ← 库文件
├── include/
│   └── config_policy_utils.h      ← 头文件
└── src/
    └── your_code.c
```

### 3.2 CMake 接入

```cmake
# CMakeLists.txt

# 方式A：直接链接本地 .so 文件
add_executable(your_app src/your_code.c)

target_include_directories(your_app PRIVATE include/)

target_link_libraries(your_app
    ${CMAKE_SOURCE_DIR}/lib/libconfig_policy_util.so
)

# 运行时让系统找到 .so（以下二选一）：
# 方式1：设置 RPATH（推荐，不依赖 LD_LIBRARY_PATH）
set_target_properties(your_app PROPERTIES
    BUILD_RPATH "${CMAKE_SOURCE_DIR}/lib"
    INSTALL_RPATH "/usr/lib"          # 部署路径
)
```

### 3.3 gcc 直接编译

```bash
# 编译并链接（-L 指定 .so 所在目录，-l 指定库名）
gcc your_code.c \
    -I include/ \
    -L lib/ -lconfig_policy_util \
    -Wl,-rpath,'$ORIGIN/lib' \
    -o your_app

# 或者在运行前设置环境变量（开发调试时使用）
export LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH
./your_app
```

### 3.4 C++ 项目注意事项

头文件已包含 `extern "C"` 保护，C++ 项目可直接 `#include`，无需任何额外处理。

---

## 四、核心概念

### 4.1 相对路径（relPath）

所有查询 API 接受的路径参数都是**相对路径**，不含前缀 `/`。

```c
// ✓ 正确
GetOneCfgFile("etc/telephony/config.json", buf, MAX_PATH_LEN);

// ✗ 错误（不能以 / 开头）
GetOneCfgFile("/etc/telephony/config.json", buf, MAX_PATH_LEN);
```

库内部会将相对路径拼接到各层目录前缀：
```
/oem    + etc/telephony/config.json → /oem/etc/telephony/config.json
/vendor + etc/telephony/config.json → /vendor/etc/telephony/config.json
```

### 4.2 优先级方向

层目录的优先级**从低到高**排列（数组下标 0 = 最低优先级）：

```
低优先级  [0] /system
          [1] /chipset
          [2] /sys_prod
          [3] /chip_prod   ← 高优先级
```

- `GetOneCfgFile`：从高优先级向低查找，返回**第一个存在的文件路径**
- `GetCfgFiles`：从低优先级向高收集，返回**所有层中存在的文件路径**（低→高顺序）
- `GetCfgDirList`：返回**所有层目录本身**（低→高顺序）

### 4.3 Follow-X 模式（运营商差异化配置）

某些配置文件因运营商不同而不同，Follow-X 机制在标准层路径中插入运营商子目录：

```
标准路径:  /vendor/etc/telephony/config.json
Follow-X:  /vendor/etc/carrier/46060/etc/telephony/config.json
                              ↑ 运营商代码（opkey）
```

不需要运营商差异化时，使用 `FOLLOWX_MODE_NO_RULE_FOLLOWED` 即可。

---

## 五、数据结构

```c
/* 配置目录列表（由 GetCfgDirList 返回） */
struct CfgDir {
    char *paths[MAX_CFG_POLICY_DIRS_CNT];  /* 各层目录路径，NULL 表示该槽位无数据 */
    char *realPolicyValue;                  /* 实际生效的层路径原始字符串（调试用） */
};

/* 配置文件列表（由 GetCfgFiles/GetCfgFilesEx 返回） */
struct CfgFiles {
    char *paths[MAX_CFG_POLICY_DIRS_CNT];  /* 各层找到的文件路径，NULL 表示该层无此文件 */
};
```

> **⚠️ 内存管理规则（必读）**
>
> `CfgDir` 和 `CfgFiles` 的内存模型**不同**，必须用对应的 Free 函数释放：
>
> | 结构体 | Free 函数 | `paths[]` 元素能否单独 free |
> |--------|-----------|----------------------------|
> | `CfgDir`   | `FreeCfgDirList()` | **不能**，`paths[]` 指向 `realPolicyValue` 内部，非独立分配 |
> | `CfgFiles` | `FreeCfgFiles()`   | **可以**，每个 `paths[i]` 都是独立 `strdup()` 分配 |
>
> 详见第七节。

---

## 六、API 参考

### 6.1 GetCfgDirList — 获取所有配置层目录

```c
CfgDir *GetCfgDirList(void);
```

**功能**：返回所有配置层的目录路径，按优先级从低到高排列。

**参数**：无

**返回值**：
- 成功：指向 `CfgDir` 结构体的指针（堆内存，**必须调用 `FreeCfgDirList()` 释放**）
- 失败：`NULL`

**示例**：

```c
#include "config_policy_utils.h"

void show_layers(void)
{
    CfgDir *dirs = GetCfgDirList();
    if (dirs == NULL) {
        fprintf(stderr, "GetCfgDirList failed\n");
        return;
    }

    printf("当前生效的配置层（低→高优先级）:\n");
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (dirs->paths[i] != NULL) {
            printf("  [%d] %s\n", i, dirs->paths[i]);
        }
    }
    /* realPolicyValue 是调试用的原始参数字符串 */
    printf("原始配置: %s\n", dirs->realPolicyValue ? dirs->realPolicyValue : "(default)");

    FreeCfgDirList(dirs);   /* ← 必须调用，且只能用这个函数 */
}
```

---

### 6.2 GetOneCfgFile — 获取最高优先级配置文件路径

```c
char *GetOneCfgFile(const char *pathSuffix, char *buf, unsigned int bufLength);
```

**功能**：在所有配置层中查找指定相对路径的文件，
返回**优先级最高的那个层**中该文件的完整路径。

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `pathSuffix` | `const char*` | 配置文件的相对路径，如 `"etc/telephony/config.json"` |
| `buf` | `char*` | 调用方提供的输出缓冲区，用于存放结果路径字符串 |
| `bufLength` | `unsigned int` | 缓冲区大小，**建议使用 `MAX_PATH_LEN`（256）** |

**返回值**：
- 找到：返回 `buf`（指向缓冲区中的完整路径字符串）
- 未找到：返回 `NULL`（`buf` 内容不确定）

> **注意**：返回值指向传入的 `buf`，无需也不应该 `free()`。

**示例**：

```c
#include "config_policy_utils.h"

void open_config(void)
{
    char path[MAX_PATH_LEN] = {0};
    char *found = GetOneCfgFile("etc/telephony/config.json", path, MAX_PATH_LEN);

    if (found == NULL) {
        printf("配置文件不存在于任何层\n");
        return;
    }

    printf("使用配置文件: %s\n", found);  /* found == path，同一块内存 */

    FILE *f = fopen(found, "r");
    if (f) {
        /* 读取配置文件... */
        fclose(f);
    }
    /* 无需 free(found) */
}
```

---

### 6.3 GetOneCfgFileEx — 获取最高优先级配置文件路径（扩展版）

```c
char *GetOneCfgFileEx(const char *pathSuffix, char *buf, unsigned int bufLength,
                       int followMode, const char *extra);
```

**功能**：与 `GetOneCfgFile` 相同，但支持指定 Follow-X 模式。

**额外参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `followMode` | `int` | Follow-X 模式，见下表 |
| `extra` | `const char*` | `followMode == FOLLOWX_MODE_USER_DEFINED` 时的自定义子目录路径；其他模式传 `""` 即可 |

**`followMode` 取值**：

| 常量 | 值 | 说明 |
|------|----|------|
| `FOLLOWX_MODE_DEFAULT` | 0 | 读取系统配置的默认 Follow-X 规则 |
| `FOLLOWX_MODE_NO_RULE_FOLLOWED` | 1 | **不走 Follow-X**，直接按层查找（最常用） |
| `FOLLOWX_MODE_SIM_DEFAULT` | 10 | 自动读取默认 SIM 卡的运营商代码 |
| `FOLLOWX_MODE_SIM_1` | 11 | 读取 SIM 卡1 的运营商代码（opkey0） |
| `FOLLOWX_MODE_SIM_2` | 12 | 读取 SIM 卡2 的运营商代码（opkey1） |
| `FOLLOWX_MODE_USER_DEFINED` | 100 | 使用 `extra` 参数指定子目录路径 |

**示例**：

```c
#include "config_policy_utils.h"

void demo_followx(void)
{
    char path[MAX_PATH_LEN] = {0};

    /* 场景1：不关心运营商，直接按层查找 */
    char *p1 = GetOneCfgFileEx("etc/config.xml", path, MAX_PATH_LEN,
                                FOLLOWX_MODE_NO_RULE_FOLLOWED, "");

    /* 场景2：查找 SIM 卡1 运营商的专属配置 */
    char *p2 = GetOneCfgFileEx("etc/telephony/OpkeyInfo.json", path, MAX_PATH_LEN,
                                FOLLOWX_MODE_SIM_1, "");

    /* 场景3：自定义运营商子目录 */
    char *p3 = GetOneCfgFileEx("etc/config.xml", path, MAX_PATH_LEN,
                                FOLLOWX_MODE_USER_DEFINED, "carrier/my_operator");
    /*
     * 场景3 实际查找路径示例：
     *   /oem/etc/carrier/my_operator/etc/config.xml
     *   /vendor/etc/carrier/my_operator/etc/config.xml
     */

    (void)p1; (void)p2; (void)p3;  /* 使用同一 path 缓冲区，只保留最后一次结果 */
}
```

---

### 6.4 GetCfgFiles — 获取所有层的配置文件路径

```c
CfgFiles *GetCfgFiles(const char *pathSuffix);
```

**功能**：在所有配置层中查找指定相对路径的文件，
返回**所有层中存在的文件路径**（从低优先级到高优先级排列）。

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `pathSuffix` | `const char*` | 配置文件的相对路径 |

**返回值**：
- 成功：指向 `CfgFiles` 结构体的指针（堆内存，**必须调用 `FreeCfgFiles()` 释放**）
- 无文件存在 / 失败：可能返回 `NULL`，也可能返回 `paths[]` 全为 `NULL` 的结构体

**使用场景**：需要合并读取多层配置（如插件系统逐层加载配置）时使用。

**示例**：

```c
#include "config_policy_utils.h"

void merge_configs(void)
{
    CfgFiles *files = GetCfgFiles("etc/plugin/config.xml");
    if (files == NULL) {
        printf("未找到任何层的配置文件\n");
        return;
    }

    /* paths[] 从低优先级（[0]）到高优先级排列，NULL 表示该层无此文件 */
    printf("找到的配置文件（低→高优先级）:\n");
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (files->paths[i] != NULL) {
            printf("  %s\n", files->paths[i]);
            /* 按低→高优先级顺序处理，后面的层会覆盖前面的配置 */
            load_and_merge(files->paths[i]);
        }
    }

    FreeCfgFiles(files);   /* ← 必须调用 */
}
```

---

### 6.5 GetCfgFilesEx — 获取所有层的配置文件路径（扩展版）

```c
CfgFiles *GetCfgFilesEx(const char *pathSuffix, int followMode, const char *extra);
```

**功能**：与 `GetCfgFiles` 相同，但支持指定 Follow-X 模式。
`followMode` 和 `extra` 参数含义与 `GetOneCfgFileEx` 完全一致。

**示例**：

```c
/* 获取所有层中 SIM 卡1 运营商专属的配置文件 */
CfgFiles *files = GetCfgFilesEx("etc/telephony/config.json",
                                  FOLLOWX_MODE_SIM_1, "");
if (files) {
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (files->paths[i]) {
            printf("%s\n", files->paths[i]);
        }
    }
    FreeCfgFiles(files);
}
```

---

### 6.6 FreeCfgDirList — 释放 GetCfgDirList 的返回值

```c
void FreeCfgDirList(CfgDir *res);
```

释放 `GetCfgDirList()` 返回的 `CfgDir` 结构体及其内部所有内存。
传入 `NULL` 是安全的（无操作）。

> **⚠️ 禁止**单独 `free(dirs->paths[i])`，原因见第七节。

---

### 6.7 FreeCfgFiles — 释放 GetCfgFiles/GetCfgFilesEx 的返回值

```c
void FreeCfgFiles(CfgFiles *res);
```

释放 `GetCfgFiles()` / `GetCfgFilesEx()` 返回的 `CfgFiles` 结构体及其内部所有内存。
传入 `NULL` 是安全的（无操作）。

---

## 七、内存管理规则（重要）

### 7.1 CfgDir 的内存模型

`GetCfgDirList()` 返回的 `CfgDir` 中，`paths[]` 各元素并**不是独立分配**的，
它们全部指向 `realPolicyValue` 字符串内部（通过原地解析冒号分隔的层路径得到）：

```
realPolicyValue: "/system:/vendor:/oem\0"
                  ↑        ↑        ↑
                paths[0] paths[1] paths[2]
```

因此：

```c
CfgDir *dirs = GetCfgDirList();

/* ✓ 正确：用 FreeCfgDirList 统一释放 */
FreeCfgDirList(dirs);

/* ✗ 错误：单独 free paths[i] 会导致 double-free 或堆损坏 */
free(dirs->paths[0]);   /* 绝对禁止 */
```

### 7.2 CfgFiles 的内存模型

`GetCfgFiles()` 返回的 `CfgFiles` 中，每个 `paths[i]` 都是独立 `strdup()` 分配的，
互相独立。可以单独 `free()`，也可以用 `FreeCfgFiles()` 统一释放：

```c
CfgFiles *files = GetCfgFiles("etc/config.xml");

/* ✓ 正确方式1：统一释放（推荐） */
FreeCfgFiles(files);

/* ✓ 正确方式2：也可以单独 free 某个元素（取走后置 NULL 避免 double-free） */
char *p = files->paths[2];
files->paths[2] = NULL;   /* 必须置 NULL */
/* ... 使用 p ... */
free(p);
FreeCfgFiles(files);      /* 此时 paths[2] 已是 NULL，FreeCfgFiles 会跳过 */
```

### 7.3 GetOneCfgFile 的返回值

`GetOneCfgFile` / `GetOneCfgFileEx` 返回的指针指向**传入的 `buf` 缓冲区**，
**不需要也不应该 `free()`**：

```c
char buf[MAX_PATH_LEN] = {0};
char *result = GetOneCfgFile("etc/config.xml", buf, MAX_PATH_LEN);

/* result == buf，同一块内存（栈上分配） */
/* ✗ 错误：free(result); */
/* ✓ 正确：直接使用 result/buf，函数返回后自动回收 */
```

### 7.4 总结

| 函数 | 返回值来源 | 释放方式 |
|------|-----------|---------|
| `GetCfgDirList()` | 堆内存 | `FreeCfgDirList()`，**禁止单独 free paths[i]** |
| `GetCfgFiles()` | 堆内存 | `FreeCfgFiles()`，或逐一 free paths[i]（需置 NULL）|
| `GetCfgFilesEx()` | 堆内存 | 同 `GetCfgFiles()` |
| `GetOneCfgFile()` | 指向传入 buf | **不需要 free** |
| `GetOneCfgFileEx()` | 指向传入 buf | **不需要 free** |

---

## 八、完整示例程序

以下示例演示了各接口的典型用法，可直接编译运行：

```c
/*
 * example.c — libconfig_policy_util 接入示例
 *
 * 编译：
 *   gcc example.c -I include/ -L lib/ -lconfig_policy_util \
 *       -Wl,-rpath,'$ORIGIN/lib' -o example
 */
#include <stdio.h>
#include <string.h>
#include "config_policy_utils.h"

/* ── 示例1：查看当前所有配置层 ─────────────────────────────────── */
static void example_show_layers(void)
{
    printf("\n=== 示例1：当前配置层目录 ===\n");

    CfgDir *dirs = GetCfgDirList();
    if (!dirs) {
        printf("  GetCfgDirList() 返回 NULL\n");
        return;
    }

    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (dirs->paths[i]) {
            printf("  [%d] %s\n", i, dirs->paths[i]);
        }
    }
    FreeCfgDirList(dirs);  /* ← 正确释放方式 */
}

/* ── 示例2：查找最高优先级配置文件 ─────────────────────────────── */
static void example_get_one_file(void)
{
    printf("\n=== 示例2：查找最高优先级配置文件 ===\n");

    char buf[MAX_PATH_LEN] = {0};

    /* 不使用 Follow-X，直接按层查找 */
    char *found = GetOneCfgFileEx("etc/telephony/config.json",
                                   buf, MAX_PATH_LEN,
                                   FOLLOWX_MODE_NO_RULE_FOLLOWED, "");
    if (found) {
        printf("  最高优先级路径: %s\n", found);
    } else {
        printf("  文件不存在于任何层\n");
    }
    /* 无需 free(found) */
}

/* ── 示例3：获取并合并所有层的配置文件 ─────────────────────────── */
static void example_get_all_files(void)
{
    printf("\n=== 示例3：所有层中的配置文件 ===\n");

    CfgFiles *files = GetCfgFiles("etc/plugin/rules.xml");
    if (!files) {
        printf("  任何层均无此文件\n");
        return;
    }

    int count = 0;
    for (int i = 0; i < MAX_CFG_POLICY_DIRS_CNT; i++) {
        if (files->paths[i]) {
            printf("  [%d] %s\n", i, files->paths[i]);
            count++;
        }
    }
    if (count == 0) {
        printf("  任何层均无此文件\n");
    }

    FreeCfgFiles(files);  /* ← 正确释放方式 */
}

/* ── 示例4：运营商差异化配置查找 ───────────────────────────────── */
static void example_followx(void)
{
    printf("\n=== 示例4：运营商差异化配置（Follow-X） ===\n");

    char buf[MAX_PATH_LEN] = {0};
    const char *rel = "etc/telephony/OpkeyInfo.json";

    /* SIM 卡1 运营商专属配置 */
    char *p_sim1 = GetOneCfgFileEx(rel, buf, MAX_PATH_LEN,
                                    FOLLOWX_MODE_SIM_1, "");
    printf("  SIM_1 专属配置: %s\n", p_sim1 ? p_sim1 : "(不存在)");

    /* 自定义运营商子目录 */
    memset(buf, 0, sizeof(buf));
    char *p_custom = GetOneCfgFileEx(rel, buf, MAX_PATH_LEN,
                                      FOLLOWX_MODE_USER_DEFINED, "carrier/46060");
    printf("  自定义路径配置: %s\n", p_custom ? p_custom : "(不存在)");
}

int main(void)
{
    example_show_layers();
    example_get_one_file();
    example_get_all_files();
    example_followx();
    return 0;
}
```

---

## 九、常见问题

### Q1：所有函数都返回 NULL，没有找到任何文件

**原因1**：`cust_init` 未运行，参数文件 `/run/config_policy/params` 不存在，
库使用了默认层路径（可能与实际分区不符）。

诊断方法：
```bash
# 检查参数文件是否存在
ls -la /run/config_policy/params

# 查看实际生效的层路径
cat /run/config_policy/params
```

**原因2**：查询的相对路径确实不存在于任何层目录中。使用诊断工具确认：
```bash
./dump_config_layers ./libconfig_policy_util.so etc/your/file.xml
```

---

### Q2：路径字符串被截断

`buf` 缓冲区过小。始终使用 `MAX_PATH_LEN`（256 字节）作为缓冲区大小：

```c
char buf[MAX_PATH_LEN] = {0};   /* ✓ */
char buf[64] = {0};              /* ✗ 可能截断 */
```

---

### Q3：程序崩溃，怀疑内存问题

检查是否对 `CfgDir->paths[i]` 调用了 `free()`：

```c
/* ✗ 这是导致崩溃的典型原因 */
CfgDir *dirs = GetCfgDirList();
free(dirs->paths[0]);       /* 错误！paths[] 指向 realPolicyValue 内部 */
FreeCfgDirList(dirs);

/* ✓ 正确做法 */
CfgDir *dirs = GetCfgDirList();
FreeCfgDirList(dirs);       /* 只调用这一个函数 */
```

---

### Q4：`GetOneCfgFile` 返回值在函数外失效

返回值指向传入的栈上 `buf`，若 `buf` 是函数内的局部变量，函数返回后失效。
需要持久保存时，`strdup()` 复制一份：

```c
const char *get_config_path(void)
{
    char buf[MAX_PATH_LEN] = {0};
    char *found = GetOneCfgFile("etc/cfg.xml", buf, MAX_PATH_LEN);
    if (!found) return NULL;
    return strdup(found);   /* 调用方负责 free() */
}
```

---

### Q5：多线程环境下能否并发调用

`GetCfgDirList` / `GetCfgFiles` / `GetOneCfgFile` 内部使用线程安全的
`strtok_r`（非 `strtok`），**多线程并发只读调用是安全的**。

但每个线程必须传入**各自独立的 `buf` 缓冲区**，不能共享同一个 `buf`：

```c
/* ✓ 正确：每个线程有自己的 buf */
void *thread_func(void *arg)
{
    char buf[MAX_PATH_LEN] = {0};          /* 线程私有 */
    char *f = GetOneCfgFile("etc/cfg.xml", buf, MAX_PATH_LEN);
    ...
}
```

---

## 十、接口速查表

| 接口 | 用途 | 返回内存 | 释放方式 |
|------|------|---------|---------|
| `GetCfgDirList()` | 获取所有层目录路径 | 堆分配 | `FreeCfgDirList()` |
| `GetOneCfgFile()` | 最高优先级文件路径 | 指向 buf | 无需释放 |
| `GetOneCfgFileEx()` | 最高优先级文件路径（支持 Follow-X） | 指向 buf | 无需释放 |
| `GetCfgFiles()` | 所有层的文件路径列表 | 堆分配 | `FreeCfgFiles()` |
| `GetCfgFilesEx()` | 所有层的文件路径列表（支持 Follow-X） | 堆分配 | `FreeCfgFiles()` |
| `FreeCfgDirList()` | 释放 `GetCfgDirList` 结果 | — | — |
| `FreeCfgFiles()` | 释放 `GetCfgFiles` 结果 | — | — |
