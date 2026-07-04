*Thinking...*

> 用户在用中文提出一个详细的Android系统工程问题。他们需要我分析TSV和数据库格式的选择（由于需要人类可读的纯文本格式，TSV更合适），设计写入接口供init调用（hotupdatefiles和hotupdateprops），设计库中的读取接口（gethotupdatefiles和gethotupdateprops），以及设计/data/hotupdate/filelist和相关目录的文件格式。
> 
> 现在我需要补充SELinux策略设计，确保文件对任何进程可读但仅init可写，并防止删除。
> 
> 对于TSV vs数据库的选择，由于数据量小、结构简单（两列），且需要人类可读的纯文本格式，TSV是最佳选择。在init中使用SQLite会增加不必要的依赖和复杂性，而TSV通过原子写操作（临时文件+重命名）可以轻松实现，调试时也能直接用cat查看，不需要事务或并发控制这些数据库才能提供的功能。
> 
> 文件格式采用制表符分隔的纯文本，每行一条记录，支持#开头的注释行，使用UTF-8编码。写入实现需要验证输入（无制表符、换行符、合理长度限制），创建/data/hotupdate目录，检查重复项（重复时返回0保证幂等性），通过原子写操作（写入临时文件、fsync、重命名、fsync目录）确保数据一致性。由于仅init调用此接口，可能不需要文件锁，但为了健壮性可以使用flock。
> 
> 文件权限设为0444，临时文件以0644创建后通过fchmod改为0444。读取实现作为库函数，打开文件只读解析，跳过注释和空行，按首个制表符分割验证两个字段，文件不存在时返回空向量。由于写入使用原子重命名，读取无需加锁即可保证看到一致的完整文件内容。SELinux设计中文件权限为0444 root:root，目录0755 root:root，DAC权限不足以防止root进程删除，需要依赖目录写权限控制。
> 
> 定义新的SELinux类型hotupdate_data_file，在file_contexts中映射/data/hotupdate路径，init通过mkdir创建目录并通过restorecon应用SELinux上下文。
> 
> 为了安全起见，在init.te中显式允许init对该目录的创建权限。对于读取访问，需要在domain.te中添加规则允许所有域搜索和读取该文件类型，但要注意AOSP中的neverallow限制——untrusted应用无法访问大多数data_file_type，除非该类型被添加到应用数据文件的例外列表中或使用app_data_file_type属性。 The issue is that if I declare the type with `data_file_type` attribute, the neverallow rules in app_neverallows.te will block untrusted apps from accessing it unless the type is explicitly whitelisted. Looking at the actual neverallow constraints, they restrict untrusted apps from accessing most data_file_type entries except for specific whitelisted types like app_data_file and media_data_file. So even if device policy adds allow rules, the platform-level neverallows would cause a build failure. The real options are either to whitelist the new type in the platform neverallow (which requires platform changes), or to avoid the data_file_type attribute entirely and use a different approach like exposing the data through a system service API instead. I need to exclude isolated_app along with untrusted apps from the broad domain grant to satisfy neverallow rules, or alternatively route access through system services for apps that genuinely need it. For write protection, I'm restricting modifications to init only via explicit allow rules and corresponding neverallows that block all other domains from writing, appending, unlinking, or renaming the hotupdate data files and directories. Since the write API is called by init, I should provide a C++ implementation as a static library that links into init, avoiding standard exceptions since init uses C++ but with specific constraints.
> 
> The functions must run after /data is mounted in the post-fs-data phase, so I'll note that the directory should be created there with the encryption=Require option for Android 12 FBE compliance. I'm designing an error code enum to handle various failure cases like invalid arguments, file operations, locking, and directory creation, then implementing shared logic for a record-adding function that validates inputs like ensuring non-empty strings without tabs or newlines and enforcing length limits.
> 
> For the write path, I'll use a lock on the list file, read existing content to check for duplicates, write atomically via a temporary file with O_TRUNC, then rename it into place with directory fsync for crash safety. The reader will parse the file line-by-line, split on tabs, and deduplicate names while preserving order since the same filename could appear with different paths. I'm also setting up the Android.bp build configuration for the shared library with logging support and vendor availability.
> 
> Now I'm defining the header with error codes and the public API functions for updating files and properties, then starting the implementation with the necessary system headers for file operations and locking.
> 
> Writing implementation code... Writing AddRecord function... Adding SELinux policy rules... Writing the header and implementation files... Writing utility functions... Writing file operations... Writing build configuration... Adding SELinux file permissions... I'm defining neverallow rules to prevent unauthorized writes to the hotupdate data files—blocking open, write, append, create, and other modification operations except for init. For directories, I'm restricting write, add_name, remove_name, and similar operations. On the DAC side, directories are 0755 root:root so only root can modify entries, and files are 0444 read-only. I should note that SELinux is the real enforcement layer here since root with CAP_DAC_OVERRIDE can bypass DAC anyway. On userdebug builds, the su domain is permissive, so root shells could theoretically delete files, but user builds don't have this issue. For the TSV versus database question, TSV is the better choice—it's human-readable, keeps init's dependencies minimal (sqlite in init is inappropriate), handles the small key-value data simply, and atomic renames provide crash consistency without needing locks or transactions.
> 
> Writing the C++ code... The lock file should only be writable by init with O_RDWR access, and the neverallow rule prevents other domains from creating it. For the reader side, I need to handle cases where the file might not exist (returning an empty vector) and can't distinguish between errors and empty files, so I'll log any issues that occur. The code should be organized in a directory structure with separate writer and reader implementations, each with their own helper functions.

# 一、TSV 还是 DB？

结论：**用 TSV（tab 分隔的明文文件），不要用 sqlite**。理由如下：

**需求本身已经排除了 DB**。你明确要求"人类可识读的明文"，sqlite 是二进制格式，`cat` 出来不可读，出问题时现场调试必须依赖 sqlite3 工具（user 版本机器上通常没有）。

**写入方是 init**。init 是系统第一个进程，应保持最小依赖。把 libsqlite 链接进 init 会增大 init 的体积和攻击面，而且 sqlite 依赖的一些环境（如 tmp 目录、mmap 行为）在 init 早期阶段并不友好。用纯 POSIX 调用写 TSV，零额外依赖。

**数据模型极简**。就是两列字符串、条数很少（热更新的文件/属性数量通常是个位数到几十条）、单写者（只有 init 写）、多读者（只读）。DB 的核心价值——并发写事务、索引、复杂查询——在这里一条都用不上。

**一致性可以用更简单的手段保证**。TSV 的写入采用"写临时文件 + fsync + rename"的原子替换方案，读者永远只会看到完整的旧文件或完整的新文件，天然免锁，掉电也不会出现半条记录，可靠性不输 DB 的事务。

TSV 唯一的弱点是字段里不能含分隔符（tab/换行），这一点在写接口里做输入校验即可彻底封死。

# 二、文件格式设计

两个文件采用相同格式：

```
# /data/hotupdate/filelist  —— 格式 v1
# 每行一条记录：filename<TAB>filepath，UTF-8 编码，'#' 开头为注释行
libfoo.so	/data/hotupdate/files/libfoo.so
libbar.so	/data/hotupdate/files/libbar.so
```

```
# /data/hotupdate/proplist
persist.vendor.foo.enable	/data/hotupdate/props/local.prop
ro.vendor.bar.version	/data/hotupdate/props/local.prop
```

格式约定：每行一条记录，两个字段用**单个 `\t`** 分隔，行尾 `\n`；空行和 `#` 开头的行被解析器忽略；字段中禁止出现 `\t`、`\n`、`\r`、`\0`（由写接口校验拒绝）；`(key, value)` 组合唯一，重复写入幂等返回 0。选 tab 而不是空格做分隔符，是因为文件路径中出现空格是合法的，而 tab 可以在写入口被无成本地禁止。

# 三、代码实现

建议的目录结构：

```
system/core/hotupdate/
├── Android.bp
├── include/hotupdate/hotupdate.h
├── hotupdate_writer.cpp    → 静态库 libhotupdate_writer，链入 init
└── hotupdate_reader.cpp    → 动态库 libhotupdate.so，给应用/服务
```

## 公共头文件 include/hotupdate/hotupdate.h

```cpp
#pragma once

#include <string>
#include <vector>

namespace android {
namespace hotupdate {

// 错误码：0 成功，负值为具体错误
enum : int {
    HOTUPDATE_OK          = 0,
    HOTUPDATE_ERR_ARG     = -1,  // 参数非法（空、含分隔符、超长、路径非绝对路径）
    HOTUPDATE_ERR_MKDIR   = -2,  // /data/hotupdate 目录创建失败
    HOTUPDATE_ERR_LOCK    = -3,  // 获取文件锁失败
    HOTUPDATE_ERR_OPEN    = -4,  // 打开列表文件失败
    HOTUPDATE_ERR_READ    = -5,  // 读取列表文件失败
    HOTUPDATE_ERR_WRITE   = -6,  // 写入临时文件失败
    HOTUPDATE_ERR_RENAME  = -7,  // 原子替换失败
    HOTUPDATE_ERR_TOOBIG  = -8,  // 列表文件尺寸超过安全上限
};

// ---- 写接口：仅供 init 调用（链接 libhotupdate_writer 静态库）----
int hotupdatefiles(const std::string& filename, const std::string& filepath);
int hotupdateprops(const std::string& propname, const std::string& proppath);

// ---- 读接口：libhotupdate.so 导出，任意进程可调用 ----
// 文件不存在或无有效记录时返回空 vector
std::vector<std::string> gethotupdatefiles();
std::vector<std::string> gethotupdateprops();

}  // namespace hotupdate
}  // namespace android
```

## 写实现 hotupdate_writer.cpp

```cpp
#define LOG_TAG "hotupdate"

#include "hotupdate/hotupdate.h"

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <string>
#include <vector>

#include <log/log.h>

namespace android {
namespace hotupdate {
namespace {

constexpr char kDir[]      = "/data/hotupdate";
constexpr char kLockPath[] = "/data/hotupdate/.lock";
constexpr char kFileList[] = "/data/hotupdate/filelist";
constexpr char kPropList[] = "/data/hotupdate/proplist";

constexpr size_t kMaxFieldLen  = 1024;       // 单字段长度上限
constexpr size_t kMaxListBytes = 1 << 20;    // 列表文件 1MB 上限，防异常膨胀
constexpr mode_t kListMode     = 0444;

// 简单的 fd RAII 封装，保证任何返回路径都不泄漏 fd
class UniqueFd {
  public:
    explicit UniqueFd(int fd = -1) : fd_(fd) {}
    ~UniqueFd() { reset(); }
    UniqueFd(const UniqueFd&) = delete;
    UniqueFd& operator=(const UniqueFd&) = delete;
    void reset(int fd = -1) {
        if (fd_ >= 0) close(fd_);
        fd_ = fd;
    }
    int get() const { return fd_; }
  private:
    int fd_;
};

bool IsValidField(const std::string& s) {
    if (s.empty() || s.size() > kMaxFieldLen) return false;
    if (s[0] == '#') return false;  // 避免与注释行冲突
    for (unsigned char c : s) {
        if (c == '\t' || c == '\n' || c == '\r' || c == '\0') return false;
    }
    return true;
}

bool WriteFully(int fd, const char* data, size_t len) {
    while (len > 0) {
        ssize_t n = TEMP_FAILURE_RETRY(write(fd, data, len));
        if (n <= 0) return false;
        data += n;
        len -= static_cast<size_t>(n);
    }
    return true;
}

// 读整个文件。文件不存在视为成功且内容为空。
int ReadWholeFile(const char* path, std::string* out) {
    out->clear();
    UniqueFd fd(TEMP_FAILURE_RETRY(open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW)));
    if (fd.get() < 0) {
        if (errno == ENOENT) return HOTUPDATE_OK;
        ALOGE("open %s for read failed: %s", path, strerror(errno));
        return HOTUPDATE_ERR_OPEN;
    }
    char buf[4096];
    for (;;) {
        ssize_t n = TEMP_FAILURE_RETRY(read(fd.get(), buf, sizeof(buf)));
        if (n < 0) {
            ALOGE("read %s failed: %s", path, strerror(errno));
            return HOTUPDATE_ERR_READ;
        }
        if (n == 0) break;
        out->append(buf, static_cast<size_t>(n));
        if (out->size() > kMaxListBytes) {
            ALOGE("%s exceeds size limit", path);
            return HOTUPDATE_ERR_TOOBIG;
        }
    }
    return HOTUPDATE_OK;
}

// 解析出所有格式合法的记录行（"key\tvalue"），非法行直接丢弃（自愈）
std::vector<std::string> ParseRecords(const std::string& content) {
    std::vector<std::string> records;
    size_t pos = 0;
    while (pos < content.size()) {
        size_t eol = content.find('\n', pos);
        std::string line = (eol == std::string::npos)
                               ? content.substr(pos)
                               : content.substr(pos, eol - pos);
        pos = (eol == std::string::npos) ? content.size() : eol + 1;

        if (line.empty() || line[0] == '#') continue;
        size_t tab = line.find('\t');
        if (tab == std::string::npos || tab == 0 || tab == line.size() - 1) continue;
        if (line.find('\t', tab + 1) != std::string::npos) continue;  // 多于两列
        records.push_back(std::move(line));
    }
    return records;
}

int AddRecord(const char* list_path, const std::string& key, const std::string& value) {
    // 1. 输入校验
    if (!IsValidField(key) || !IsValidField(value)) {
        ALOGE("invalid argument for %s", list_path);
        return HOTUPDATE_ERR_ARG;
    }
    if (value[0] != '/') {  // 路径必须是绝对路径
        ALOGE("path must be absolute: %s", value.c_str());
        return HOTUPDATE_ERR_ARG;
    }

    // 2. 确保目录存在（init.rc 中已 mkdir，此处兜底）
    if (mkdir(kDir, 0755) != 0 && errno != EEXIST) {
        ALOGE("mkdir %s failed: %s", kDir, strerror(errno));
        return HOTUPDATE_ERR_MKDIR;
    }

    // 3. 排他锁：防止未来出现并发写入者时互相踩踏
    UniqueFd lock_fd(TEMP_FAILURE_RETRY(
        open(kLockPath, O_RDWR | O_CREAT | O_CLOEXEC, 0600)));
    if (lock_fd.get() < 0 || flock(lock_fd.get(), LOCK_EX) != 0) {
        ALOGE("lock %s failed: %s", kLockPath, strerror(errno));
        return HOTUPDATE_ERR_LOCK;
    }

    // 4. 读取现有内容并去重（重复写入幂等返回 0）
    std::string content;
    int rc = ReadWholeFile(list_path, &content);
    if (rc != HOTUPDATE_OK) return rc;

    std::string record = key;
    record += '\t';
    record += value;

    std::vector<std::string> records = ParseRecords(content);
    for (const auto& r : records) {
        if (r == record) return HOTUPDATE_OK;
    }
    records.push_back(record);

    std::string new_content;
    for (const auto& r : records) {
        new_content += r;
        new_content += '\n';
    }

    // 5. 原子替换：写临时文件 -> fchmod 0444 -> fsync -> rename -> fsync 目录
    std::string tmp_path = std::string(list_path) + ".tmp";
    unlink(tmp_path.c_str());  // 清理可能残留的临时文件
    UniqueFd tmp_fd(TEMP_FAILURE_RETRY(
        open(tmp_path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0644)));
    if (tmp_fd.get() < 0) {
        ALOGE("open %s failed: %s", tmp_path.c_str(), strerror(errno));
        return HOTUPDATE_ERR_OPEN;
    }
    if (!WriteFully(tmp_fd.get(), new_content.data(), new_content.size()) ||
        fchmod(tmp_fd.get(), kListMode) != 0 ||
        fsync(tmp_fd.get()) != 0) {
        ALOGE("write %s failed: %s", tmp_path.c_str(), strerror(errno));
        unlink(tmp_path.c_str());
        return HOTUPDATE_ERR_WRITE;
    }
    tmp_fd.reset();

    if (rename(tmp_path.c_str(), list_path) != 0) {
        ALOGE("rename to %s failed: %s", list_path, strerror(errno));
        unlink(tmp_path.c_str());
        return HOTUPDATE_ERR_RENAME;
    }

    // fsync 目录，确保 rename 落盘，掉电后目录项不丢
    UniqueFd dir_fd(TEMP_FAILURE_RETRY(
        open(kDir, O_RDONLY | O_DIRECTORY | O_CLOEXEC)));
    if (dir_fd.get() >= 0) fsync(dir_fd.get());

    return HOTUPDATE_OK;
}

}  // namespace

int hotupdatefiles(const std::string& filename, const std::string& filepath) {
    return AddRecord(kFileList, filename, filepath);
}

int hotupdateprops(const std::string& propname, const std::string& proppath) {
    return AddRecord(kPropList, propname, proppath);
}

}  // namespace hotupdate
}  // namespace android
```

## 读实现 hotupdate_reader.cpp

```cpp
#define LOG_TAG "hotupdate"

#include "hotupdate/hotupdate.h"

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

#include <set>
#include <string>
#include <vector>

#include <log/log.h>

namespace android {
namespace hotupdate {
namespace {

constexpr char kFileList[] = "/data/hotupdate/filelist";
constexpr char kPropList[] = "/data/hotupdate/proplist";
constexpr size_t kMaxListBytes = 1 << 20;

// 读取列表文件第一列。任何异常（不存在/超限/格式错）都退化为
// 跳过或返回空列表，绝不让调用方崩溃。
std::vector<std::string> ReadFirstColumn(const char* path) {
    std::vector<std::string> result;

    int raw_fd = TEMP_FAILURE_RETRY(open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW));
    if (raw_fd < 0) {
        if (errno != ENOENT) {
            ALOGW("open %s failed: %s", path, strerror(errno));
        }
        return result;  // 文件不存在 = 无热更新记录
    }

    std::string content;
    char buf[4096];
    for (;;) {
        ssize_t n = TEMP_FAILURE_RETRY(read(raw_fd, buf, sizeof(buf)));
        if (n < 0) {
            ALOGW("read %s failed: %s", path, strerror(errno));
            close(raw_fd);
            return {};
        }
        if (n == 0) break;
        content.append(buf, static_cast<size_t>(n));
        if (content.size() > kMaxListBytes) {
            ALOGW("%s exceeds size limit, ignored", path);
            close(raw_fd);
            return {};
        }
    }
    close(raw_fd);

    std::set<std::string> seen;  // 去重，保持首次出现的顺序
    size_t pos = 0;
    while (pos < content.size()) {
        size_t eol = content.find('\n', pos);
        std::string line = (eol == std::string::npos)
                               ? content.substr(pos)
                               : content.substr(pos, eol - pos);
        pos = (eol == std::string::npos) ? content.size() : eol + 1;

        if (line.empty() || line[0] == '#') continue;
        size_t tab = line.find('\t');
        if (tab == std::string::npos || tab == 0 || tab == line.size() - 1) {
            ALOGW("malformed line in %s, skipped", path);
            continue;
        }
        std::string key = line.substr(0, tab);
        if (seen.insert(key).second) {
            result.push_back(std::move(key));
        }
    }
    return result;
}

}  // namespace

std::vector<std::string> gethotupdatefiles() {
    return ReadFirstColumn(kFileList);
}

std::vector<std::string> gethotupdateprops() {
    return ReadFirstColumn(kPropList);
}

}  // namespace hotupdate
}  // namespace android
```

由于写侧采用 rename 原子替换，读侧不需要任何锁，任何时刻打开的文件都是完整一致的版本。

## Android.bp

```python
cc_library_static {
    name: "libhotupdate_writer",
    srcs: ["hotupdate_writer.cpp"],
    export_include_dirs: ["include"],
    static_libs: ["liblog"],
    cflags: ["-Wall", "-Werror"],
    recovery_available: true,
}

cc_library_shared {
    name: "libhotupdate",
    srcs: ["hotupdate_reader.cpp"],
    export_include_dirs: ["include"],
    shared_libs: ["liblog"],
    cflags: ["-Wall", "-Werror"],
    vendor_available: true,   // 如有 vendor 进程需要调用则保留
}
```

写库做成静态库链入 init（在 init 的 Android.bp 的 `static_libs` 中加入 `libhotupdate_writer`）；读库做成 `libhotupdate.so` 供服务和应用链接。注意写接口只能在 `/data` 挂载并解密之后（即 `post-fs-data` 之后）调用。

# 四、权限与 SELinux 管控方案

## DAC 层

目录 `/data/hotupdate` 设为 `0755 root:root`，两份列表文件 `0444 root:root`。删除文件的权限由**目录**的写权限决定，目录只有 root 可写，配合文件 0444，非 root 进程在 DAC 层既不能改也不能删。但要清楚：root 进程持有 `CAP_DAC_OVERRIDE`，DAC 拦不住它们，真正的强制防线是 SELinux。

在 init.rc 中创建目录（Android 12 的 FBE 要求新的 /data 顶层目录显式声明加密策略）：

```
on post-fs-data
    mkdir /data/hotupdate 0755 root root encryption=Require
```

init 的 mkdir 会自动按 file_contexts 打上正确的 SELinux 标签。

## SELinux 层

**第一步，定义新类型**（放在 system/sepolicy 或 system_ext 的 `file.te`）：

```
type hotupdate_data_file, file_type, data_file_type, core_data_file_type;
```

`file_type` 和 `data_file_type` 是 /data 下文件的强制属性（缺失会触发编译期 neverallow 检查失败）。

**第二步，file_contexts 打标签**：

```
/data/hotupdate(/.*)?    u:object_r:hotupdate_data_file:s0
```

**第三步，授予 init 完整管理权限**（`init.te`）：

```
allow init hotupdate_data_file:dir create_dir_perms;
allow init hotupdate_data_file:file create_file_perms;
```

**第四步，授予全局只读权限**（`domain.te` 或单独的 te 文件）：

```
allow { domain -all_untrusted_apps -isolated_app } hotupdate_data_file:dir search;
allow { domain -all_untrusted_apps -isolated_app } hotupdate_data_file:file r_file_perms;
```

`r_file_perms` 展开为 `{ getattr open read ioctl lock map watch watch_reads }`，只含读语义。这里必须排除 untrusted app 和 isolated app，因为 AOSP 平台策略中存在 neverallow，禁止不受信应用打开绝大多数 `data_file_type` 文件，不排除会直接编译失败。如果业务上确实需要普通三方应用读到这份列表，不要硬开文件权限，而是通过一个系统服务的 Binder 接口转发，或把结果写进一条只读系统属性——这是更符合 Android 安全模型的做法。

另外提醒一点：`core_data_file_type` 会受 Treble 的 core/vendor 数据隔离 neverallow 约束。如果你的调用方全部是 system 侧进程（coredomain），按上面写即可；如果有 **vendor 域进程**也要链接 libhotupdate.so 读文件，类型需要定义在 public 策略中让 vendor 策略可见，并需评估是否去掉 `core_data_file_type` 属性以规避 Treble 隔离的 neverallow，建议在你的具体策略基线上编译验证。

**第五步，用 neverallow 把"只有 init 能写、任何人不能删"固化成编译期红线**，防止后人误加权限：

```
neverallow { domain -init } hotupdate_data_file:file
    { write append create unlink rename setattr relabelfrom };
neverallow { domain -init } hotupdate_data_file:dir
    { write add_name remove_name rename reparent rmdir relabelfrom };
```

这样即使未来有人在别的 te 文件里给某个域加了写权限，整个 sepolicy 都无法编译通过。

最后两点提醒：其一，userdebug/eng 版本上 `su` 域是 permissive 的，adb root 后仍然可以删掉这两个文件，这是调试版本的固有行为，user 版本不受影响；其二，`/data` 在恢复出厂设置时会被整体清空，filelist/proplist 会随之消失，你的热更新方案需要把"文件不存在等于无更新"作为正常初始状态处理——上面读接口返回空 vector 的设计正是为此。