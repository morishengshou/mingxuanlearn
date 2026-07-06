下面基于你**修正后的新需求**，给出一套 Android 12 上可落地的完整方案。重点目标是：

- `/data/hotupdate/filelist`、`/data/hotupdate/proplist` 使用**人类可读明文格式**
- 写接口给 `init` 或受信系统进程调用
- 读接口独立编译为 lib 给应用和服务调用
- 文件最终权限为 `0444`
- 通过 SELinux 新增标签进行管控
- 代码尽量可靠、健壮、可恢复、可审计

---

# 1. 需求确认与接口修正建议

你当前描述中有两个地方需要特别说明。

---

## 1.1 写属性接口命名参数建议修正

你写的是：

```cpp
int hotupdateprops(string filename, string filepath)
```

但功能描述是：

> 记录更新的属性，将属性和属性所在的 local.prop 文件记录到 `/data/hotupdate/proplist`

所以建议语义上改为：

```cpp
int hotupdateprops(const std::string& propname,
                   const std::string& proppath);
```

如果为了兼容你现有调用代码，也可以函数签名仍叫：

```cpp
int hotupdateprops(const std::string& filename,
                   const std::string& filepath);
```

但内部含义应解释为：

```text
filename -> propname
filepath -> proppath
```

为了后续维护，强烈建议使用清晰命名。

---

## 1.2 gethotupdateprops 入参问题

你当前写的是：

```cpp
std::vector<std::string> gethotupdateprops(string propname, string proppath)
```

但功能描述是：

> 读取 `/data/hotupdate/proplist` 里的属性名成为列表返回。

如果只是读取所有属性名，最合理接口应是：

```cpp
std::vector<std::string> gethotupdateprops(void);
```

你给出的入参 `propname`、`proppath` 在这个功能中没有使用价值。

因此我建议：

## 推荐 API

```cpp
std::vector<std::string> gethotupdateprops(void);
```

## 如果必须保持你给出的 ABI

可以保留兼容接口：

```cpp
std::vector<std::string> gethotupdateprops(const std::string& propname,
                                           const std::string& proppath);
```

但内部忽略参数，或者作为筛选条件使用。

为了最少改变你的需求，下面我会同时设计：

```cpp
std::vector<std::string> gethotupdateprops(void);
std::vector<std::string> gethotupdateprops(const std::string& propname,
                                           const std::string& proppath);
```

其中带参版本默认兼容旧调用，内部调用无参版本。

---

# 2. 总体架构设计

建议拆成两个动态库：

```text
libhotupdate_writer.so
libhotupdate_client.so
```

---

## 2.1 Writer 库

仅给 `init`、`hotupdate_service`、OTA/update 相关系统进程使用。

提供：

```cpp
int hotupdatefiles(const std::string& filename,
                   const std::string& filepath);

int hotupdateprops(const std::string& propname,
                   const std::string& proppath);
```

负责：

- 创建 `/data/hotupdate`
- 创建 list 文件
- 写入记录
- 文件加锁
- `fsync`
- 恢复权限为 `0444`

---

## 2.2 Client 库

给应用和服务调用。

提供：

```cpp
std::vector<std::string> gethotupdatefiles(void);

std::vector<std::string> gethotupdateprops(void);

std::vector<std::string> gethotupdateprops(const std::string& propname,
                                           const std::string& proppath);
```

负责：

- 只读打开文件
- 解析明文内容
- 返回文件名列表或属性名列表
- 遇到坏行跳过
- 失败时返回空 vector
- 不抛异常

---

# 3. 目录和文件设计

## 3.1 目录

```text
/data/hotupdate
```

推荐属性：

```text
owner: system
group: system
mode : 0755
label: u:object_r:hotupdate_data_file:s0
```

说明：

- 目录需要 `0755`，否则任意进程即使能读文件，也可能无法 traverse 目录。
- 是否所有进程都能访问，还取决于 SELinux。

---

## 3.2 文件

```text
/data/hotupdate/filelist
/data/hotupdate/proplist
```

推荐属性：

```text
owner: system
group: system
mode : 0444
label: u:object_r:hotupdate_data_file:s0
```

---

# 4. 明文文件格式设计

你要求文件必须人类可读。推荐使用：

```text
版本头 + 注释 + TSV 记录
```

TSV 即 tab-separated values。

原因：

- 人类可读
- grep/cat/sed/awk 友好
- 比 JSON 更轻
- 比 Base64 更直观
- 解析简单
- 配合严格校验后足够可靠

---

# 5. `/data/hotupdate/filelist` 格式

```text
# hotupdate-filelist-v1
# format: F<TAB>filename<TAB>filepath
F	libabc.so	/system/lib64/libabc.so
F	app_process64	/system/bin/app_process64
F	framework.jar	/system/framework/framework.jar
```

---

## 5.1 字段说明

| 字段 | 示例 | 说明 |
|---|---|---|
| `F` | `F` | 记录类型，表示 file |
| `filename` | `libabc.so` | 更新的文件名 |
| `filepath` | `/system/lib64/libabc.so` | 更新文件路径 |

---

# 6. `/data/hotupdate/proplist` 格式

```text
# hotupdate-proplist-v1
# format: P<TAB>propname<TAB>proppath
P	persist.sys.hotupdate.enable	/data/local.prop
P	ro.vendor.build.fingerprint	/vendor/build.prop
P	persist.vendor.hotupdate.version	/vendor/default.prop
```

---

## 6.1 字段说明

| 字段 | 示例 | 说明 |
|---|---|---|
| `P` | `P` | 记录类型，表示 property |
| `propname` | `persist.sys.hotupdate.enable` | 更新的属性名 |
| `proppath` | `/data/local.prop` | 属性所在 prop 文件 |

---

# 7. 字段合法性约束

为了保证明文格式可靠，所有字段必须禁止以下字符：

```text
\0
\n
\r
\t
```

建议进一步禁止所有 ASCII 控制字符：

```text
0x00 ~ 0x1F
0x7F
```

---

## 7.1 filename 约束

建议：

```text
非空
长度 <= 255
不能包含 /
不能包含空格
不能包含控制字符
```

合法示例：

```text
libabc.so
app_process64
framework.jar
```

非法示例：

```text
../libabc.so
system/bin/app_process
bad name.so
```

---

## 7.2 filepath 约束

建议：

```text
非空
必须以 / 开头
长度 < PATH_MAX
不能包含控制字符
不能包含空格
不能包含 /../
不能以 /.. 结尾
建议限制在白名单路径下
```

推荐白名单：

```text
/system/
/system_ext/
/product/
/vendor/
/odm/
/data/
```

---

## 7.3 propname 约束

建议只允许：

```text
a-z
A-Z
0-9
_
.
-
```

并限制长度：

```text
1 ~ 128
```

合法示例：

```text
persist.sys.hotupdate.enable
ro.vendor.build.fingerprint
vendor.hotupdate.version
```

---

## 7.4 proppath 约束

建议：

```text
非空
必须以 / 开头
长度 < PATH_MAX
不能包含控制字符
不能包含空格
不能包含 /../
不能以 /.. 结尾
建议必须以 .prop 结尾
```

推荐合法示例：

```text
/data/local.prop
/vendor/build.prop
/system/build.prop
/product/etc/build.prop
```

---

# 8. 错误码设计

写接口正常返回 `0`，其他情况返回负错误码。

```cpp
enum HotUpdateResult {
    HOTUPDATE_OK = 0,

    HOTUPDATE_ERR_INVALID_ARGUMENT = -1,
    HOTUPDATE_ERR_MKDIR_FAILED = -2,
    HOTUPDATE_ERR_OPEN_FAILED = -3,
    HOTUPDATE_ERR_LOCK_FAILED = -4,
    HOTUPDATE_ERR_WRITE_FAILED = -5,
    HOTUPDATE_ERR_FSYNC_FAILED = -6,
    HOTUPDATE_ERR_CHMOD_FAILED = -7,
    HOTUPDATE_ERR_PERMISSION = -8,
    HOTUPDATE_ERR_FILE_TOO_LARGE = -9,
    HOTUPDATE_ERR_NOT_REGULAR_FILE = -10,
    HOTUPDATE_ERR_UNKNOWN = -100,
};
```

---

# 9. 代码实现设计

下面给出可直接放进 AOSP 环境的 C++ 实现框架。

---

# 10. 头文件设计

## `include/hotupdate_writer.h`

```cpp
#pragma once

#include <string>

namespace android {
namespace hotupdate {

enum HotUpdateResult {
    HOTUPDATE_OK = 0,

    HOTUPDATE_ERR_INVALID_ARGUMENT = -1,
    HOTUPDATE_ERR_MKDIR_FAILED = -2,
    HOTUPDATE_ERR_OPEN_FAILED = -3,
    HOTUPDATE_ERR_LOCK_FAILED = -4,
    HOTUPDATE_ERR_WRITE_FAILED = -5,
    HOTUPDATE_ERR_FSYNC_FAILED = -6,
    HOTUPDATE_ERR_CHMOD_FAILED = -7,
    HOTUPDATE_ERR_PERMISSION = -8,
    HOTUPDATE_ERR_FILE_TOO_LARGE = -9,
    HOTUPDATE_ERR_NOT_REGULAR_FILE = -10,
    HOTUPDATE_ERR_UNKNOWN = -100,
};

int hotupdatefiles(const std::string& filename,
                   const std::string& filepath);

int hotupdateprops(const std::string& propname,
                   const std::string& proppath);

}  // namespace hotupdate
}  // namespace android
```

---

## `include/hotupdate_client.h`

```cpp
#pragma once

#include <string>
#include <vector>

namespace android {
namespace hotupdate {

std::vector<std::string> gethotupdatefiles();

std::vector<std::string> gethotupdateprops();

/*
 * 兼容你当前需求中带参数的声明。
 * 默认忽略参数，返回全部 propname。
 */
std::vector<std::string> gethotupdateprops(const std::string& propname,
                                           const std::string& proppath);

}  // namespace hotupdate
}  // namespace android
```

---

# 11. 公共工具实现

## `hotupdate_common.h`

```cpp
#pragma once

#include <string>
#include <utility>
#include <vector>

namespace android {
namespace hotupdate {
namespace internal {

constexpr const char* kHotUpdateDir = "/data/hotupdate";
constexpr const char* kFileListPath = "/data/hotupdate/filelist";
constexpr const char* kPropListPath = "/data/hotupdate/proplist";

constexpr const char* kFileListHeader =
        "# hotupdate-filelist-v1\n"
        "# format: F<TAB>filename<TAB>filepath\n";

constexpr const char* kPropListHeader =
        "# hotupdate-proplist-v1\n"
        "# format: P<TAB>propname<TAB>proppath\n";

bool IsValidFileName(const std::string& name);
bool IsValidPropName(const std::string& name);
bool IsValidFilePath(const std::string& path);
bool IsValidPropPath(const std::string& path);

std::string BuildTsvRecord(char type,
                           const std::string& first,
                           const std::string& second);

bool ParseTsvRecord(const std::string& line,
                    char expected_type,
                    std::string* first,
                    std::string* second);

std::vector<std::pair<std::string, std::string>>
ReadEntries(const char* path, char expected_type);

}  // namespace internal
}  // namespace hotupdate
}  // namespace android
```

---

## `hotupdate_common.cpp`

```cpp
#include "hotupdate_common.h"

#include <android-base/file.h>
#include <android-base/logging.h>
#include <android-base/strings.h>

#include <limits.h>

#include <cctype>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace android {
namespace hotupdate {
namespace internal {

constexpr size_t kMaxRecords = 4096;

bool HasForbiddenChar(const std::string& s) {
    for (unsigned char c : s) {
        if (c == '\0' || c == '\n' || c == '\r' || c == '\t') {
            return true;
        }

        if (c < 0x20 || c == 0x7F) {
            return true;
        }
    }

    return false;
}

bool HasSpace(const std::string& s) {
    return s.find(' ') != std::string::npos;
}

bool IsValidFileName(const std::string& name) {
    if (name.empty() || name.size() > 255) return false;
    if (HasForbiddenChar(name)) return false;
    if (HasSpace(name)) return false;
    if (name.find('/') != std::string::npos) return false;
    return true;
}

bool IsValidPropName(const std::string& name) {
    if (name.empty() || name.size() > 128) return false;
    if (HasForbiddenChar(name)) return false;

    for (char c : name) {
        if (!(std::isalnum(static_cast<unsigned char>(c)) ||
              c == '_' || c == '.' || c == '-')) {
            return false;
        }
    }

    return true;
}

bool IsAllowedPathPrefix(const std::string& path) {
    static const char* kAllowedPrefixes[] = {
        "/system/",
        "/system_ext/",
        "/product/",
        "/vendor/",
        "/odm/",
        "/data/",
    };

    for (const char* prefix : kAllowedPrefixes) {
        if (path.rfind(prefix, 0) == 0) {
            return true;
        }
    }

    return false;
}

bool IsValidAbsolutePathCommon(const std::string& path) {
    if (path.empty() || path.size() >= PATH_MAX) return false;
    if (path[0] != '/') return false;
    if (HasForbiddenChar(path)) return false;
    if (HasSpace(path)) return false;

    if (path.find("/../") != std::string::npos) return false;

    if (path.size() >= 3 &&
        path.compare(path.size() - 3, 3, "/..") == 0) {
        return false;
    }

    if (!IsAllowedPathPrefix(path)) return false;

    return true;
}

bool IsValidFilePath(const std::string& path) {
    return IsValidAbsolutePathCommon(path);
}

bool IsValidPropPath(const std::string& path) {
    if (!IsValidAbsolutePathCommon(path)) return false;

    /*
     * 根据你的描述，属性所在文件是 local.prop。
     * 如果只允许 local.prop，可使用下面判断：
     */
    if (path.size() < strlen("local.prop")) {
        return false;
    }

    if (path.compare(path.size() - strlen("local.prop"),
                     strlen("local.prop"),
                     "local.prop") != 0 &&
        path.compare(path.size() - strlen(".prop"),
                     strlen(".prop"),
                     ".prop") != 0) {
        return false;
    }

    return true;
}

std::string BuildTsvRecord(char type,
                           const std::string& first,
                           const std::string& second) {
    std::string line;
    line.reserve(1 + 1 + first.size() + 1 + second.size() + 1);

    line.push_back(type);
    line.push_back('\t');
    line.append(first);
    line.push_back('\t');
    line.append(second);
    line.push_back('\n');

    return line;
}

bool ParseTsvRecord(const std::string& line,
                    char expected_type,
                    std::string* first,
                    std::string* second) {
    if (line.empty()) return false;
    if (line[0] == '#') return false;

    std::vector<std::string> parts = android::base::Split(line, "\t");
    if (parts.size() != 3) {
        return false;
    }

    if (parts[0].size() != 1 || parts[0][0] != expected_type) {
        return false;
    }

    if (parts[1].empty() || parts[2].empty()) {
        return false;
    }

    if (HasForbiddenChar(parts[1]) || HasForbiddenChar(parts[2])) {
        return false;
    }

    if (first != nullptr) {
        *first = parts[1];
    }

    if (second != nullptr) {
        *second = parts[2];
    }

    return true;
}

std::vector<std::pair<std::string, std::string>>
ReadEntries(const char* path, char expected_type) {
    std::vector<std::pair<std::string, std::string>> result;
    std::set<std::string> seen;

    std::string content;
    if (!android::base::ReadFileToString(path, &content)) {
        PLOG(WARNING) << "failed to read " << path;
        return result;
    }

    std::vector<std::string> lines = android::base::Split(content, "\n");

    for (const auto& raw_line : lines) {
        if (result.size() >= kMaxRecords) {
            LOG(WARNING) << "too many hotupdate records, truncated";
            break;
        }

        std::string line = android::base::Trim(raw_line);
        if (line.empty()) continue;
        if (line[0] == '#') continue;

        std::string first;
        std::string second;

        if (!ParseTsvRecord(line, expected_type, &first, &second)) {
            LOG(WARNING) << "skip invalid hotupdate record";
            continue;
        }

        /*
         * 按第一列去重：
         * filelist: filename
         * proplist: propname
         */
        if (seen.insert(first).second) {
            result.emplace_back(first, second);
        }
    }

    return result;
}

}  // namespace internal
}  // namespace hotupdate
}  // namespace android
```

---

# 12. Writer 实现

## `hotupdate_writer.cpp`

```cpp
#include "hotupdate_writer.h"
#include "hotupdate_common.h"

#include <android-base/file.h>
#include <android-base/logging.h>
#include <android-base/unique_fd.h>

#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <cerrno>
#include <string>

namespace android {
namespace hotupdate {

namespace {

constexpr mode_t kDirMode = 0755;
constexpr mode_t kReadableFileMode = 0444;
constexpr mode_t kWritableFileMode = 0644;
constexpr off_t kMaxListFileSize = 1024 * 1024;

bool EnsureHotUpdateDir() {
    struct stat st {};
    if (stat(internal::kHotUpdateDir, &st) == 0) {
        if (!S_ISDIR(st.st_mode)) {
            LOG(ERROR) << internal::kHotUpdateDir << " exists but is not directory";
            return false;
        }

        chmod(internal::kHotUpdateDir, kDirMode);
        return true;
    }

    if (mkdir(internal::kHotUpdateDir, kDirMode) != 0 && errno != EEXIST) {
        PLOG(ERROR) << "mkdir failed: " << internal::kHotUpdateDir;
        return false;
    }

    chmod(internal::kHotUpdateDir, kDirMode);
    return true;
}

bool EnsureFileExistsWithHeader(const char* path, const char* header) {
    struct stat st {};

    if (lstat(path, &st) == 0) {
        if (!S_ISREG(st.st_mode)) {
            LOG(ERROR) << path << " exists but is not a regular file";
            return false;
        }

        chmod(path, kReadableFileMode);
        return true;
    }

    android::base::unique_fd fd(
            TEMP_FAILURE_RETRY(open(path,
                                    O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC | O_NOFOLLOW,
                                    kWritableFileMode)));
    if (fd.get() < 0) {
        PLOG(ERROR) << "failed to create " << path;
        return false;
    }

    if (!android::base::WriteStringToFd(header, fd.get())) {
        PLOG(ERROR) << "failed to write header " << path;
        return false;
    }

    if (fsync(fd.get()) != 0) {
        PLOG(ERROR) << "fsync header failed " << path;
        return false;
    }

    chmod(path, kReadableFileMode);
    return true;
}

int AppendRecord(const char* path,
                 const char* header,
                 const std::string& record) {
    if (!EnsureHotUpdateDir()) {
        return HOTUPDATE_ERR_MKDIR_FAILED;
    }

    if (!EnsureFileExistsWithHeader(path, header)) {
        return HOTUPDATE_ERR_OPEN_FAILED;
    }

    /*
     * 文件最终需要 0444。
     * 写入前临时改成 0644，写入后恢复 0444。
     * 调用者必须具备 SELinux setattr 权限以及 DAC 权限。
     */
    if (chmod(path, kWritableFileMode) != 0) {
        PLOG(ERROR) << "chmod writable failed " << path;
        return HOTUPDATE_ERR_CHMOD_FAILED;
    }

    android::base::unique_fd fd(
            TEMP_FAILURE_RETRY(open(path,
                                    O_RDWR | O_APPEND | O_CLOEXEC | O_NOFOLLOW)));
    if (fd.get() < 0) {
        PLOG(ERROR) << "open append failed " << path;
        chmod(path, kReadableFileMode);

        if (errno == EACCES || errno == EPERM) {
            return HOTUPDATE_ERR_PERMISSION;
        }

        return HOTUPDATE_ERR_OPEN_FAILED;
    }

    if (flock(fd.get(), LOCK_EX) != 0) {
        PLOG(ERROR) << "flock failed " << path;
        chmod(path, kReadableFileMode);
        return HOTUPDATE_ERR_LOCK_FAILED;
    }

    struct stat st {};
    if (fstat(fd.get(), &st) != 0) {
        PLOG(ERROR) << "fstat failed " << path;
        flock(fd.get(), LOCK_UN);
        chmod(path, kReadableFileMode);
        return HOTUPDATE_ERR_OPEN_FAILED;
    }

    if (!S_ISREG(st.st_mode)) {
        LOG(ERROR) << path << " is not regular file";
        flock(fd.get(), LOCK_UN);
        chmod(path, kReadableFileMode);
        return HOTUPDATE_ERR_NOT_REGULAR_FILE;
    }

    if (st.st_size > kMaxListFileSize) {
        LOG(ERROR) << path << " is too large";
        flock(fd.get(), LOCK_UN);
        chmod(path, kReadableFileMode);
        return HOTUPDATE_ERR_FILE_TOO_LARGE;
    }

    ssize_t ret = TEMP_FAILURE_RETRY(write(fd.get(), record.data(), record.size()));
    if (ret < 0 || static_cast<size_t>(ret) != record.size()) {
        PLOG(ERROR) << "write failed " << path;
        flock(fd.get(), LOCK_UN);
        chmod(path, kReadableFileMode);
        return HOTUPDATE_ERR_WRITE_FAILED;
    }

    if (fsync(fd.get()) != 0) {
        PLOG(ERROR) << "fsync failed " << path;
        flock(fd.get(), LOCK_UN);
        chmod(path, kReadableFileMode);
        return HOTUPDATE_ERR_FSYNC_FAILED;
    }

    flock(fd.get(), LOCK_UN);

    if (chmod(path, kReadableFileMode) != 0) {
        PLOG(ERROR) << "chmod readonly failed " << path;
        return HOTUPDATE_ERR_CHMOD_FAILED;
    }

    return HOTUPDATE_OK;
}

}  // namespace

int hotupdatefiles(const std::string& filename,
                   const std::string& filepath) {
    if (!internal::IsValidFileName(filename) ||
        !internal::IsValidFilePath(filepath)) {
        LOG(ERROR) << "invalid argument for hotupdatefiles";
        return HOTUPDATE_ERR_INVALID_ARGUMENT;
    }

    std::string record = internal::BuildTsvRecord('F', filename, filepath);
    return AppendRecord(internal::kFileListPath,
                        internal::kFileListHeader,
                        record);
}

int hotupdateprops(const std::string& propname,
                   const std::string& proppath) {
    if (!internal::IsValidPropName(propname) ||
        !internal::IsValidPropPath(proppath)) {
        LOG(ERROR) << "invalid argument for hotupdateprops";
        return HOTUPDATE_ERR_INVALID_ARGUMENT;
    }

    std::string record = internal::BuildTsvRecord('P', propname, proppath);
    return AppendRecord(internal::kPropListPath,
                        internal::kPropListHeader,
                        record);
}

}  // namespace hotupdate
}  // namespace android
```

---

# 13. Client 实现

## `hotupdate_client.cpp`

```cpp
#include "hotupdate_client.h"
#include "hotupdate_common.h"

#include <android-base/logging.h>

#include <string>
#include <vector>

namespace android {
namespace hotupdate {

namespace {

std::vector<std::string> ReadFirstColumnList(const char* path,
                                             char expected_type) {
    std::vector<std::string> result;

    auto entries = internal::ReadEntries(path, expected_type);
    result.reserve(entries.size());

    for (const auto& entry : entries) {
        result.emplace_back(entry.first);
    }

    return result;
}

}  // namespace

std::vector<std::string> gethotupdatefiles() {
    return ReadFirstColumnList(internal::kFileListPath, 'F');
}

std::vector<std::string> gethotupdateprops() {
    return ReadFirstColumnList(internal::kPropListPath, 'P');
}

std::vector<std::string> gethotupdateprops(const std::string& propname,
                                           const std::string& proppath) {
    /*
     * 兼容需求中的函数签名。
     * 当前需求是“读取 proplist 里的属性名成为列表返回”，
     * 所以这里默认忽略入参，返回全部属性名。
     *
     * 如果你希望做过滤，可以改成：
     * - propname 非空时只返回匹配 propname
     * - proppath 非空时只返回指定 proppath 下的属性
     */
    (void)propname;
    (void)proppath;

    return gethotupdateprops();
}

}  // namespace hotupdate
}  // namespace android
```

---

# 14. Android.bp 示例

## 14.1 推荐拆成两个库

```bp
cc_library_static {
    name: "libhotupdate_common",
    srcs: [
        "hotupdate_common.cpp",
    ],
    shared_libs: [
        "libbase",
        "liblog",
    ],
    export_include_dirs: [
        "include",
    ],
    cflags: [
        "-Wall",
        "-Werror",
    ],
}

cc_library_shared {
    name: "libhotupdate_writer",
    srcs: [
        "hotupdate_writer.cpp",
    ],
    static_libs: [
        "libhotupdate_common",
    ],
    shared_libs: [
        "libbase",
        "liblog",
    ],
    export_include_dirs: [
        "include",
    ],
    cflags: [
        "-Wall",
        "-Werror",
    ],
    system_ext_specific: true,
}

cc_library_shared {
    name: "libhotupdate_client",
    srcs: [
        "hotupdate_client.cpp",
    ],
    static_libs: [
        "libhotupdate_common",
    ],
    shared_libs: [
        "libbase",
        "liblog",
    ],
    export_include_dirs: [
        "include",
    ],
    cflags: [
        "-Wall",
        "-Werror",
    ],
    system_ext_specific: true,
}
```

如果 vendor 进程也要用：

```bp
vendor_available: true,
```

但注意：`/data/hotupdate` 的 SELinux 策略也要允许 vendor domain 访问，否则库能链接但读不到文件。

---

# 15. init 创建目录与文件

建议不要直接在 rc 里用 `write` 每次覆盖文件。

错误示例：

```rc
write /data/hotupdate/filelist "# hotupdate-filelist-v1\n"
```

这会导致每次开机可能覆盖已有记录。

---

## 15.1 推荐做一个 hotupdate_init 工具

该工具做：

- 如果目录不存在，创建目录
- 如果文件不存在，创建文件头
- 如果文件存在，不覆盖
- 设置 owner
- 设置 mode
- restorecon

然后在 rc 中调用：

```rc
on post-fs-data
    mkdir /data/hotupdate 0755 system system
    restorecon_recursive /data/hotupdate
    exec - system system -- /system/bin/hotupdate_init
```

---

## 15.2 如果必须只用 rc

可以：

```rc
on post-fs-data
    mkdir /data/hotupdate 0755 system system
    chown system system /data/hotupdate
    chmod 0755 /data/hotupdate
    restorecon_recursive /data/hotupdate
```

文件由第一次调用写接口时创建。

---

# 16. 关于 `0444` 和写入的关系

文件最终权限：

```text
0444
```

含义：

```text
owner/group/others 全部只读
```

这满足：

> 任意进程从 DAC 文件权限角度可读。

但这也意味着普通进程不能写。

写入者需要：

1. 是 root，或
2. 具备修改文件权限能力，或
3. SELinux 允许 `setattr/write/append`，并且 DAC 也允许，或
4. 由 `init` 执行写入

本方案中 writer 做：

```text
chmod 0644
open append
write
fsync
chmod 0444
```

因此写入 domain 必须具备 SELinux 的：

```text
setattr
write
append
lock
```

普通 reader domain 只给：

```text
open
read
getattr
map
```

---

# 17. SELinux 管控方案

你希望：

> 任意进程对两个文件都有可读权限，同时 SELinux 新增标签进行管控。

需要注意：

```text
Linux mode 0444 允许所有 UID 读
```

但 Android 上还需要：

```text
SELinux allow
```

也就是说：

```text
DAC 允许 + SELinux 允许 = 实际可读
```

---

# 18. SELinux 文件标签

## 18.1 file_contexts

新增：

```text
/data/hotupdate(/.*)?    u:object_r:hotupdate_data_file:s0
```

可以放在产品策略：

```text
device/<vendor>/<product>/sepolicy/private/file_contexts
```

或系统策略对应位置。

---

## 18.2 file.te

```te
type hotupdate_data_file, file_type, data_file_type;
```

如果你放在 vendor sepolicy，注意 public/private 暴露关系和 neverallow 约束。

---

# 19. SELinux 读权限设计

有三种方案。

---

## 19.1 方案 A：真正允许所有 app 和系统服务读

如果你真的要“任意进程”读取，那么至少需要允许：

```te
allow domain hotupdate_data_file:dir {
    search getattr
};

allow domain hotupdate_data_file:file {
    open read getattr map
};
```

但这非常宽，不推荐。很多 Android sepolicy 中也可能触发 neverallow 或安全审查问题。

---

## 19.2 方案 B：允许所有 appdomain 读，系统服务按需读

如果需求中的“应用和服务”主要是普通 App 和部分系统 service，推荐：

```te
allow appdomain hotupdate_data_file:dir {
    search getattr
};

allow appdomain hotupdate_data_file:file {
    open read getattr map
};
```

然后对系统 native service 白名单：

```te
allow system_server hotupdate_data_file:dir {
    search getattr
};

allow system_server hotupdate_data_file:file {
    open read getattr map
};

allow my_native_service hotupdate_data_file:dir {
    search getattr
};

allow my_native_service hotupdate_data_file:file {
    open read getattr map
};
```

---

## 19.3 方案 C：定义 reader attribute，白名单管控

这是最推荐的工程方案。

```te
attribute hotupdate_reader_domain;

allow hotupdate_reader_domain hotupdate_data_file:dir {
    search getattr
};

allow hotupdate_reader_domain hotupdate_data_file:file {
    open read getattr map
};
```

然后把需要访问的 domain 加入：

```te
typeattribute system_server hotupdate_reader_domain;
typeattribute my_native_service hotupdate_reader_domain;
typeattribute another_service hotupdate_reader_domain;
```

如果确实要所有普通 app 都能读：

```te
typeattribute appdomain hotupdate_reader_domain;
```

---

# 20. SELinux 写权限设计

建议只给写权限到：

- `init`
- `hotupdate_service`
- OTA/update 相关 domain

---

## 20.1 定义 writer attribute

```te
attribute hotupdate_writer_domain;

allow hotupdate_writer_domain hotupdate_data_file:dir {
    search read write add_name remove_name getattr
};

allow hotupdate_writer_domain hotupdate_data_file:file {
    create open read write append getattr setattr lock rename unlink
};
```

---

## 20.2 允许 init 写

```te
typeattribute init hotupdate_writer_domain;
```

或者直接：

```te
allow init hotupdate_data_file:dir {
    search read write add_name remove_name getattr
};

allow init hotupdate_data_file:file {
    create open read write append getattr setattr lock rename unlink
};
```

---

## 20.3 如果有 hotupdate_service

```te
type hotupdate_service, domain;
type hotupdate_service_exec, exec_type, file_type, system_file_type;

init_daemon_domain(hotupdate_service)

typeattribute hotupdate_service hotupdate_writer_domain;
```

`file_contexts`：

```text
/system/bin/hotupdate_service    u:object_r:hotupdate_service_exec:s0
```

---

# 21. SELinux 完整示例

## `hotupdate_file.te`

```te
type hotupdate_data_file, file_type, data_file_type;
```

---

## `hotupdate_access.te`

```te
attribute hotupdate_reader_domain;
attribute hotupdate_writer_domain;

allow hotupdate_reader_domain hotupdate_data_file:dir {
    search getattr
};

allow hotupdate_reader_domain hotupdate_data_file:file {
    open read getattr map
};

allow hotupdate_writer_domain hotupdate_data_file:dir {
    search read write add_name remove_name getattr
};

allow hotupdate_writer_domain hotupdate_data_file:file {
    create open read write append getattr setattr lock rename unlink
};
```

---

## `hotupdate_domain.te`

```te
typeattribute system_server hotupdate_reader_domain;

/*
 * 如果所有普通 app 都需要读，打开：
 */
typeattribute appdomain hotupdate_reader_domain;

/*
 * init 写。
 */
typeattribute init hotupdate_writer_domain;

/*
 * 如果你有自定义 native service：
 */
typeattribute my_native_service hotupdate_reader_domain;
```

---

## `file_contexts`

```text
/data/hotupdate(/.*)?    u:object_r:hotupdate_data_file:s0
```

---

# 22. 关于 appdomain 读取的风险

如果你加入：

```te
typeattribute appdomain hotupdate_reader_domain;
```

再加文件权限：

```text
0444
```

那么普通应用进程也可以读取：

```text
/data/hotupdate/filelist
/data/hotupdate/proplist
```

这意味着这些信息对普通 app 可见：

- 哪些系统文件发生过热更新
- 哪些属性被热更新
- 属性所在文件路径
- 可能暴露系统版本、OTA 策略或内部路径

如果这属于敏感信息，建议不要给 `appdomain`，而是通过系统 service 暴露受控接口。

但如果你的业务明确要求“任意进程可读”，那上述配置是满足要求的。

---

# 23. 文件权限和 SELinux 组合

最终状态建议：

```sh
ls -l /data/hotupdate
```

期望：

```text
drwxr-xr-x system system /data/hotupdate
-r--r--r-- system system /data/hotupdate/filelist
-r--r--r-- system system /data/hotupdate/proplist
```

查看 label：

```sh
ls -Z /data/hotupdate
```

期望：

```text
u:object_r:hotupdate_data_file:s0 filelist
u:object_r:hotupdate_data_file:s0 proplist
```

---

# 24. 可靠性设计要点

## 24.1 写入使用 `flock`

防止多进程同时写导致记录交叉。

```cpp
flock(fd.get(), LOCK_EX)
```

---

## 24.2 使用 `O_APPEND`

确保每次写都追加到文件尾。

```cpp
O_APPEND
```

---

## 24.3 单条记录一次 write

构造完整行：

```text
F\tfilename\tfilepath\n
```

然后一次 `write()` 写入。

---

## 24.4 使用 `fsync`

写完后：

```cpp
fsync(fd.get())
```

降低掉电丢失风险。

---

## 24.5 读取坏行跳过

如果文件尾部因异常断电产生半行：

```text
F	libabc.so	/syst
```

读取时跳过，不影响其他记录。

---

## 24.6 文件大小限制

建议限制：

```cpp
1 MB
```

防止异常调用无限增长。

---

## 24.7 最大记录数限制

建议限制：

```cpp
4096
```

防止读取时占用过多内存。

---

## 24.8 符号链接防护

打开文件使用：

```cpp
O_NOFOLLOW
```

创建前使用：

```cpp
lstat
```

避免路径被替换成符号链接。

---

# 25. 是否需要原子重写

当前方案是：

```text
append-only
```

优点：

- 简单
- 稳定
- 不容易丢历史
- 多进程写入容易控制

缺点：

- 删除和去重需要读侧处理
- 文件会增长

如果未来需要“清理重复记录”或“压缩文件”，可以设计维护工具：

```text
/data/hotupdate/filelist.tmp
fsync(tmp)
rename(tmp, filelist)
fsync(dir)
chmod 0444
restorecon
```

但当前需求只记录更新文件和属性，append-only 足够。

---

# 26. 调试命令

查看内容：

```sh
adb shell cat /data/hotupdate/filelist
adb shell cat /data/hotupdate/proplist
```

查看 tab：

```sh
adb shell cat -A /data/hotupdate/filelist
adb shell sed -n l /data/hotupdate/filelist
```

查看权限：

```sh
adb shell ls -l /data/hotupdate
```

查看 SELinux 标签：

```sh
adb shell ls -Z /data/hotupdate
```

查看拒绝日志：

```sh
adb shell dmesg | grep avc
adb logcat -b all | grep avc
```

---

# 27. 接口行为总结

## 27.1 `hotupdatefiles`

调用：

```cpp
int ret = hotupdatefiles("libabc.so", "/system/lib64/libabc.so");
```

写入：

```text
F	libabc.so	/system/lib64/libabc.so
```

返回：

```text
0 成功
负数 错误码
```

---

## 27.2 `hotupdateprops`

调用：

```cpp
int ret = hotupdateprops("persist.sys.hotupdate.enable",
                         "/data/local.prop");
```

写入：

```text
P	persist.sys.hotupdate.enable	/data/local.prop
```

返回：

```text
0 成功
负数 错误码
```

---

## 27.3 `gethotupdatefiles`

读取：

```text
/data/hotupdate/filelist
```

返回：

```cpp
{
    "libabc.so",
    "app_process64",
    "framework.jar"
}
```

---

## 27.4 `gethotupdateprops`

读取：

```text
/data/hotupdate/proplist
```

返回：

```cpp
{
    "persist.sys.hotupdate.enable",
    "ro.vendor.build.fingerprint",
    "persist.vendor.hotupdate.version"
}
```

---

# 28. 最终推荐方案一句话总结

最终建议采用：

```text
/data/hotupdate/filelist:
# hotupdate-filelist-v1
# format: F<TAB>filename<TAB>filepath
F	libabc.so	/system/lib64/libabc.so

/data/hotupdate/proplist:
# hotupdate-proplist-v1
# format: P<TAB>propname<TAB>proppath
P	persist.sys.hotupdate.enable	/data/local.prop
```

配合：

- 文件权限 `0444`
- 目录权限 `0755`
- SELinux 类型 `hotupdate_data_file`
- reader domain 只给 `open/read/getattr/map`
- writer domain 只给 `create/write/append/setattr/lock`
- 写入使用 `flock + O_APPEND + fsync`
- 输入严格校验
- 读取坏行跳过
- 文件大小和记录数限制

这套设计既满足人类可读调试，又能保证 Android 系统侧接口的可靠性和安全可控性。