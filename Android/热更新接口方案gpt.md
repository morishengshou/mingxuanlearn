下面给你一个偏工程落地的设计方案，目标是：

1. **文件明文、人类可读**
2. **写接口可靠、幂等、去重**
3. **读接口简单、安全、健壮**
4. **普通进程只能读，不能写、不能删**
5. **SELinux 明确管控**
6. **适配 Android 12 系统环境**

---

# 1. TSV 文件还是 DB 数据库？

## 结论

你的需求更适合使用 **TSV 明文文件**，不建议使用 SQLite DB。

推荐：

```text
/data/hotupdate/filelist
/data/hotupdate/proplist
```

使用 **TSV 格式**，即：

```text
<key>\t<value>\n
```

例如：

```text
# hotupdate file list v1
# filename<TAB>filepath
framework-res.apk	/system/framework/framework-res.apk
services.jar	/system/framework/services.jar
```

```text
# hotupdate prop list v1
# propname<TAB>proppath
persist.sys.foo	/vendor/etc/local.prop
ro.vendor.bar	/vendor/etc/local.prop
```

---

## TSV 与 SQLite 对比

| 维度 | TSV 明文文件 | SQLite DB |
|---|---|---|
| 人类可读 | 非常好 | 不直观，需要 sqlite 工具 |
| 实现复杂度 | 低 | 中高 |
| 依赖 | libc/C++ 标准库即可 | 需要 sqlite 库 |
| init 早期调用适配 | 好 | 可能引入不必要依赖 |
| 数据规模 | 小规模非常适合 | 更适合大量数据 |
| 唯一性保证 | 代码内实现即可 | 可用 UNIQUE 约束 |
| 崩溃恢复 | 可通过临时文件 + rename 保证 | SQLite 自带 |
| SELinux 管控 | 简单 | 还要考虑 db、journal、wal 等文件 |
| 明文审查 | 方便 adb/root 查看 | 不方便 |
| 误删/误改控制 | 文件权限 + 目录权限 + SELinux | 同样需要 SELinux |
| 并发写 | 需要 flock | SQLite 自带较好 |
| 维护成本 | 低 | 高 |

你的数据模型非常简单：

```text
filename + filepath 唯一
propname + proppath 唯一
读取时只需要返回第一列
```

这不值得引入 SQLite。

尤其是 SQLite 可能还会生成：

```text
filelist
filelist-wal
filelist-shm
filelist-journal
```

这会让权限、SELinux 标签和防删除管控变复杂。

所以建议：

> **使用 TSV 明文文件 + flock 锁 + 原子写入 + fsync + rename。**

Android SELinux 的文件上下文通常通过 `file_contexts` 配置，并在启动时由 init 加载；AOSP 也建议设备相关策略放在 device sepolicy 中。([source.android.com](https://source.android.com/docs/security/features/selinux/compatibility?utm_source=openai))

---

# 2. 文件格式设计

## 2.1 `/data/hotupdate/filelist`

格式：

```text
# hotupdate file list v1
# filename<TAB>filepath
filename<TAB>filepath
filename<TAB>filepath
```

示例：

```text
# hotupdate file list v1
# filename<TAB>filepath
services.jar	/system/framework/services.jar
framework-res.apk	/system/framework/framework-res.apk
```

---

## 2.2 `/data/hotupdate/proplist`

格式：

```text
# hotupdate prop list v1
# propname<TAB>proppath
propname<TAB>proppath
propname<TAB>proppath
```

示例：

```text
# hotupdate prop list v1
# propname<TAB>proppath
persist.vendor.hotupdate.enable	/vendor/etc/local.prop
ro.vendor.feature.foo	/vendor/etc/local.prop
```

---

## 2.3 字符约束

为了防止解析歧义，建议强制禁止：

| 字符 | 原因 |
|---|---|
| `\n` | 破坏行结构 |
| `\r` | 破坏跨平台解析 |
| `\t` | 破坏 TSV 字段结构 |
| `\0` | C 字符串风险 |

建议字段最大长度：

```cpp
filename <= 255
filepath <= 4096
propname <= 128
proppath <= 4096
```

路径建议必须是绝对路径：

```text
/path/to/file
```

不建议允许相对路径。

---

# 3. 错误码设计

建议定义统一错误码。

```cpp
enum HotUpdateError {
    HOTUPDATE_OK = 0,
    HOTUPDATE_ERR_INVALID_ARG = -1,
    HOTUPDATE_ERR_NAME_TOO_LONG = -2,
    HOTUPDATE_ERR_PATH_TOO_LONG = -3,
    HOTUPDATE_ERR_MKDIR_FAILED = -4,
    HOTUPDATE_ERR_OPEN_FAILED = -5,
    HOTUPDATE_ERR_LOCK_FAILED = -6,
    HOTUPDATE_ERR_READ_FAILED = -7,
    HOTUPDATE_ERR_WRITE_FAILED = -8,
    HOTUPDATE_ERR_FSYNC_FAILED = -9,
    HOTUPDATE_ERR_RENAME_FAILED = -10,
    HOTUPDATE_ERR_CHMOD_FAILED = -11,
    HOTUPDATE_ERR_CHOWN_FAILED = -12,
    HOTUPDATE_ERR_PARSE_FAILED = -13,
};
```

正常返回 `0`。

重复记录也返回 `0`，因为接口是幂等的。

---

# 4. 写接口设计

你的两个写接口：

```cpp
int hotupdatefiles(std::string filename, std::string filepath);
int hotupdateprops(std::string propname, std::string proppath);
```

它们可以共用一个内部函数：

```cpp
static int AddUniquePair(
    const std::string& list_path,
    const std::string& header1,
    const std::string& header2,
    const std::string& key,
    const std::string& value);
```

核心流程：

1. 参数校验
2. 确保 `/data/hotupdate` 目录存在
3. 打开 list 文件，不存在则创建
4. 对 lock 文件加 `flock`
5. 读取已有内容
6. 检查 `key + value` 是否已存在
7. 不存在则追加到内存列表
8. 写入临时文件
9. `fsync(temp_fd)`
10. `rename(temp, real)`
11. `fsync(/data/hotupdate 目录 fd)`
12. 设置权限 `0444`
13. 恢复 SELinux 标签由 init 或 restorecon 负责

---

# 5. C++ 代码设计

下面代码适合放到系统 native 库里，例如：

```text
libhotupdate
```

写接口只允许 init 或特定系统服务调用。

读接口可导出给应用和服务使用。

---

## 5.1 头文件 `hotupdate.h`

```cpp
#pragma once

#include <string>
#include <vector>

enum HotUpdateError {
    HOTUPDATE_OK = 0,
    HOTUPDATE_ERR_INVALID_ARG = -1,
    HOTUPDATE_ERR_NAME_TOO_LONG = -2,
    HOTUPDATE_ERR_PATH_TOO_LONG = -3,
    HOTUPDATE_ERR_MKDIR_FAILED = -4,
    HOTUPDATE_ERR_OPEN_FAILED = -5,
    HOTUPDATE_ERR_LOCK_FAILED = -6,
    HOTUPDATE_ERR_READ_FAILED = -7,
    HOTUPDATE_ERR_WRITE_FAILED = -8,
    HOTUPDATE_ERR_FSYNC_FAILED = -9,
    HOTUPDATE_ERR_RENAME_FAILED = -10,
    HOTUPDATE_ERR_CHMOD_FAILED = -11,
    HOTUPDATE_ERR_CHOWN_FAILED = -12,
    HOTUPDATE_ERR_PARSE_FAILED = -13,
};

int hotupdatefiles(const std::string& filename, const std::string& filepath);
int hotupdateprops(const std::string& propname, const std::string& proppath);

std::vector<std::string> gethotupdatefiles();
std::vector<std::string> gethotupdateprops();
```

---

## 5.2 实现文件 `hotupdate.cpp`

```cpp
#include "hotupdate.h"

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr const char* kHotUpdateDir = "/data/hotupdate";
constexpr const char* kFileListPath = "/data/hotupdate/filelist";
constexpr const char* kPropListPath = "/data/hotupdate/proplist";
constexpr const char* kLockPath = "/data/hotupdate/.lock";

constexpr size_t kMaxNameLen = 255;
constexpr size_t kMaxPropNameLen = 128;
constexpr size_t kMaxPathLen = 4096;
constexpr size_t kMaxLineLen = 8192;

bool ContainsInvalidChar(const std::string& s) {
    for (char c : s) {
        if (c == '\0' || c == '\n' || c == '\r' || c == '\t') {
            return true;
        }
    }
    return false;
}

bool IsAbsolutePath(const std::string& path) {
    return !path.empty() && path[0] == '/';
}

int ValidateKeyValue(
        const std::string& key,
        const std::string& value,
        size_t max_key_len,
        size_t max_value_len) {
    if (key.empty() || value.empty()) {
        return HOTUPDATE_ERR_INVALID_ARG;
    }

    if (ContainsInvalidChar(key) || ContainsInvalidChar(value)) {
        return HOTUPDATE_ERR_INVALID_ARG;
    }

    if (key.size() > max_key_len) {
        return HOTUPDATE_ERR_NAME_TOO_LONG;
    }

    if (value.size() > max_value_len) {
        return HOTUPDATE_ERR_PATH_TOO_LONG;
    }

    if (!IsAbsolutePath(value)) {
        return HOTUPDATE_ERR_INVALID_ARG;
    }

    return HOTUPDATE_OK;
}

int EnsureDir() {
    struct stat st {};
    if (stat(kHotUpdateDir, &st) == 0) {
        if (!S_ISDIR(st.st_mode)) {
            return HOTUPDATE_ERR_MKDIR_FAILED;
        }
        return HOTUPDATE_OK;
    }

    if (errno != ENOENT) {
        return HOTUPDATE_ERR_MKDIR_FAILED;
    }

    if (mkdir(kHotUpdateDir, 0555) != 0) {
        if (errno == EEXIST) {
            return HOTUPDATE_OK;
        }
        return HOTUPDATE_ERR_MKDIR_FAILED;
    }

    return HOTUPDATE_OK;
}

class FdGuard {
public:
    explicit FdGuard(int fd = -1) : fd_(fd) {}
    ~FdGuard() {
        if (fd_ >= 0) {
            close(fd_);
        }
    }

    FdGuard(const FdGuard&) = delete;
    FdGuard& operator=(const FdGuard&) = delete;

    int get() const {
        return fd_;
    }

    int release() {
        int old = fd_;
        fd_ = -1;
        return old;
    }

private:
    int fd_;
};

std::string DirName(const std::string& path) {
    auto pos = path.find_last_of('/');
    if (pos == std::string::npos) {
        return ".";
    }
    if (pos == 0) {
        return "/";
    }
    return path.substr(0, pos);
}

bool ParseTsvLine(
        const std::string& line,
        std::string* key,
        std::string* value) {
    if (line.empty()) {
        return false;
    }

    if (line[0] == '#') {
        return false;
    }

    size_t tab = line.find('\t');
    if (tab == std::string::npos) {
        return false;
    }

    if (line.find('\t', tab + 1) != std::string::npos) {
        return false;
    }

    std::string k = line.substr(0, tab);
    std::string v = line.substr(tab + 1);

    if (k.empty() || v.empty()) {
        return false;
    }

    if (ContainsInvalidChar(k) || ContainsInvalidChar(v)) {
        return false;
    }

    *key = std::move(k);
    *value = std::move(v);
    return true;
}

int ReadPairs(
        const std::string& path,
        std::vector<std::pair<std::string, std::string>>* pairs) {
    pairs->clear();

    std::ifstream in(path);
    if (!in.good()) {
        if (errno == ENOENT) {
            return HOTUPDATE_OK;
        }
        return HOTUPDATE_ERR_READ_FAILED;
    }

    std::string line;
    while (std::getline(in, line)) {
        if (line.size() > kMaxLineLen) {
            return HOTUPDATE_ERR_PARSE_FAILED;
        }

        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }

        if (line.empty() || line[0] == '#') {
            continue;
        }

        std::string key;
        std::string value;
        if (!ParseTsvLine(line, &key, &value)) {
            return HOTUPDATE_ERR_PARSE_FAILED;
        }

        pairs->push_back({key, value});
    }

    if (in.bad()) {
        return HOTUPDATE_ERR_READ_FAILED;
    }

    return HOTUPDATE_OK;
}

bool WriteAll(int fd, const std::string& data) {
    const char* p = data.data();
    size_t left = data.size();

    while (left > 0) {
        ssize_t n = write(fd, p, left);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }

        if (n == 0) {
            return false;
        }

        p += n;
        left -= static_cast<size_t>(n);
    }

    return true;
}

int AtomicWriteFile(
        const std::string& path,
        const std::string& content) {
    std::string tmp = path + ".tmp";

    int fd = open(
            tmp.c_str(),
            O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
            0444);
    if (fd < 0) {
        return HOTUPDATE_ERR_OPEN_FAILED;
    }

    FdGuard fd_guard(fd);

    if (!WriteAll(fd, content)) {
        unlink(tmp.c_str());
        return HOTUPDATE_ERR_WRITE_FAILED;
    }

    if (fsync(fd) != 0) {
        unlink(tmp.c_str());
        return HOTUPDATE_ERR_FSYNC_FAILED;
    }

    if (fchmod(fd, 0444) != 0) {
        unlink(tmp.c_str());
        return HOTUPDATE_ERR_CHMOD_FAILED;
    }

    if (close(fd_guard.release()) != 0) {
        unlink(tmp.c_str());
        return HOTUPDATE_ERR_WRITE_FAILED;
    }

    if (rename(tmp.c_str(), path.c_str()) != 0) {
        unlink(tmp.c_str());
        return HOTUPDATE_ERR_RENAME_FAILED;
    }

    std::string dir = DirName(path);
    int dfd = open(dir.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (dfd >= 0) {
        FdGuard dfd_guard(dfd);
        fsync(dfd);
    }

    return HOTUPDATE_OK;
}

std::string BuildContent(
        const std::string& header1,
        const std::string& header2,
        const std::vector<std::pair<std::string, std::string>>& pairs) {
    std::ostringstream oss;
    oss << header1 << "\n";
    oss << header2 << "\n";

    for (const auto& p : pairs) {
        oss << p.first << '\t' << p.second << '\n';
    }

    return oss.str();
}

int AddUniquePair(
        const std::string& list_path,
        const std::string& header1,
        const std::string& header2,
        const std::string& key,
        const std::string& value,
        size_t max_key_len,
        size_t max_value_len) {
    int ret = ValidateKeyValue(key, value, max_key_len, max_value_len);
    if (ret != HOTUPDATE_OK) {
        return ret;
    }

    ret = EnsureDir();
    if (ret != HOTUPDATE_OK) {
        return ret;
    }

    int lock_fd = open(kLockPath, O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (lock_fd < 0) {
        return HOTUPDATE_ERR_OPEN_FAILED;
    }

    FdGuard lock_guard(lock_fd);

    if (flock(lock_fd, LOCK_EX) != 0) {
        return HOTUPDATE_ERR_LOCK_FAILED;
    }

    std::vector<std::pair<std::string, std::string>> pairs;
    ret = ReadPairs(list_path, &pairs);
    if (ret != HOTUPDATE_OK) {
        flock(lock_fd, LOCK_UN);
        return ret;
    }

    for (const auto& p : pairs) {
        if (p.first == key && p.second == value) {
            chmod(list_path.c_str(), 0444);
            flock(lock_fd, LOCK_UN);
            return HOTUPDATE_OK;
        }
    }

    pairs.push_back({key, value});

    std::sort(pairs.begin(), pairs.end());
    pairs.erase(std::unique(pairs.begin(), pairs.end()), pairs.end());

    std::string content = BuildContent(header1, header2, pairs);

    ret = AtomicWriteFile(list_path, content);

    flock(lock_fd, LOCK_UN);
    return ret;
}

std::vector<std::string> ReadFirstColumnUnique(const std::string& path) {
    std::vector<std::string> result;

    int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return result;
    }

    FdGuard fd_guard(fd);

    FILE* fp = fdopen(fd_guard.release(), "r");
    if (!fp) {
        return result;
    }

    char* line = nullptr;
    size_t cap = 0;

    std::set<std::string> seen;

    while (true) {
        ssize_t n = getline(&line, &cap, fp);
        if (n < 0) {
            break;
        }

        std::string s(line, static_cast<size_t>(n));

        while (!s.empty() && (s.back() == '\n' || s.back() == '\r')) {
            s.pop_back();
        }

        if (s.empty() || s[0] == '#') {
            continue;
        }

        if (s.size() > kMaxLineLen) {
            continue;
        }

        std::string key;
        std::string value;
        if (!ParseTsvLine(s, &key, &value)) {
            continue;
        }

        if (seen.insert(key).second) {
            result.push_back(key);
        }
    }

    free(line);
    fclose(fp);

    return result;
}

}  // namespace

int hotupdatefiles(const std::string& filename, const std::string& filepath) {
    return AddUniquePair(
            kFileListPath,
            "# hotupdate file list v1",
            "# filename<TAB>filepath",
            filename,
            filepath,
            kMaxNameLen,
            kMaxPathLen);
}

int hotupdateprops(const std::string& propname, const std::string& proppath) {
    return AddUniquePair(
            kPropListPath,
            "# hotupdate prop list v1",
            "# propname<TAB>proppath",
            propname,
            proppath,
            kMaxPropNameLen,
            kMaxPathLen);
}

std::vector<std::string> gethotupdatefiles() {
    return ReadFirstColumnUnique(kFileListPath);
}

std::vector<std::string> gethotupdateprops() {
    return ReadFirstColumnUnique(kPropListPath);
}
```

---

# 6. 关于返回列表是否需要去重

虽然写入时已经保证：

```text
filename filepath
```

组合唯一，但读取接口要求返回：

```cpp
std::vector<std::string> gethotupdatefiles()
```

只返回文件名。

这意味着可能存在：

```text
foo.apk	/system/app/foo.apk
foo.apk	/product/app/foo.apk
```

此时 `filename` 相同但 `filepath` 不同。

你需要决定：

## 方案 A：返回去重后的文件名

当前代码采用这个方案。

返回：

```text
foo.apk
```

只出现一次。

## 方案 B：返回所有记录的第一列

返回：

```text
foo.apk
foo.apk
```

如果调用方需要知道不同路径，这个接口本身不够，需要改成：

```cpp
std::vector<HotUpdateFile> gethotupdatefilepairs();
```

建议你保留当前接口时使用 **文件名去重**，避免调用方重复处理。

---

# 7. 文件权限设计

你的目标：

> 任意进程可读，但不能修改，也避免被其他进程意外删除。

仅仅设置文件为：

```text
0444
```

不够。

因为在 Linux 里，**删除文件需要的是父目录写权限**，不是文件自身写权限。

所以应设置：

```text
/data/hotupdate        0555
/data/hotupdate/filelist 0444
/data/hotupdate/proplist 0444
/data/hotupdate/.lock 0600
```

这样普通进程即使能读 `filelist` 和 `proplist`，也不能删除它们，因为没有 `/data/hotupdate` 目录写权限。

但是写接口由 init 调用时，需要能临时写入：

```text
/data/hotupdate/filelist.tmp
/data/hotupdate/proplist.tmp
```

如果目录长期是 `0555`，普通写入流程也会受影响。

因此推荐以下两种方案之一。

---

# 8. 推荐权限方案

## 方案一：由 init 执行写接口，目录保持 `0700`

如果写接口只在 init 进程内执行，且读接口由普通进程访问文件，那么目录权限不能是 `0700`，否则普通进程无法穿越目录读取文件。

所以目录至少需要：

```text
0555
```

普通进程才能访问：

```text
/data/hotupdate/filelist
```

但是 `0555` 会导致即使 root 以外的普通进程不能删文件，init 作为 root 仍然可以改写。

这符合你的需求。

推荐：

```text
/data/hotupdate           0555 root root
/data/hotupdate/filelist  0444 root root
/data/hotupdate/proplist  0444 root root
/data/hotupdate/.lock     0600 root root
```

写接口内部在写之前临时：

```cpp
chmod("/data/hotupdate", 0755);
```

不推荐这样做，因为存在短暂窗口。

---

## 方案二：目录 `0711`，文件 `0444`

```text
/data/hotupdate           0711 root root
/data/hotupdate/filelist  0444 root root
/data/hotupdate/proplist  0444 root root
```

目录 `0711` 的含义：

| 权限 | 效果 |
|---|---|
| owner root 可读写执行 | root 可管理 |
| group/other 只有 execute | 普通进程不能列目录，但可以访问已知文件名 |

这样普通进程不能：

```bash
ls /data/hotupdate
```

但可以：

```bash
cat /data/hotupdate/filelist
```

只要文件本身是 `0444`。

这是更好的方案。

推荐使用：

```text
/data/hotupdate           0711 root root
/data/hotupdate/filelist  0444 root root
/data/hotupdate/proplist  0444 root root
/data/hotupdate/.lock     0600 root root
```

---

# 9. init.rc 创建目录和文件

Android init `.rc` 支持 `mkdir`、`chmod`、`chown` 等命令，AOSP init 语言文档中也有对应命令说明。([chromium.googlesource.com](https://chromium.googlesource.com/aosp/platform/system/core/%2B/refs/heads/upstream/init/?utm_source=openai))

示例：

```rc
on post-fs-data
    mkdir /data/hotupdate 0711 root root
    restorecon /data/hotupdate

    write /data/hotupdate/filelist "# hotupdate file list v1\n# filename<TAB>filepath\n"
    chown root root /data/hotupdate/filelist
    chmod 0444 /data/hotupdate/filelist
    restorecon /data/hotupdate/filelist

    write /data/hotupdate/proplist "# hotupdate prop list v1\n# propname<TAB>proppath\n"
    chown root root /data/hotupdate/proplist
    chmod 0444 /data/hotupdate/proplist
    restorecon /data/hotupdate/proplist
```

注意：

`write` 每次启动都会覆盖文件，这可能不是你想要的。

如果你希望文件持久保存，不要每次 `write` 覆盖。

更推荐：

```rc
on post-fs-data
    mkdir /data/hotupdate 0711 root root
    restorecon_recursive /data/hotupdate

    exec u:r:init:s0 root root -- /system/bin/hotupdate_init
```

然后由 `hotupdate_init` 判断文件是否存在，不存在才初始化。

---

# 10. SELinux 标签设计

建议新增专用类型：

```text
hotupdate_data_file
```

用于：

```text
/data/hotupdate
/data/hotupdate/filelist
/data/hotupdate/proplist
```

---

## 10.1 file_contexts

在 device sepolicy 中添加，例如：

```text
device/<vendor>/<device>/sepolicy/private/file_contexts
```

或对应的 vendor/device sepolicy 路径。

内容：

```text
/data/hotupdate(/.*)?        u:object_r:hotupdate_data_file:s0
```

如果你希望 `.lock` 单独管控，可以拆分：

```text
/data/hotupdate              u:object_r:hotupdate_data_file:s0
/data/hotupdate/filelist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/proplist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/\.lock       u:object_r:hotupdate_private_file:s0
```

我更推荐拆分：

```text
hotupdate_public_file
hotupdate_private_file
```

因为：

- `filelist` / `proplist` 可被广泛读取
- `.lock` 不应该被任意进程读取

推荐 file_contexts：

```text
/data/hotupdate              u:object_r:hotupdate_dir:s0
/data/hotupdate/filelist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/proplist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/\.lock       u:object_r:hotupdate_private_file:s0
/data/hotupdate/.*\.tmp      u:object_r:hotupdate_private_file:s0
```

---

## 10.2 file.te

```te
type hotupdate_dir, file_type, data_file_type;
type hotupdate_public_file, file_type, data_file_type;
type hotupdate_private_file, file_type, data_file_type;
```

---

## 10.3 允许 init 创建和写入

```te
allow init hotupdate_dir:dir {
    create
    read
    write
    open
    search
    add_name
    remove_name
    getattr
    setattr
};

allow init hotupdate_public_file:file {
    create
    read
    write
    open
    getattr
    setattr
    rename
    unlink
};

allow init hotupdate_private_file:file {
    create
    read
    write
    open
    getattr
    setattr
    rename
    unlink
    lock
};
```

如果实际写接口不是 init 域，而是某个自定义 native daemon，例如：

```text
u:r:hotupdate_service:s0
```

则应替换为：

```te
allow hotupdate_service ...
```

不要随便给 `init` 太多权限，最好由专用服务域处理。

---

# 11. 普通进程只读 SELinux 方案

你说：

> 任意进程对 filelist 和 proplist 都有可读权限，但不能修改。

Android SELinux 里不建议真的给所有 domain 放开所有权限。更稳妥方案是：

## 推荐方案

给需要调用 lib 的 domain 赋予读取权限。

例如：

```te
allow system_server hotupdate_dir:dir search;
allow system_server hotupdate_public_file:file { read open getattr };

allow platform_app hotupdate_dir:dir search;
allow platform_app hotupdate_public_file:file { read open getattr };

allow priv_app hotupdate_dir:dir search;
allow priv_app hotupdate_public_file:file { read open getattr };

allow vendor_app hotupdate_dir:dir search;
allow vendor_app hotupdate_public_file:file { read open getattr };
```

如果你确实要“任意进程”，可定义属性：

```te
allow domain hotupdate_dir:dir search;
allow domain hotupdate_public_file:file { read open getattr };
```

但这个比较宽，不建议用于高安全要求系统。

更建议用宏封装。

---

## 11.1 定义宏

`hotupdate_macros.te`：

```te
define(`r_hotupdate_public_files', `
allow $1 hotupdate_dir:dir search;
allow $1 hotupdate_public_file:file { read open getattr };
')
```

然后：

```te
r_hotupdate_public_files(system_server)
r_hotupdate_public_files(platform_app)
r_hotupdate_public_files(priv_app)
r_hotupdate_public_files(vendor_app)
r_hotupdate_public_files(hal_xxx)
```

---

# 12. 防止其他进程修改或删除

需要同时依赖三层：

## 12.1 Linux DAC 权限

```text
/data/hotupdate              0711 root root
/data/hotupdate/filelist     0444 root root
/data/hotupdate/proplist     0444 root root
/data/hotupdate/.lock        0600 root root
```

普通进程：

- 可以打开已知文件读取
- 不能列目录
- 不能创建文件
- 不能删除文件
- 不能修改文件

---

## 12.2 SELinux MAC 权限

只允许普通进程：

```te
read open getattr
```

不允许：

```te
write
create
unlink
rename
setattr
append
```

---

## 12.3 写接口限制

不要把：

```cpp
hotupdatefiles()
hotupdateprops()
```

暴露给任意应用使用。

如果它们在同一个 lib 里，普通进程也能链接到符号并调用。

但即使调用，由于 Linux 权限和 SELinux 限制，应该写失败。

不过更好的做法是：

### 拆成两个库

```text
libhotupdate_writer
libhotupdate_reader
```

其中：

```text
libhotupdate_writer
```

只给 init 或系统 native service 使用。

```text
libhotupdate_reader
```

给应用和服务使用。

如果必须同一个库，也建议用 linker namespace / Soong visibility 控制，不把 writer 头文件提供给普通 app/service。

---

# 13. Android.bp 示例

## 13.1 reader/writer 拆库推荐

```bp
cc_library {
    name: "libhotupdate_reader",
    vendor_available: true,
    srcs: [
        "hotupdate_reader.cpp",
    ],
    shared_libs: [
        "liblog",
    ],
    export_include_dirs: [
        "include",
    ],
}

cc_library {
    name: "libhotupdate_writer",
    vendor_available: false,
    srcs: [
        "hotupdate_writer.cpp",
    ],
    shared_libs: [
        "liblog",
    ],
    export_include_dirs: [
        "include",
    ],
    visibility: [
        "//system/core/init:__subpackages__",
        "//device/vendor/device/hotupdate:__subpackages__",
    ],
}
```

如果必须单库：

```bp
cc_library {
    name: "libhotupdate",
    vendor_available: true,
    srcs: [
        "hotupdate.cpp",
    ],
    shared_libs: [
        "liblog",
    ],
    export_include_dirs: [
        "include",
    ],
}
```

---

# 14. 文件初始化工具建议

建议做一个小工具：

```text
/system/bin/hotupdate_init
```

职责：

1. 创建 `/data/hotupdate`
2. 初始化 `filelist`
3. 初始化 `proplist`
4. chmod/chown
5. restorecon

但是 `restorecon` 通常由 init 命令执行更直接。

伪代码：

```cpp
mkdir("/data/hotupdate", 0711);
chown("/data/hotupdate", 0, 0);
chmod("/data/hotupdate", 0711);

if (!exists("/data/hotupdate/filelist")) {
    write default header;
}
chown(filelist, 0, 0);
chmod(filelist, 0444);

if (!exists("/data/hotupdate/proplist")) {
    write default header;
}
chown(proplist, 0, 0);
chmod(proplist, 0444);
```

init.rc：

```rc
on post-fs-data
    mkdir /data/hotupdate 0711 root root
    restorecon /data/hotupdate

    exec u:r:hotupdate_init:s0 root root -- /system/bin/hotupdate_init

    restorecon_recursive /data/hotupdate
    chmod 0711 /data/hotupdate
    chown root root /data/hotupdate
    chmod 0444 /data/hotupdate/filelist
    chmod 0444 /data/hotupdate/proplist
```

---

# 15. 更严格的写入流程建议

前面的代码使用临时文件：

```text
filelist.tmp
proplist.tmp
```

然后 `rename()`。

注意：`rename()` 后，新文件的 SELinux label 可能来自 tmp 文件标签。

所以 file_contexts 最好覆盖：

```text
/data/hotupdate/filelist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/proplist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/.*\.tmp      u:object_r:hotupdate_private_file:s0
```

但是如果 `filelist.tmp` rename 成 `filelist`，它可能保持 `hotupdate_private_file` 标签，而不是自动变为 `hotupdate_public_file`。

因此有两个选择：

## 选择 A：写完 rename 后调用 restorecon

在写接口中调用：

```cpp
restorecon("/data/hotupdate/filelist");
```

这需要引入 Android libselinux 接口。

## 选择 B：tmp 文件也使用 public label

```text
/data/hotupdate(/.*)? u:object_r:hotupdate_public_file:s0
```

简单但 `.lock` 也可能变 public，不够精细。

## 选择 C：不用 `rename`，直接在原文件上 truncate 写入

不推荐，崩溃可能导致文件损坏。

---

## 推荐做法

为了可靠性，仍然使用 `rename`。

并在 init.rc 中定期/启动时：

```rc
restorecon_recursive /data/hotupdate
```

同时在代码中可选集成 `restorecon`。

Android 系统中 `file_contexts` 的标签规则需要通过 `restorecon` 等机制应用到已有文件上；init 启动阶段会加载平台和设备相关 file_contexts。([source.android.com](https://source.android.com/docs/security/features/selinux/compatibility?utm_source=openai))

---

# 16. 加入 restorecon 的写接口增强

如果你的模块可以链接 `libselinux`，可以加：

```cpp
#include <selinux/restorecon.h>
```

Android 中常见用法类似：

```cpp
selinux_android_restorecon(path.c_str(), 0);
```

示例：

```cpp
#include <selinux/android.h>

static void RestoreConFile(const std::string& path) {
    selinux_android_restorecon(path.c_str(), 0);
}
```

在 `rename()` 后：

```cpp
selinux_android_restorecon(path.c_str(), 0);
chmod(path.c_str(), 0444);
```

Android.bp：

```bp
shared_libs: [
    "libselinux",
]
```

如果担心依赖复杂，可以不在 lib 中做 restorecon，而由 init 在写操作后或启动后修复。

但对于系统重要接口，我建议加入。

---

# 17. 更完整的 AtomicWriteFile 增强点

建议在 `rename()` 后增加：

```cpp
chmod(path.c_str(), 0444);
chown(path.c_str(), 0, 0);
restorecon(path.c_str());
```

不过注意顺序：

```text
rename
restorecon
chown
chmod
fsync directory
```

---

# 18. 是否允许文件被清空？

建议：

- 文件不存在：读接口返回空 vector
- 文件格式错误：读接口跳过错误行或返回空？

对于系统重要接口，我建议：

## 写接口

严格解析。

只要旧文件中存在非法行，返回：

```cpp
HOTUPDATE_ERR_PARSE_FAILED
```

避免在损坏文件上继续写。

## 读接口

宽容解析。

跳过非法行，返回合法项。

因为读接口被很多服务调用，不应因一行坏数据影响整体系统。

当前上面代码就是这个设计。

---

# 19. 并发设计

写接口需要考虑：

- init 多次调用
- 多个 service 同时调用 writer
- reader 正在读取时 writer 更新

方案：

| 场景 | 处理方式 |
|---|---|
| 多写并发 | `.lock` + `flock(LOCK_EX)` |
| 读写并发 | writer 使用临时文件 + rename |
| 读到半文件 | 不会，rename 原子 |
| 崩溃 | 旧文件仍在，tmp 可下次清理 |
| 重复写 | 内存 set 去重 |

读接口不加锁也可以，因为 `rename()` 是原子替换。

---

# 20. 启动时清理临时文件

init.rc 可加：

```rc
on post-fs-data
    rm /data/hotupdate/filelist.tmp
    rm /data/hotupdate/proplist.tmp
```

或者在 `hotupdate_init` 中处理。

---

# 21. 最终推荐架构

```text
/data/hotupdate/
├── filelist       0444 root root u:object_r:hotupdate_public_file:s0
├── proplist       0444 root root u:object_r:hotupdate_public_file:s0
└── .lock          0600 root root u:object_r:hotupdate_private_file:s0
```

目录：

```text
/data/hotupdate    0711 root root u:object_r:hotupdate_dir:s0
```

接口：

```cpp
int hotupdatefiles(const std::string& filename, const std::string& filepath);
int hotupdateprops(const std::string& propname, const std::string& proppath);

std::vector<std::string> gethotupdatefiles();
std::vector<std::string> gethotupdateprops();
```

文件格式：

```text
# hotupdate file list v1
# filename<TAB>filepath
filename<TAB>filepath
```

```text
# hotupdate prop list v1
# propname<TAB>proppath
propname<TAB>proppath
```

---

# 22. SELinux 最终推荐配置

## `file_contexts`

```text
/data/hotupdate              u:object_r:hotupdate_dir:s0
/data/hotupdate/filelist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/proplist     u:object_r:hotupdate_public_file:s0
/data/hotupdate/\.lock       u:object_r:hotupdate_private_file:s0
/data/hotupdate/.*\.tmp      u:object_r:hotupdate_private_file:s0
```

---

## `file.te`

```te
type hotupdate_dir, file_type, data_file_type;
type hotupdate_public_file, file_type, data_file_type;
type hotupdate_private_file, file_type, data_file_type;
```

---

## `init.te` 或对应 writer domain

```te
allow init hotupdate_dir:dir {
    create
    read
    write
    open
    search
    add_name
    remove_name
    getattr
    setattr
};

allow init hotupdate_public_file:file {
    create
    read
    write
    open
    getattr
    setattr
    rename
    unlink
};

allow init hotupdate_private_file:file {
    create
    read
    write
    open
    getattr
    setattr
    rename
    unlink
    lock
};
```

---

## reader 权限

推荐只授权必要 domain：

```te
allow system_server hotupdate_dir:dir search;
allow system_server hotupdate_public_file:file { read open getattr };

allow platform_app hotupdate_dir:dir search;
allow platform_app hotupdate_public_file:file { read open getattr };

allow priv_app hotupdate_dir:dir search;
allow priv_app hotupdate_public_file:file { read open getattr };

allow vendor_app hotupdate_dir:dir search;
allow vendor_app hotupdate_public_file:file { read open getattr };
```

如果你确实要所有 domain 可读：

```te
allow domain hotupdate_dir:dir search;
allow domain hotupdate_public_file:file { read open getattr };
```

但不建议。

---

# 23. 关键注意事项

1. **0444 文件权限不能防删除**，防删除主要靠父目录没有写权限。
2. 推荐目录权限使用 `0711`，而不是 `0777` 或 `0755`。
3. 写入必须使用 `flock + temp + fsync + rename`。
4. TSV 中必须禁止 `\t`、`\n`、`\r`、`\0`。
5. 普通进程只允许 SELinux `read/open/getattr/search`。
6. 不建议 SQLite，因为你的数据模型太简单，而且 SQLite 额外文件会增加 SELinux 和权限复杂度。
7. 如果用临时文件 rename，注意 rename 后 SELinux 标签问题，建议写接口中 restorecon 或启动时 restorecon_recursive。
8. 最好把 writer 和 reader 拆成两个库，防止普通进程误调用写接口。
9. 读接口建议容错，写接口建议严格。
10. 重复写入返回 `0`，保证接口幂等。

---

总体推荐方案：

> **TSV 明文文件 + `/data/hotupdate` 目录 0711 + 文件 0444 + SELinux 专用标签 + writer 独立授权 + flock + 原子 rename。**

---
Learn more:
1. [Policy compatibility  |  Android Open Source Project](https://source.android.com/docs/security/features/selinux/compatibility?utm_source=openai)
2. [init - aosp/platform/system/core - Git at Google](https://chromium.googlesource.com/aosp/platform/system/core/%2B/refs/heads/upstream/init/?utm_source=openai)