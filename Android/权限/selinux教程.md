下面是一份面向 **Android 12 系统开发新手** 的 SELinux 入门教程，重点覆盖：

- Android SELinux 是什么
- 进程 / 文件 / 属性如何打标签
- `.te` 文件怎么写
- 常见规则语法
- 如何给一个新进程加 SELinux 域
- 系统进程相比普通进程有哪些典型权限
- Android 12 上常见调试方法

---

# 1. Android SELinux 是什么？

SELinux，全称 **Security-Enhanced Linux**，是一套 Linux 强制访问控制机制，简称 **MAC**。

传统 Linux 权限主要依赖：

```text
用户 UID
用户组 GID
文件 rwx 权限
capability
```

而 SELinux 会在这些权限之外，再增加一层安全检查。

也就是说：

> 即使一个进程是 root，如果 SELinux 不允许，它也不能访问某些文件、设备、socket、binder 服务等。

---

# 2. Android SELinux 的核心概念

Android 中 SELinux 最重要的几个概念是：

| 概念 | 说明 |
|---|---|
| domain | 进程的 SELinux 标签 |
| type | 文件、设备、socket、属性等对象的 SELinux 标签 |
| context | 完整 SELinux 上下文 |
| allow 规则 | 允许某个 domain 访问某个 type |
| neverallow 规则 | 永远禁止的规则 |
| permissive | 只打印 SELinux 拒绝日志，不真正拦截 |
| enforcing | 真正执行 SELinux 拦截 |

---

# 3. SELinux Context 长什么样？

Android 中常见 context 格式如下：

```text
u:r:system_server:s0
u:object_r:system_file:s0
u:object_r:vendor_file:s0
u:r:init:s0
```

它通常由 4 部分组成：

```text
user:role:type:level
```

例如：

```text
u:r:system_server:s0
```

含义是：

| 字段 | 示例 | 说明 |
|---|---|---|
| user | u | SELinux user，Android 基本固定为 u |
| role | r | 进程一般是 r |
| type | system_server | 最重要，表示进程 domain |
| level | s0 | MLS 等级，Android 常见为 s0 |

对于文件：

```text
u:object_r:system_file:s0
```

其中最重要的是：

```text
system_file
```

它表示文件 type。

---

# 4. Android 中哪些东西会有 SELinux 标签？

Android SELinux 会给很多对象加标签，包括：

## 4.1 进程

查看进程标签：

```bash
ps -AZ
```

示例：

```text
u:r:init:s0                root     1     0 init
u:r:system_server:s0       system   1234  567 zygote64
u:r:surfaceflinger:s0      system   888   1 surfaceflinger
u:r:untrusted_app:s0       u0_a123  2345  567 com.example.app
```

其中：

```text
u:r:system_server:s0
```

就是 system_server 的 SELinux domain。

---

## 4.2 文件

查看文件标签：

```bash
ls -Z /system/bin
ls -Z /vendor/bin
ls -Z /dev
```

示例：

```text
u:object_r:system_file:s0 /system/bin/app_process64
u:object_r:surfaceflinger_exec:s0 /system/bin/surfaceflinger
u:object_r:vendor_file:s0 /vendor/bin/hw/android.hardware.camera.provider@2.4-service
```

---

## 4.3 属性

Android property 也有 SELinux 标签。

相关文件通常有：

```text
system/sepolicy/private/property_contexts
system/sepolicy/public/property_contexts
vendor/.../property_contexts
```

示例：

```text
persist.sys.timezone     u:object_r:system_prop:s0
ro.product.              u:object_r:exported_default_prop:s0
vendor.camera.           u:object_r:vendor_camera_prop:s0
```

---

## 4.4 Binder 服务

Android 服务也会有 SELinux 类型，比如：

```text
system_server_service
surfaceflinger_service
audioserver_service
hal_camera_service
```

相关文件：

```text
service_contexts
hwservice_contexts
vndservice_contexts
```

---

# 5. Android SELinux 策略文件在哪里？

Android 12 中，AOSP 里主要路径如下：

```text
system/sepolicy/
```

常见目录：

```text
system/sepolicy/public/
system/sepolicy/private/
system/sepolicy/vendor/
system/sepolicy/prebuilts/
```

设备相关策略通常在：

```text
device/<vendor>/<device>/sepolicy/
vendor/<vendor>/<device>/sepolicy/
```

常见文件：

| 文件 | 作用 |
|---|---|
| `.te` | 定义 domain/type 以及 allow 规则 |
| `file_contexts` | 给文件路径打标签 |
| `property_contexts` | 给属性打标签 |
| `service_contexts` | 给 Binder service 打标签 |
| `hwservice_contexts` | 给 HAL service 打标签 |
| `genfs_contexts` | 给 proc/sysfs 等伪文件系统打标签 |
| `seapp_contexts` | 给 Android App 打标签 |
| `mac_permissions.xml` | 根据签名/包名分配 seinfo |

---

# 6. `.te` 文件是什么？

`.te` 是 SELinux Type Enforcement 文件，主要用于：

1. 定义一个进程 domain
2. 定义文件 type
3. 写 allow 访问规则
4. 使用宏简化策略
5. 定义 domain transition

例如：

```te
type mydaemon, domain;
type mydaemon_exec, exec_type, file_type, system_file_type;

init_daemon_domain(mydaemon)

allow mydaemon system_file:file read;
```

---

# 7. SELinux 规则基本语法

## 7.1 allow 规则

基本格式：

```te
allow 源domain 目标type:对象类别 权限集合;
```

示例：

```te
allow mydaemon my_data_file:file { read write open getattr };
```

含义：

```text
允许 mydaemon 进程访问 my_data_file 类型的 file 对象，
权限包括 read、write、open、getattr。
```

---

## 7.2 常见对象类别

| 类别 | 说明 |
|---|---|
| file | 普通文件 |
| dir | 目录 |
| lnk_file | 符号链接 |
| chr_file | 字符设备 |
| blk_file | 块设备 |
| sock_file | socket 文件 |
| unix_stream_socket | Unix stream socket |
| unix_dgram_socket | Unix datagram socket |
| tcp_socket | TCP socket |
| udp_socket | UDP socket |
| binder | Binder 调用 |
| service_manager | Binder service manager |
| property_service | Android property service |
| process | 进程操作 |
| filesystem | 文件系统 |
| capability | Linux capability |

---

## 7.3 常见文件权限

```te
read
write
open
getattr
setattr
create
unlink
rename
append
map
execute
execute_no_trans
```

常用组合：

```te
allow mydaemon my_file:file { open read getattr };
allow mydaemon my_file:file { open read write getattr };
allow mydaemon my_file:file { create open read write getattr setattr unlink };
```

---

## 7.4 常见目录权限

```te
search
read
write
open
getattr
add_name
remove_name
create
rmdir
```

示例：

```te
allow mydaemon my_data_dir:dir { search read open getattr };
allow mydaemon my_data_dir:dir { search write add_name remove_name };
```

如果要在目录里创建文件，通常需要：

```te
allow mydaemon my_data_dir:dir { search write add_name };
allow mydaemon my_data_file:file { create open read write getattr setattr };
```

---

## 7.5 常见 Binder 权限

```te
binder_call(client, server)
binder_use(domain)
```

示例：

```te
binder_use(mydaemon)
binder_call(mydaemon, system_server)
```

如果访问 service_manager 中的服务，还常见：

```te
allow mydaemon activity_service:service_manager find;
```

---

## 7.6 常见 property 权限

读取属性：

```te
get_prop(mydaemon, system_prop)
```

设置属性：

```te
set_prop(mydaemon, my_prop)
```

示例：

```te
get_prop(mydaemon, vendor_camera_prop)
set_prop(mydaemon, vendor_camera_prop)
```

同时还需要在 `property_contexts` 中定义属性类型。

---

# 8. 如何给进程加 SELinux 标签？

这是 Android SELinux 开发中最常见的问题。

## 场景：你新增了一个 native daemon

假设你有一个新进程：

```text
/system/bin/mydaemon
```

你希望它运行时标签为：

```text
u:r:mydaemon:s0
```

文件标签为：

```text
u:object_r:mydaemon_exec:s0
```

---

## 8.1 第一步：写 init rc

例如：

```rc
service mydaemon /system/bin/mydaemon
    class main
    user system
    group system
    oneshot
```

如果它由 init 启动，SELinux domain transition 通常由 `init_daemon_domain()` 宏完成。

---

## 8.2 第二步：写 `file_contexts`

给可执行文件打标签：

```text
/system/bin/mydaemon    u:object_r:mydaemon_exec:s0
```

如果在 vendor 分区：

```text
/vendor/bin/mydaemon    u:object_r:mydaemon_exec:s0
```

---

## 8.3 第三步：写 `.te`

新建：

```text
mydaemon.te
```

内容：

```te
type mydaemon, domain;
type mydaemon_exec, exec_type, file_type, system_file_type;

init_daemon_domain(mydaemon)
```

这几行非常关键。

含义：

```te
type mydaemon, domain;
```

定义一个进程 domain。

```te
type mydaemon_exec, exec_type, file_type, system_file_type;
```

定义可执行文件类型。

```te
init_daemon_domain(mydaemon)
```

表示：

> 当 init 执行带有 `mydaemon_exec` 标签的文件时，进程切换到 `mydaemon` domain。

---

## 8.4 第四步：编译刷机后验证

查看文件标签：

```bash
adb shell ls -Z /system/bin/mydaemon
```

期望：

```text
u:object_r:mydaemon_exec:s0 /system/bin/mydaemon
```

查看进程标签：

```bash
adb shell ps -AZ | grep mydaemon
```

期望：

```text
u:r:mydaemon:s0 system ... mydaemon
```

---

# 9. 如果进程没有切到正确 domain 怎么办？

常见原因如下。

## 9.1 `file_contexts` 没匹配

检查：

```bash
adb shell ls -Z /system/bin/mydaemon
```

如果看到：

```text
u:object_r:system_file:s0
```

而不是：

```text
u:object_r:mydaemon_exec:s0
```

说明 `file_contexts` 没生效。

可能原因：

- 路径写错
- 正则没匹配
- 文件在 vendor，但策略写到 system
- 没重新编译 vendor/system image
- 被更靠前或更具体的规则覆盖

---

## 9.2 `.te` 中没有定义 exec type

需要类似：

```te
type mydaemon_exec, exec_type, file_type, system_file_type;
```

vendor 进程一般更可能是：

```te
type mydaemon_exec, exec_type, vendor_file_type, file_type;
```

---

## 9.3 没有 domain transition

如果是 init 启动，通常要：

```te
init_daemon_domain(mydaemon)
```

如果是别的进程启动，需要自己写 transition，例如：

```te
domain_auto_trans(parent_domain, mydaemon_exec, mydaemon)
```

---

# 10. system 分区进程和 vendor 分区进程区别

Android Treble 后，SELinux 策略分区更严格。

一般来说：

## system 进程

通常位于：

```text
/system/bin
/system_ext/bin
/product/bin
```

可能使用：

```te
system_file_type
```

例如：

```te
type mydaemon_exec, exec_type, file_type, system_file_type;
```

---

## vendor 进程

通常位于：

```text
/vendor/bin
/vendor/bin/hw
/odm/bin
```

应使用：

```te
vendor_file_type
```

例如：

```te
type vendor_mydaemon, domain;
type vendor_mydaemon_exec, exec_type, vendor_file_type, file_type;

init_daemon_domain(vendor_mydaemon)
```

`file_contexts`：

```text
/vendor/bin/vendor_mydaemon    u:object_r:vendor_mydaemon_exec:s0
```

---

# 11. App 进程如何打标签？

普通 Android App 的 SELinux domain 通常不是你在 `.te` 里给每个包单独定义的。

常见 App domain：

```text
untrusted_app
priv_app
platform_app
system_app
isolated_app
shell
```

查看：

```bash
adb shell ps -AZ | grep com.example
```

示例：

```text
u:r:untrusted_app:s0:c123,c456 u0_a123 ... com.example.demo
```

App 的标签由以下内容共同决定：

1. APK 安装位置
2. APK 签名
3. `priv-app` / `app`
4. `seinfo`
5. `seapp_contexts`
6. `mac_permissions.xml`

---

## 11.1 普通三方 App

通常是：

```text
u:r:untrusted_app:s0:cXX,cYY
```

---

## 11.2 priv-app

如果放在：

```text
/system/priv-app/
```

并满足权限白名单等条件，可能是：

```text
u:r:priv_app:s0
```

---

## 11.3 platform 签名 App

平台签名 App 可能是：

```text
u:r:platform_app:s0
```

---

## 11.4 system_app

某些系统 App 可能匹配到：

```text
u:r:system_app:s0
```

---

# 12. `seapp_contexts` 示例

示例：

```text
user=system seinfo=platform name=com.example.myapp domain=system_app type=system_app_data_file
```

含义：

```text
当 app 满足：
user=system
seinfo=platform
包名 com.example.myapp

则进程 domain 是 system_app，
数据目录 type 是 system_app_data_file。
```

不过新手不建议随便改 `seapp_contexts`，因为很容易触发 `neverallow`。

---

# 13. 常用宏介绍

Android SELinux 大量使用宏。宏通常定义在：

```text
system/sepolicy/public/te_macros
system/sepolicy/private/te_macros
```

常见宏如下。

---

## 13.1 `init_daemon_domain`

```te
init_daemon_domain(mydaemon)
```

用于 init 启动的 daemon。

相当于帮你做：

- 允许 init 执行对应 exec 文件
- 建立从 init 到 mydaemon 的 domain transition
- 设置基本进程权限

---

## 13.2 `domain_auto_trans`

```te
domain_auto_trans(init, mydaemon_exec, mydaemon)
```

表示：

```text
当 init 执行 mydaemon_exec 文件时，
自动切换到 mydaemon domain。
```

---

## 13.3 `binder_use`

```te
binder_use(mydaemon)
```

允许 domain 使用 binder 基础能力。

---

## 13.4 `binder_call`

```te
binder_call(mydaemon, system_server)
```

允许：

```text
mydaemon 调用 system_server 的 binder 接口。
```

---

## 13.5 `get_prop`

```te
get_prop(mydaemon, system_prop)
```

允许读取某类 property。

---

## 13.6 `set_prop`

```te
set_prop(mydaemon, my_prop)
```

允许设置某类 property。

---

## 13.7 `r_dir_file`

```te
r_dir_file(mydaemon, my_data_file)
```

允许读取某个目录/文件类型。

---

## 13.8 `rw_file_perms`

常见权限集合：

```te
allow mydaemon my_file:file rw_file_perms;
```

类似于：

```te
{ open getattr read write append ioctl lock map }
```

具体以源码宏定义为准。

---

# 14. 如何写一个完整示例？

下面给一个比较完整的 native daemon 示例。

---

## 14.1 目标

进程：

```text
/system/bin/mydaemon
```

运行 domain：

```text
u:r:mydaemon:s0
```

可执行文件 type：

```text
u:object_r:mydaemon_exec:s0
```

数据目录：

```text
/data/vendor/mydaemon
```

数据文件 type：

```text
u:object_r:mydaemon_data_file:s0
```

---

## 14.2 `init.mydaemon.rc`

```rc
service mydaemon /system/bin/mydaemon
    class main
    user system
    group system
    oneshot
```

---

## 14.3 `file_contexts`

```text
/system/bin/mydaemon          u:object_r:mydaemon_exec:s0
/data/vendor/mydaemon(/.*)?   u:object_r:mydaemon_data_file:s0
```

---

## 14.4 `mydaemon.te`

```te
type mydaemon, domain;
type mydaemon_exec, exec_type, file_type, system_file_type;

type mydaemon_data_file, file_type, data_file_type;

init_daemon_domain(mydaemon)

allow mydaemon mydaemon_data_file:dir {
    create
    read
    write
    open
    getattr
    setattr
    search
    add_name
    remove_name
};

allow mydaemon mydaemon_data_file:file {
    create
    read
    write
    open
    getattr
    setattr
    unlink
    rename
    map
};
```

---

## 14.5 更推荐用宏简化

```te
type mydaemon, domain;
type mydaemon_exec, exec_type, file_type, system_file_type;

type mydaemon_data_file, file_type, data_file_type;

init_daemon_domain(mydaemon)

allow mydaemon mydaemon_data_file:dir create_dir_perms;
allow mydaemon mydaemon_data_file:file create_file_perms;
```

---

# 15. 给进程访问设备节点权限

假设设备节点：

```text
/dev/mydevice
```

---

## 15.1 `file_contexts`

```text
/dev/mydevice    u:object_r:mydevice_device:s0
```

---

## 15.2 `.te`

```te
type mydevice_device, dev_type;

allow mydaemon mydevice_device:chr_file rw_file_perms;
```

如果是字符设备，一般是：

```te
chr_file
```

如果是块设备，一般是：

```te
blk_file
```

---

# 16. 访问 sysfs 节点

例如：

```text
/sys/devices/platform/my_node
```

不要直接给所有 sysfs 权限：

```te
allow mydaemon sysfs:file rw_file_perms;
```

这通常不推荐，甚至可能被 `neverallow` 禁止。

推荐新建专用 type。

---

## 16.1 `genfs_contexts`

```text
genfscon sysfs /devices/platform/my_node u:object_r:sysfs_my_node:s0
```

---

## 16.2 `.te`

```te
type sysfs_my_node, fs_type, sysfs_type;

allow mydaemon sysfs_my_node:file rw_file_perms;
allow mydaemon sysfs_my_node:dir search;
```

---

# 17. 访问 proc 节点

类似 sysfs，建议使用专用 type。

## 17.1 `genfs_contexts`

```text
genfscon proc /my_node u:object_r:proc_my_node:s0
```

---

## 17.2 `.te`

```te
type proc_my_node, fs_type, proc_type;

allow mydaemon proc_my_node:file rw_file_perms;
```

---

# 18. 设置 Android property

假设你想让 mydaemon 设置属性：

```text
vendor.mydaemon.status
```

---

## 18.1 `property_contexts`

```text
vendor.mydaemon.    u:object_r:vendor_mydaemon_prop:s0
```

---

## 18.2 `.te`

```te
type vendor_mydaemon_prop, property_type;

set_prop(mydaemon, vendor_mydaemon_prop)
get_prop(mydaemon, vendor_mydaemon_prop)
```

Android 12 上 vendor 属性通常建议以：

```text
vendor.
persist.vendor.
ro.vendor.
```

开头。

---

# 19. Binder 服务相关权限

假设你的进程需要访问 system_server 中的某个服务，比如 activity service。

通常需要：

```te
binder_use(mydaemon)
binder_call(mydaemon, system_server)

allow mydaemon activity_service:service_manager find;
```

含义：

1. 允许 mydaemon 使用 Binder
2. 允许 mydaemon 调用 system_server
3. 允许 mydaemon 从 service_manager 查找 activity_service

---

# 20. 注册 Binder 服务

如果 mydaemon 自己要注册 Binder service，比如：

```text
mydaemon
```

---

## 20.1 `service_contexts`

```text
mydaemon    u:object_r:mydaemon_service:s0
```

---

## 20.2 `.te`

```te
type mydaemon_service, service_manager_type;

allow mydaemon mydaemon_service:service_manager add;
allow system_server mydaemon_service:service_manager find;

binder_use(mydaemon)
binder_call(system_server, mydaemon)
```

---

# 21. HAL 服务相关

Android 12 中 HAL 通常涉及：

```text
hwservice_contexts
vintf
hal_server_domain
hal_client_domain
```

例如自定义 HAL：

```te
type hal_myhal_default, domain;
type hal_myhal_default_exec, exec_type, vendor_file_type, file_type;

init_daemon_domain(hal_myhal_default)

hal_server_domain(hal_myhal_default, hal_myhal)
```

客户端：

```te
hal_client_domain(system_server, hal_myhal)
```

`hwservice_contexts`：

```text
vendor.example.myhal::IMyHal/default    u:object_r:hal_myhal_hwservice:s0
```

---

# 22. 如何根据 avc denied 写规则？

当 SELinux 拒绝访问时，logcat 或 dmesg 中会出现：

```text
avc: denied { read write } for pid=1234 comm="mydaemon" name="xxx"
scontext=u:r:mydaemon:s0
tcontext=u:object_r:my_file:s0
tclass=file
```

重点看 4 个字段：

| 字段 | 含义 |
|---|---|
| scontext | 谁访问 |
| tcontext | 被访问对象 |
| tclass | 对象类别 |
| denied 权限 | 被拒绝的权限 |

对应规则：

```te
allow mydaemon my_file:file { read write };
```

---

## 22.1 示例

日志：

```text
avc: denied { search } for comm="mydaemon" name="vendor"
scontext=u:r:mydaemon:s0
tcontext=u:object_r:vendor_data_file:s0
tclass=dir
```

可写：

```te
allow mydaemon vendor_data_file:dir search;
```

但不要看到 denied 就无脑加规则，要先判断：

> 它真的应该访问这个对象吗？

---

# 23. 使用 audit2allow 要小心

可以用：

```bash
audit2allow
```

根据 denied 日志生成 allow 规则。

但新手要注意：

> audit2allow 生成的规则只能作为参考，不能直接全部复制。

原因：

1. 可能权限过大
2. 可能违反 Android neverallow
3. 可能掩盖代码设计问题
4. 可能不符合 Treble 分区策略

---

# 24. permissive 和 enforcing

查看 SELinux 状态：

```bash
adb shell getenforce
```

结果：

```text
Enforcing
```

或：

```text
Permissive
```

临时切 permissive：

```bash
adb shell setenforce 0
```

临时切 enforcing：

```bash
adb shell setenforce 1
```

但在 user 版本上通常不能这么做。

---

## 24.1 让单个 domain permissive

开发阶段可以：

```te
permissive mydaemon;
```

这表示：

```text
mydaemon 的 SELinux 拒绝只打印日志，不真正拦截。
```

但正式版本不要保留。

---

# 25. neverallow 是什么？

`neverallow` 是 SELinux 中的硬性禁止规则。

例如：

```te
neverallow untrusted_app shell_data_file:file write;
```

含义：

```text
永远不允许 untrusted_app 写 shell_data_file 类型文件。
```

如果你写了违反 neverallow 的 allow 规则，编译会失败。

---

# 26. 为什么普通 App 权限很少？

普通 App 通常运行在：

```text
untrusted_app
```

它受到很多限制，例如：

- 不能直接访问大部分 `/dev` 节点
- 不能直接访问其他 App 数据目录
- 不能直接访问很多 system/vendor 私有文件
- 不能设置大多数系统属性
- 不能注册核心 Binder 服务
- 不能访问很多 HAL service
- 不能 ptrace 系统进程
- 不能加载内核模块
- 不能 mount 文件系统
- 不能访问大量 proc/sysfs 节点

即使 App 申请了 Android permission，也不代表 SELinux 一定允许。

---

# 27. 系统进程比普通进程有哪些权限？

你问的“系统进程有哪些普通进程没有的权限”，可以从几个角度理解。

---

## 27.1 system_server

`system_server` 是 Android framework 的核心进程，domain 通常是：

```text
u:r:system_server:s0
```

它通常拥有普通 App 没有的能力：

| 能力 | 说明 |
|---|---|
| 管理 Activity/Service/Broadcast | AMS |
| 管理 Package | PMS |
| 管理 Window | WMS |
| 管理 Power | PowerManagerService |
| 管理 Input | InputManagerService |
| 访问大量 system property | 读取/设置部分系统属性 |
| 查找和调用大量 Binder/HAL 服务 | 通过 service_manager/hwservicemanager |
| 管理 App 进程 | 与 zygote、ActivityManager 配合 |
| 访问部分 `/data/system` 文件 | 系统配置、packages、settings 等 |
| 访问 keystore、stats、netd 等服务 | 系统管理功能 |
| 控制部分设备能力 | 间接通过 HAL/service |

但它也不是无限权限，很多底层设备节点仍不应直接访问。

---

## 27.2 init

`init` 是 1 号进程，domain：

```text
u:r:init:s0
```

它有很多特殊能力：

| 能力 | 说明 |
|---|---|
| 启动 native daemon | 通过 init.rc |
| 执行 domain transition | 启动不同 SELinux domain |
| 创建目录/节点 | 根据 rc 脚本 |
| 设置部分属性 | property service |
| mount 文件系统 | early init 阶段 |
| 管理服务生命周期 | start/stop/restart |
| 处理 uevent | 创建设备节点 |

普通进程一般没有这些权限。

---

## 27.3 vold

`vold` 负责存储管理，通常有：

- mount/unmount 文件系统
- 管理外部存储
- 访问块设备
- 处理加密存储

普通 App 不能直接 mount，也不能直接访问块设备。

---

## 27.4 netd

`netd` 负责网络管理，通常有：

- 配置 iptables / nftables
- 管理网络接口
- 配置 DNS
- 管理 tethering
- 部分 netlink 操作

普通 App 只能通过 framework API 间接请求网络功能。

---

## 27.5 servicemanager / hwservicemanager

它们负责 Binder 服务注册和查找：

- `servicemanager` 管理 framework Binder service
- `hwservicemanager` 管理 HIDL HAL service

普通 App 不能随意注册系统服务。

---

## 27.6 hal_xxx 进程

HAL 进程通常有硬件访问权限，比如：

```text
hal_camera_default
hal_audio_default
hal_bluetooth_default
hal_graphics_composer_default
```

这些进程可能访问：

- `/dev/video*`
- `/dev/snd/*`
- `/dev/binder`
- `/dev/hwbinder`
- sysfs 节点
- vendor 私有节点

普通 App 不能直接访问硬件设备节点，只能通过 framework/HAL 间接访问。

---

# 28. 不同进程权限差异示例

## 普通 App

```text
u:r:untrusted_app:s0
```

通常只能：

- 访问自己的 `/data/data/<package>`
- 使用被允许的 Binder 服务
- 访问部分公共系统资源
- 使用 Android permission 授权后的 framework API

---

## system_app

```text
u:r:system_app:s0
```

相比普通 App 可能多一些：

- 访问更多系统 Binder service
- 使用部分系统 API
- 读取部分系统属性
- 访问 system app 自己的数据
- 享受 platform 签名权限

但仍明显弱于 `system_server`。

---

## priv_app

```text
u:r:priv_app:s0
```

相比普通 App 可能多一些：

- privileged permissions
- 更多 framework 服务访问能力
- 某些受限 API 能力

但仍不能随便访问 `/dev` 或 `/data/system`。

---

## system_server

```text
u:r:system_server:s0
```

拥有大量 framework 管理权限，但受 SELinux 限制。

---

## init

```text
u:r:init:s0
```

系统启动和服务管理核心。

---

# 29. 新手写 SELinux 规则的基本原则

## 原则 1：最小权限

不要这样写：

```te
allow mydaemon system_file:file *;
allow mydaemon device:chr_file *;
allow mydaemon self:capability *;
```

应该只允许必要权限：

```te
allow mydaemon mydevice_device:chr_file rw_file_perms;
```

---

## 原则 2：给对象单独打标签

不要让你的进程访问大而泛的类型：

```te
allow mydaemon sysfs:file write;
```

更推荐：

```te
type sysfs_mydaemon, fs_type, sysfs_type;
allow mydaemon sysfs_mydaemon:file write;
```

---

## 原则 3：不要绕过架构

例如普通 App 想直接访问 camera device：

```text
/dev/video0
```

不推荐直接给 App 权限。

正确架构：

```text
App -> Camera Framework -> CameraService -> Camera HAL -> Kernel Driver
```

---

## 原则 4：不要长期使用 permissive

开发阶段可以：

```te
permissive mydaemon;
```

量产必须移除。

---

## 原则 5：不要盲目相信 audit2allow

`audit2allow` 是参考工具，不是设计工具。

---

# 30. 常见错误和解决方法

## 30.1 编译报 neverallow

错误示例：

```text
neverallow check failed
```

说明你加的 allow 违反系统安全规则。

解决思路：

1. 不要强行绕过 neverallow
2. 检查进程是否放错分区
3. 检查 domain 是否应该访问目标对象
4. 使用已有 HAL/framework 通道
5. 新建专用 type，而不是访问泛类型

---

## 30.2 运行时报 avc denied

看日志：

```bash
adb logcat -b all | grep avc
adb shell dmesg | grep avc
```

根据：

```text
scontext
tcontext
tclass
denied permission
```

判断规则。

---

## 30.3 文件标签不对

执行：

```bash
adb shell restorecon -RF /path
adb shell ls -Z /path
```

如果是只读分区，需要重新打包镜像。

---

## 30.4 新规则没生效

检查：

- 是否编进对应 policy
- 是否写在正确目录
- 是否刷了对应分区
- 是否设备使用 split policy
- 是否被 vendor/system 分区边界限制
- 是否重启

---

# 31. Android 12 常用调试命令

查看 SELinux 状态：

```bash
adb shell getenforce
```

查看进程标签：

```bash
adb shell ps -AZ
```

查看文件标签：

```bash
adb shell ls -Z /path
```

查看 avc denied：

```bash
adb logcat -b all | grep -i "avc: denied"
adb shell dmesg | grep -i "avc: denied"
```

临时 permissive：

```bash
adb shell setenforce 0
```

恢复 enforcing：

```bash
adb shell setenforce 1
```

重新恢复文件 context：

```bash
adb shell restorecon -RF /path
```

查看某个进程：

```bash
adb shell ps -AZ | grep mydaemon
```

---

# 32. 一个最小可用模板

如果你只是想快速给一个 init 启动的进程加标签，可以参考这个模板。

## 32.1 假设进程路径

```text
/vendor/bin/mydaemon
```

---

## 32.2 `file_contexts`

```text
/vendor/bin/mydaemon    u:object_r:mydaemon_exec:s0
```

---

## 32.3 `mydaemon.te`

```te
type mydaemon, domain;
type mydaemon_exec, exec_type, vendor_file_type, file_type;

init_daemon_domain(mydaemon)
```

---

## 32.4 init rc

```rc
service mydaemon /vendor/bin/mydaemon
    class main
    user system
    group system
    oneshot
```

---

## 32.5 验证

```bash
adb shell ls -Z /vendor/bin/mydaemon
adb shell ps -AZ | grep mydaemon
```

期望看到：

```text
u:object_r:mydaemon_exec:s0 /vendor/bin/mydaemon
u:r:mydaemon:s0 ... mydaemon
```

---

# 33. 进阶：普通进程如何拥有更多权限？

不要简单理解为：

> 把普通进程改成 system_server 或 init 就能拥有权限。

这是错误且危险的。

正确做法是：

1. 给进程定义自己的 domain
2. 给它需要访问的资源定义专用 type
3. 只添加必要 allow 规则
4. 如果是硬件访问，走 HAL
5. 如果是 framework 能力，走 Binder service
6. 如果是 App，优先用 Android permission 和系统 API

---

# 34. 快速学习路线

建议你按这个顺序学习：

1. 会看 `ps -AZ`
2. 会看 `ls -Z`
3. 理解 `scontext`、`tcontext`、`tclass`
4. 能根据 avc denied 写简单 allow
5. 能给 init daemon 加 domain
6. 能给文件、设备、property 加 type
7. 学会使用宏
8. 理解 `neverallow`
9. 理解 system/vendor policy 分区
10. 理解 App domain 和 native daemon domain 的区别

---

# 35. 总结

Android SELinux 可以先记住这句话：

> **进程有 domain，资源有 type，allow 决定 domain 能不能访问 type。**

最常见开发流程是：

```text
1. 给可执行文件写 file_contexts
2. 在 .te 中定义 domain 和 exec type
3. 使用 init_daemon_domain 建立 domain transition
4. 根据 avc denied 最小化添加 allow
5. 避免违反 neverallow
6. 验证 ps -AZ 和 ls -Z
```

最小 daemon 示例：

```te
type mydaemon, domain;
type mydaemon_exec, exec_type, vendor_file_type, file_type;

init_daemon_domain(mydaemon)
```

`file_contexts`：

```text
/vendor/bin/mydaemon    u:object_r:mydaemon_exec:s0
```

验证：

```bash
adb shell ps -AZ | grep mydaemon
adb shell ls -Z /vendor/bin/mydaemon
```

如果你能熟练掌握这个流程，就已经具备 Android SELinux 系统开发的入门能力了。

