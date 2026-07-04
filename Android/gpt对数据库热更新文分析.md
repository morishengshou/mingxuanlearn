使用数据库，尤其是 **SQLite**，确实可以更自然地解决：

```text
查重
并发读写
结构化存储
后续扩展
```

但在你这个 Android 12 系统接口场景里，是否更好，需要分情况看。

结论先说：

> **SQLite 可以解决查重，也能提供更规范的并发和事务能力；但对你当前只维护两个小型清单文件的需求来说，SQLite 未必比明文文件更合适。**
>
> 如果记录量很小、要求人类可读、接口简单，我仍然更推荐：
>
> ```text
> 明文 TSV + 加锁 + 去重 + 原子重写
> ```
>
> 如果未来记录量大、字段多、查询条件复杂、需要频繁写入，则可以考虑 SQLite。

---

# 1. SQLite 能不能解决查重？

可以，而且非常适合。

你可以在 SQLite 中建表并设置唯一约束：

```sql
CREATE TABLE hotupdate_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(filename, filepath)
);
```

属性表：

```sql
CREATE TABLE hotupdate_props (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    propname TEXT NOT NULL,
    proppath TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(propname, proppath)
);
```

写入时使用：

```sql
INSERT OR IGNORE INTO hotupdate_files(filename, filepath, created_at)
VALUES (?, ?, ?);
```

或者：

```sql
INSERT INTO hotupdate_files(filename, filepath, created_at)
VALUES (?, ?, ?)
ON CONFLICT(filename, filepath) DO NOTHING;
```

这样可以天然保证：

```text
filename + filepath 唯一
propname + proppath 唯一
```

---

# 2. SQLite 读写效率会更好吗？

## 2.1 小数据量场景

如果你的文件内容只有：

```text
几十条
几百条
几千条
```

而且读接口只是：

```cpp
gethotupdatefiles()
gethotupdateprops()
```

这种全量读取场景，SQLite **不一定更快**。

原因是 SQLite 每次需要：

- 打开数据库
- 加载 schema
- 准备 SQL 语句
- 执行查询
- 遍历结果
- 做 SQLite 内部锁和页缓存管理

而明文文件只需要：

```text
open -> read -> split lines -> parse
```

对于小文件，明文读取往往更简单、更快。

---

## 2.2 大数据量场景

如果记录达到：

```text
几万条
几十万条
```

并且你需要：

```text
按 filename 查
按 filepath 查
按 propname 查
判断是否存在
分页
排序
删除
更新
统计
```

那么 SQLite 明显更合适。

有索引后：

```sql
CREATE INDEX idx_hotupdate_files_filename ON hotupdate_files(filename);
CREATE INDEX idx_hotupdate_props_propname ON hotupdate_props(propname);
```

查找效率会比每次扫描文本文件好很多。

---

## 2.3 写入效率

SQLite 对单条写入会有事务、日志、fsync 成本。

如果每次写一条都单独提交：

```text
BEGIN
INSERT
COMMIT
```

性能未必比明文追加好。

但如果批量写入：

```text
BEGIN TRANSACTION
INSERT ...
INSERT ...
INSERT ...
COMMIT
```

SQLite 会很高效。

---

# 3. SQLite 可以解决并发问题吗？

可以，比手写文件锁更完善。

SQLite 支持：

- 多进程并发读
- 写事务串行化
- 崩溃恢复
- 唯一约束
- journal 或 WAL
- 原子提交

对你的场景来说：

```text
多个进程同时读
一个可信进程写
```

SQLite 可以很好支持。

不过也要注意：

```text
多写进程并发时，仍然可能出现 SQLITE_BUSY
```

因此代码里仍要处理：

```cpp
SQLITE_BUSY
SQLITE_LOCKED
```

需要设置：

```cpp
sqlite3_busy_timeout(db, 5000);
```

---

# 4. SQLite 的最大问题：与你的“任意进程可读”需求冲突

你当前需求是：

```text
任意进程对 /data/hotupdate/filelist 和 /data/hotupdate/proplist 可读
文件权限 0444
```

如果改成 SQLite，数据库文件通常不是一个文件，而可能包括：

```text
/data/hotupdate/hotupdate.db
/data/hotupdate/hotupdate.db-wal
/data/hotupdate/hotupdate.db-shm
```

如果启用 WAL，会有：

```text
-wal
-shm
```

这会带来权限和 SELinux 管控复杂性。

---

## 4.1 SQLite 读库可能需要写权限？

这是很多人容易忽略的点。

SQLite 即使只是读数据库，在某些模式下也可能需要：

- 创建或访问 `-wal`
- 创建或访问 `-shm`
- 获取锁
- 写共享内存文件
- 更新 journal 状态

尤其是 WAL 模式下，普通 reader 可能需要访问：

```text
hotupdate.db-wal
hotupdate.db-shm
```

如果你只给：

```text
0444
```

可能导致读失败。

---

## 4.2 只读打开 SQLite 可以缓解

可以用只读方式打开：

```cpp
sqlite3_open_v2(path,
                &db,
                SQLITE_OPEN_READONLY | SQLITE_OPEN_FULLMUTEX,
                nullptr);
```

但仍要考虑：

- 数据库是否处于 WAL 模式
- 是否存在 `-wal` 文件
- reader 是否能读 `-wal`
- 是否需要访问 `-shm`
- Android 上 SELinux 是否允许

---

## 4.3 可以禁用 WAL

使用 rollback journal 模式：

```sql
PRAGMA journal_mode=DELETE;
```

或者：

```sql
PRAGMA journal_mode=TRUNCATE;
```

但写事务时可能会产生：

```text
hotupdate.db-journal
```

这又涉及文件权限和 SELinux。

---

## 4.4 使用 immutable 只读模式

SQLite 支持 URI 参数：

```text
file:/data/hotupdate/hotupdate.db?immutable=1
```

只读打开：

```cpp
sqlite3_open_v2(
    "file:/data/hotupdate/hotupdate.db?immutable=1",
    &db,
    SQLITE_OPEN_READONLY | SQLITE_OPEN_URI,
    nullptr);
```

`immutable=1` 告诉 SQLite：

```text
数据库文件不会被当前连接修改，也不检查锁
```

这样读更简单，但有风险：

- 如果写进程正在更新数据库，reader 可能看到不一致状态
- 必须保证写入用原子替换数据库文件
- 不适合普通 SQLite 事务并发模型

---

# 5. 数据库对“人类可读调试”不友好

你明确要求：

```text
文件需要使用人类可识读的明文
```

SQLite 是二进制格式。

你可以通过：

```sh
sqlite3 /data/hotupdate/hotupdate.db "select * from hotupdate_files;"
```

查看，但它不是：

```sh
cat /data/hotupdate/filelist
```

这种直接明文。

这与当前需求不完全一致。

除非你同时维护：

```text
hotupdate.db
filelist 明文导出
proplist 明文导出
```

但这样又会引入：

```text
双写一致性问题
```

---

# 6. 使用 SQLite 的风险

## 6.1 权限模型复杂

原本明文文件只有：

```text
filelist
proplist
```

SQLite 可能涉及：

```text
hotupdate.db
hotupdate.db-journal
hotupdate.db-wal
hotupdate.db-shm
```

这些文件都需要正确：

```text
owner
mode
SELinux label
```

否则普通进程可能读失败。

---

## 6.2 与 0444 冲突

SQLite 数据库在某些模式下即使读也可能需要锁文件或辅助文件。

如果全部设为：

```text
0444
```

要非常小心打开方式和 journal 模式。

---

## 6.3 SELinux 规则变复杂

你不仅要允许：

```te
open read getattr map
```

还可能需要允许访问：

```text
db-wal
db-shm
db-journal
```

如果 reader 需要打开目录或辅助文件，还需要更宽的目录权限。

写入者还需要：

```te
create write append rename unlink setattr lock
```

---

## 6.4 数据库损坏风险

SQLite 很可靠，但不是没有损坏风险。

风险来源：

- 断电
- 存储异常
- 错误使用 `immutable=1`
- 错误复制数据库文件
- 多进程不正确访问
- journal 文件权限异常
- 强行删除 wal/shm 文件

虽然 SQLite 的事务能力通常比手写文件更可靠，但错误配置会造成复杂问题。

---

## 6.5 依赖更重

你需要引入：

```text
libsqlite
```

相比明文文件方案，依赖更复杂。

---

## 6.6 初始化和迁移复杂

你需要维护：

```text
schema version
数据库升级
表结构迁移
索引
异常恢复
```

例如：

```sql
PRAGMA user_version;
```

这对小清单文件来说可能过度设计。

---

## 6.7 调试便利性下降

明文：

```sh
cat /data/hotupdate/filelist
```

SQLite：

```sh
sqlite3 /data/hotupdate/hotupdate.db \
    "select filename, filepath from hotupdate_files;"
```

在 user build 上可能没有 `sqlite3` 命令。

---

# 7. SQLite 什么时候值得用？

如果满足下面几个条件，可以考虑 SQLite：

1. 记录数量可能很大，例如几万条以上
2. 需要频繁查重
3. 需要复杂查询
4. 需要删除、更新、状态字段
5. 需要事务一致性
6. 需要记录时间、版本、来源、状态
7. 不强制要求 `cat` 直接可读
8. 可以接受更复杂的 SELinux 和权限设计

---

# 8. 你的场景是否适合 SQLite？

你的当前需求是：

```text
记录更新文件名和路径
记录更新属性名和 prop 路径
读接口返回文件名列表或属性名列表
文件要求人类可读明文
文件要 0444 任意进程可读
```

这几个条件更偏向：

```text
明文文件方案
```

而不是 SQLite。

尤其是：

```text
人类可读明文
任意进程 0444 读取
```

这两个要求和 SQLite 不太匹配。

---

# 9. 明文文件也可以很好解决查重

你可以用：

```text
TSV 明文 + 加锁 + 全量读 + 去重 + 原子重写
```

它可以做到：

- 文件内容明文
- 每行唯一
- 坏行自动清理
- 文件头固定
- 不产生额外 journal/wal 文件
- SELinux 简单
- 0444 读权限清晰
- `cat` 可直接调试

---

# 10. 推荐最终方案：不用 SQLite

对于你当前需求，我建议使用：

```text
明文 TSV 文件
```

并将写入逻辑升级为：

```text
flock LOCK_EX
读取全部记录
放入 set 去重
插入新记录
写 tmp 文件
fsync tmp
rename tmp -> 正式文件
fsync 目录
chmod 0444
```

这已经能解决：

```text
查重
唯一性
崩溃恢复
明文调试
任意进程只读
```

而且比 SQLite 的权限模型更简单。

---

# 11. 如果仍然使用 SQLite，推荐架构

如果你未来确实要用 SQLite，我建议不要让任意进程直接读 SQLite 数据库，而是：

```text
hotupdate_service 管理 SQLite
其他进程通过 Binder/AIDL 访问
```

这样：

- SQLite 文件不需要 0444
- 只有 hotupdate_service 能读写数据库
- SELinux 更安全
- app 不直接接触数据库文件
- 可以统一鉴权
- 可以避免 WAL/SHM 权限问题

但这改变了你的当前需求，因为你现在希望 lib 直接读文件。

---

# 12. SQLite 方案示例

如果仅作参考，数据库表可以设计为：

```sql
CREATE TABLE IF NOT EXISTS hotupdate_files (
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(filename, filepath)
);

CREATE TABLE IF NOT EXISTS hotupdate_props (
    propname TEXT NOT NULL,
    proppath TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(propname, proppath)
);
```

写入：

```sql
INSERT OR IGNORE INTO hotupdate_files(filename, filepath, created_at)
VALUES (?, ?, ?);
```

读取：

```sql
SELECT filename FROM hotupdate_files ORDER BY filename;
```

属性：

```sql
SELECT propname FROM hotupdate_props ORDER BY propname;
```

---

# 13. 简单对比

| 项目 | 明文 TSV + 原子重写 | SQLite |
|---|---|---|
| 查重 | 可以，通过 set | **天然支持 UNIQUE** |
| 并发 | 需要 flock | **内建事务/锁** |
| 小数据读取 | **很快** | 不一定更快 |
| 大数据查询 | 一般 | **更好** |
| 人类可读 | **cat 直接看** | 不可直接看 |
| 0444 任意读 | **简单** | 复杂 |
| SELinux | **简单** | 更复杂 |
| 辅助文件 | 无 | 可能有 wal/shm/journal |
| 崩溃恢复 | 原子 rename 可保证 | 事务可保证 |
| 依赖 | 少 | 多 |
| 迁移 | 简单 | 需要 schema 管理 |
| 适合当前需求 | **更适合** | 偏重 |

---

# 14. 最终结论

SQLite 的答案是：

```text
能解决查重；
复杂查询和大量数据时效率更好；
但对你当前需求不一定更高效；
还会带来权限、SELinux、WAL/journal、0444只读、调试不直观等风险。
```

我建议你的最终方案仍然选：

```text
明文 TSV + 文件锁 + 去重 + 原子重写
```

这比 SQLite 更符合你现在的核心要求：

```text
人类可读
任意进程可读
SELinux 简单
记录量小
接口简单
系统可靠
```

如果后续业务发展到需要复杂查询、删除、状态管理、上万条记录，再考虑升级到：

```text
hotupdate_service + SQLite + Binder API
```