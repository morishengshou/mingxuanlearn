*Thinking...*

> I'm working through a comprehensive design for Android 12 hot update file management, considering whether to use TSV files or a database for the recording interfaces, then designing the four interface functions, file formats that must remain human-readable plaintext, and the SELinux permission scheme to control access.
> 
> For the TSV versus database question, TSV is clearly the right choice here—the requirement for human-readable plaintext rules out SQLite entirely since it's binary, and init runs early with minimal dependencies, so adding database complexity would be unnecessary overhead. The data structure is simple key-value pairs with small volume, making TSV efficient for this use case.
> 
> Now I'm designing the actual file formats and implementation details: the filelist would use tab-separated filename and filepath pairs, proplist would do the same for property names and paths, and I need to handle uniqueness checks, atomic writes using temp files and renames, file locking with flock, and proper escaping for special characters. The write interfaces for init need to append entries with uniqueness validation and return appropriate error codes on failure.
> 
> For the read side, the library functions parse the TSV files and return vectors of just the first column—either filenames or property names. On the SELinux side, I'm creating a new file type for hotupdate data, setting up contexts so init can write to these files while all domains can read them, and using directory permissions to prevent unauthorized deletion since SELinux denies by default when write permission isn't granted.
> 
> Now I'm writing production-quality C++ code with proper input validation, file locking for atomicity, and error handling. I'll define error codes as an enum and implement the write interfaces with flock to ensure thread-safe appends, checking for duplicates before writing. For the read interfaces, I'll parse the TSV format and return the appropriate column data.
> 
> For SELinux policy, I need to define the hotupdate_data_file type and set up the file_contexts to label the /data/hotupdate directory and files appropriately.
> 
> For write access, I'm granting init the necessary permissions to create, modify, and manage the files in that directory. For read access across all domains, I need to be careful about Android's neverallow rules that might prevent untrusted apps from accessing certain data files. Adding the mlstrustedobject attribute to the type definition will let apps bypass MLS category checks, since they run with specific categories that would otherwise block access.
> 
> I should also note that init needs to create the directory with the correct SELinux context using mkdir in init.rc followed by restorecon. For deletion protection, the combination of DAC permissions (755 directory owned by root/system) and SELinux rules (other domains lack write and remove_name permissions) prevents unauthorized deletion. On the file permissions side, even though 444 is read-only, root can still write to it because root bypasses DAC checks, though SELinux still enforces the policy.
> 
> I'll present both approaches—recommending 0644 as cleaner but respecting the user's preference for 444 and explaining how it works with root as the writer. The real deletion protection comes from the directory permissions and SELinux policy, not the file mode itself.
> 
> Writing the helper code...

# 一、TSV 还是 SQLite db？

结论很明确：**用 TSV(纯文本) 更好**。理由如下：

首先你自己已经给出了硬性约束——"文件需要使用人类可识读的明文"。SQLite 是二进制格式，直接违背这个要求，除非再额外写导出工具，得不偿失。

其次从运行环境看，`hotupdatefiles/hotupdateprops` 是**给 init 调用**的。init 是开机极早期、依赖极少的进程。引入 SQLite 意味着链接 libsqlite、处理 db 锁、WAL 日志文件、页缓存以及可能的 db 损坏恢复问题，这在 init 阶段是明显的可靠性负担。而纯文本只依赖 libc。

再看数据特征：这里的数据只是"两个字符串一组"的小规模列表，唯一性约束简单，查询模式只有"全量读取"和"追加去重"。这正是 TSV 的舒适区。SQLite 的索引、事务、SQL 查询能力在这里完全用不上。

只有当你未来出现"百万级记录、复杂条件查询、多写者高并发"时才该考虑 db。你的场景不属于这一类。

下面按 TSV 方案给出完整设计。

---

# 二、文件格式设计

采用 **TSV(Tab 分隔)**，而不是空格分隔。因为文件路径中允许包含空格，但几乎不会包含制表符，用 `\t` 做分隔符能天然规避解析歧义。

`/data/hotupdate/filelist`：

```
# hotupdate filelist v1
# <filename>\t<filepath>
libfoo.so	/system/lib64/libfoo.so
config.xml	/vendor/etc/config.xml
```

`/data/hotupdate/proplist`：

```
# hotupdate proplist v1
# <propname>\t<proppath>
ro.build.version.sdk	/data/hotupdate/local.prop
persist.sys.foo	/vendor/etc/local.prop
```

格式约定：

- 每行一条记录，字段间用单个 `\t` 分隔，行尾 `\n`。
- 以 `#` 开头的行是注释/表头，读取时忽略。
- 字段本身**不允许**包含 `\t`、`\n`、`\r`，写入接口会校验并拒绝，从而保证格式永远可解析、无需复杂转义。
- 唯一性以整行 `key\tvalue` 组合判定。

---

# 三、写接口实现(给 init 调用)

关键的健壮性措施：输入校验、`flock` 排他锁防并发、读全量去重、`fsync` 落盘、目录自动创建。重复记录视为幂等成功(返回 0)。

```cpp
// hotupdate_writer.h
#pragma once
#include <string>

// 返回 0 成功；负值为错误码
int hotupdatefiles(const std::string& filename, const std::string& filepath);
int hotupdateprops(const std::string& propname, const std::string& proppath);
```

```cpp
// hotupdate_writer.cpp
#include "hotupdate_writer.h"

#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <string>
#include <vector>

namespace {

constexpr char kDir[]      = "/data/hotupdate";
constexpr char kFileList[] = "/data/hotupdate/filelist";
constexpr char kPropList[] = "/data/hotupdate/proplist";

// 错误码
enum : int {
    HU_OK          =  0,
    HU_E_ARG       = -1,   // 参数非法(空/含非法字符)
    HU_E_MKDIR     = -2,   // 目录创建失败
    HU_E_OPEN      = -3,   // 打开文件失败
    HU_E_LOCK      = -4,   // 加锁失败
    HU_E_IO        = -5,   // 读写失败
};

// 字段合法性校验：非空、不含分隔/换行字符
bool ValidField(const std::string& s) {
    if (s.empty()) return false;
    for (char c : s) {
        if (c == '\t' || c == '\n' || c == '\r' || c == '\0') return false;
    }
    return true;
}

int EnsureDir() {
    struct stat st{};
    if (stat(kDir, &st) == 0) {
        return S_ISDIR(st.st_mode) ? HU_OK : HU_E_MKDIR;
    }
    // 0755: 属主可写，其他进程只读，配合 SELinux 防删除
    if (mkdir(kDir, 0755) != 0 && errno != EEXIST) {
        return HU_E_MKDIR;
    }
    return HU_OK;
}

// 读取整个文件内容到 buf；文件不存在返回空串且 ok=true
bool ReadAll(int fd, std::string& out) {
    out.clear();
    if (lseek(fd, 0, SEEK_SET) < 0) return false;
    char tmp[4096];
    ssize_t n;
    while ((n = read(fd, tmp, sizeof(tmp))) > 0) {
        out.append(tmp, static_cast<size_t>(n));
    }
    return n == 0;  // n<0 表示出错
}

bool WriteAll(int fd, const std::string& data) {
    const char* p = data.data();
    size_t left = data.size();
    while (left > 0) {
        ssize_t n = write(fd, p, left);
        if (n < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        p += n;
        left -= static_cast<size_t>(n);
    }
    return true;
}

// 判断 content 中是否已存在整行 line(不含换行)
bool LineExists(const std::string& content, const std::string& line) {
    size_t pos = 0;
    while (pos <= content.size()) {
        size_t eol = content.find('\n', pos);
        std::string cur = (eol == std::string::npos)
                              ? content.substr(pos)
                              : content.substr(pos, eol - pos);
        // 去掉可能的 \r
        if (!cur.empty() && cur.back() == '\r') cur.pop_back();
        if (cur == line) return true;
        if (eol == std::string::npos) break;
        pos = eol + 1;
    }
    return false;
}

// 通用去重追加
int RecordUnique(const char* path, const std::string& key,
                 const std::string& value) {
    if (!ValidField(key) || !ValidField(value)) return HU_E_ARG;

    int rc = EnsureDir();
    if (rc != HU_OK) return rc;

    // 属主写 0644：其他进程无写权限
    int fd = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0644);
    if (fd < 0) return HU_E_OPEN;

    // 排他锁，防止 init 内多命令并发写
    if (flock(fd, LOCK_EX) != 0) {
        close(fd);
        return HU_E_LOCK;
    }

    int result = HU_OK;
    std::string content;
    if (!ReadAll(fd, content)) {
        result = HU_E_IO;
    } else {
        const std::string line = key + "\t" + value;
        if (LineExists(content, line)) {
            result = HU_OK;                 // 幂等：已存在即成功
        } else {
            // 追加到文件末尾
            if (lseek(fd, 0, SEEK_END) < 0) {
                result = HU_E_IO;
            } else {
                std::string rec = line + "\n";
                if (!WriteAll(fd, rec)) {
                    result = HU_E_IO;
                } else if (fsync(fd) != 0) {  // 确保落盘
                    result = HU_E_IO;
                }
            }
        }
    }

    flock(fd, LOCK_UN);
    close(fd);
    return result;
}

}  // namespace

int hotupdatefiles(const std::string& filename, const std::string& filepath) {
    return RecordUnique(kFileList, filename, filepath);
}

int hotupdateprops(const std::string& propname, const std::string& proppath) {
    return RecordUnique(kPropList, propname, proppath);
}
```

---

# 四、读接口实现(独立编译成 lib)

读接口对任意进程开放，因此要**只读、无副作用、对畸形数据零崩溃**：文件缺失返回空 vector，忽略注释行与非法行，用共享锁 `LOCK_SH` 保证读到的是完整快照。

```cpp
// libhotupdate_reader.h
#pragma once
#include <string>
#include <vector>

std::vector<std::string> gethotupdatefiles(void);
std::vector<std::string> gethotupdateprops(void);
```

```cpp
// libhotupdate_reader.cpp
#include "libhotupdate_reader.h"

#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

#include <cerrno>
#include <string>
#include <vector>

namespace {

constexpr char kFileList[] = "/data/hotupdate/filelist";
constexpr char kPropList[] = "/data/hotupdate/proplist";

bool ReadFileLocked(const char* path, std::string& out) {
    out.clear();
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return errno == ENOENT ? true : false;  // 不存在视为空
    }
    // 共享锁：与写者的排他锁互斥，避免读到半截行
    flock(fd, LOCK_SH);

    char tmp[4096];
    ssize_t n;
    bool ok = true;
    while ((n = read(fd, tmp, sizeof(tmp))) > 0) {
        out.append(tmp, static_cast<size_t>(n));
    }
    if (n < 0) ok = false;

    flock(fd, LOCK_UN);
    close(fd);
    return ok;
}

// 提取每行的第一个字段(tab 之前)，忽略空行/注释行/无字段行
std::vector<std::string> ExtractFirstColumn(const std::string& content) {
    std::vector<std::string> result;
    size_t pos = 0;
    while (pos <= content.size()) {
        size_t eol = content.find('\n', pos);
        std::string line = (eol == std::string::npos)
                               ? content.substr(pos)
                               : content.substr(pos, eol - pos);
        if (!line.empty() && line.back() == '\r') line.pop_back();

        if (!line.empty() && line[0] != '#') {
            size_t tab = line.find('\t');
            std::string key = (tab == std::string::npos)
                                  ? line
                                  : line.substr(0, tab);
            if (!key.empty()) result.push_back(key);
        }
        if (eol == std::string::npos) break;
        pos = eol + 1;
    }
    return result;
}

std::vector<std::string> ReadColumn(const char* path) {
    std::string content;
    if (!ReadFileLocked(path, content)) return {};
    return ExtractFirstColumn(content);
}

}  // namespace

std::vector<std::string> gethotupdatefiles(void) {
    return ReadColumn(kFileList);
}

std::vector<std::string> gethotupdateprops(void) {
    return ReadColumn(kPropList);
}
```

`Android.bp` 里把 reader 编成共享库：

```python
cc_library_shared {
    name: "libhotupdate_reader",
    srcs: ["libhotupdate_reader.cpp"],
    export_include_dirs: ["include"],
    vendor_available: true,   // 视调用方而定
    cflags: ["-Wall", "-Werror"],
}
```

---

# 五、权限与 SELinux 管控方案

你的目标是"**任意进程可读，任何进程都不能改、也不能删**(写者除外)"。这需要 DAC + SELinux 两层配合。这里有一个非常关键的、容易被忽略的点：

> **文件权限 444 只能防"改内容"，防不了"删文件"。能否删除一个文件取决于对它所在目录的写权限,而不是文件本身的权限。**

所以真正阻止删除的是**目录权限**和 **SELinux 对目录的 `remove_name` 控制**。

## 1. DAC 层

- 目录 `/data/hotupdate`:`0755 root system`,只有属主(root)能在其中增删文件,其他进程无目录写权限→无法删除里面的文件。
- 文件本身:建议 `0644 root system`。若你坚持用 `444`,init 作为 root 拥有 `CAP_DAC_OVERRIDE`,仍能改写,但阅读性上 644/444 对普通进程都是只读,效果等价。**关键是目录别给别人写权限。**

在 init.rc 里创建:

```
on post-fs-data
    mkdir /data/hotupdate 0755 root system
    restorecon_recursive /data/hotupdate
```

## 2. SELinux 层

### (a) 定义新类型

`file.te`(或独立 `hotupdate.te`):

```
# 注意 mlstrustedobject：让不同 MLS 类别的 app 也能跨类别读取该文件
type hotupdate_data_file, file_type, data_file_type, core_data_file_type, mlstrustedobject;
```

`mlstrustedobject` 很重要——普通应用运行在带 category(如 `c512,c768`)的 MLS 上下文,不加这个属性,跨 app 读取会被 MLS 规则拦掉。

### (b) 打标签

`file_contexts`:

```
/data/hotupdate(/.*)?    u:object_r:hotupdate_data_file:s0
```

### (c) 只给写者(init 域)写权限

假设写操作发生在 init 域(若是独立 service,替换为对应域名):

```
# 目录：可增删条目(add_name/remove_name 决定能否创建/删除文件)
allow init hotupdate_data_file:dir {
    create search open read getattr setattr add_name remove_name write
};
# 文件：可读写改
allow init hotupdate_data_file:file {
    create open read write append getattr setattr lock unlink rename
};
```

### (d) 给所有域只读权限

```
# 除写者外，其余域只授予读取相关权限，绝不给 write/append/unlink/rename
allow { domain -init } hotupdate_data_file:dir  { search open read getattr };
allow { domain -init } hotupdate_data_file:file { open read getattr lock };
```

### (e) 用 neverallow 上锁,把约束固化(推荐)

这一步是"务必可靠"的点睛之笔,它能在编译期就阻止任何人误加写权限:

```
# 除 init 外，任何域都不得写/追加/删除/重命名该文件
neverallow { domain -init } hotupdate_data_file:file
    { write append create unlink rename setattr };
# 除 init 外，任何域都不得在该目录增删条目(防删除的关键)
neverallow { domain -init } hotupdate_data_file:dir
    { add_name remove_name write };
```

## 三层防护如何协同

删除防护:其他进程既没有目录 DAC 写权限,SELinux 也不授予 `dir remove_name`,双重拦截,无法 `unlink`。修改防护:文件对其他进程 DAC 只读,且 SELinux 不给 `file write/append`。读取放行:`allow ... :file { open read }` + `mlstrustedobject` 保证任意进程(含跨 MLS 的 app)都能读。而 `neverallow` 把这些约束固化在编译期,防止后续被人误改策略。

---

# 六、几点补充建议

关于并发,`flock` 是建议性锁,只对同样使用 `flock` 的进程有效。由于写者只有 init、且读者都走本 lib(已加 `LOCK_SH`),这套约定是自洽的;再叠加 SELinux 只有 init 能写,实际上写并发几乎不存在,锁主要用于保证读者不会读到追加到一半的行。

关于原子性,当前实现用"追加单行 + fsync"。因为单行通常远小于 `PIPE_BUF`,在持锁下追加是安全的。若你未来需要"整体重写"语义(比如清空重建),请改用"写临时文件 + `rename()`"的原子替换方式,并对临时文件同样 `restorecon`。

关于错误码,我用了 `-1 ~ -5` 的负值区分参数、目录、打开、加锁、IO 五类异常,你可以按团队规范映射成正值或统一的 errno 体系。重复记录我按幂等处理返回 0,如果你的业务需要区分"新增"和"已存在",可以额外增加一个正值返回码而不破坏"0=成功"的约定。

如果写接口实际不是在 init 主域、而是某个由 init 拉起的 service 里执行,请把上面 SELinux 规则中的 `init` 替换成该 service 的域名,并相应调整 `neverallow` 的排除项。要不要我帮你把它做成一个带独立域(如 `hotupdate_writer`)的完整 service sepolicy 模板?