在 Android SELinux 里，`neverallow` 可以理解为：

> **一种“绝对不允许”的安全规则，用来禁止某些 SELinux 权限被授予。**

即使你在别的地方写了 `allow` 规则，只要违反了 `neverallow`，**编译阶段就会报错**，系统策略无法通过。

---

## 1. 先简单理解 SELinux 规则

Android 里的 SELinux 主要通过策略规则控制：

> **谁** 可以对 **什么对象** 做 **什么操作**

比如：

```te
allow system_app system_file:file read;
```

大概意思是：

> 允许 `system_app` 这个域读取 `system_file` 类型的文件。

结构可以理解为：

```te
allow 源类型 目标类型:对象类别 权限;
```

例如：

```te
allow appdomain system_file:file execute;
```

表示：

> 允许普通 App 域执行 `system_file` 类型的文件。

---

## 2. `neverallow` 是什么？

`neverallow` 的语法和 `allow` 很像：

```te
neverallow 源类型 目标类型:对象类别 权限;
```

但它的意思不是“授予权限”，而是：

> **禁止策略中出现任何匹配这个条件的 `allow` 规则。**

例如：

```te
neverallow appdomain system_file:file execute;
```

意思是：

> 绝不允许 `appdomain` 执行 `system_file` 类型的文件。

如果你又写了：

```te
allow appdomain system_file:file execute;
```

那么编译 SELinux policy 时就会失败。

---

## 3. `neverallow` 和 `allow` 的关系

可以这样理解：

| 规则 | 作用 |
|---|---|
| `allow` | 授权，允许某个域访问某个资源 |
| `neverallow` | 约束，禁止某类授权出现 |
| `dontaudit` | 不打印某些拒绝日志 |
| `auditallow` | 对某些允许行为也打印日志 |

`neverallow` 不是运行时才拒绝，而是**编译期检查**。

也就是说：

```te
neverallow foo bar:file write;
```

并不是系统运行时看到 `foo` 写 `bar` 文件才拒绝，而是：

> 如果整个 SELinux 策略里存在任何允许 `foo` 写 `bar:file` 的规则，编译时就失败。

---

## 4. 为什么 Android 要有 `neverallow`？

Android 系统里有很多安全边界。比如：

- 普通 App 不能访问系统核心文件
- 普通 App 不能直接访问 block device
- 普通 App 不能随意执行 vendor 分区文件
- 非特权进程不能修改 SELinux policy
- 非 init 进程不能随意切换安全上下文
- vendor 不能破坏 system 的安全约束

`neverallow` 的作用就是把这些安全边界写死。

它像一道“红线”：

> 你可以加 `allow` 解决功能问题，但不能越过系统安全红线。

---

## 5. 一个简单例子

假设有如下规则：

```te
neverallow appdomain device:blk_file { read write };
```

意思是：

> 所有普通 App 域都绝不能读写 block device。

如果某个开发者为了让 App 直接访问分区设备，加了：

```te
allow untrusted_app device:blk_file read;
```

由于 `untrusted_app` 属于 `appdomain`，这条 `allow` 会命中上面的 `neverallow`，编译会报错。

这时你不能简单地继续加强 `allow`，而应该思考：

- 这个访问方式是不是设计错了？
- 是否应该通过系统服务代理访问？
- 是否应该定义专门的 HAL？
- 是否应该把功能放到 native daemon 里？
- 是否应该走 Binder、AIDL、HIDL 等接口？

---

## 6. Android 编译时常见 neverallow 报错

你可能会看到类似错误：

```text
libsepol.report_failure: neverallow on line 123 of system/sepolicy/private/domain.te
violated by allow xxx yyy:file { read write };
```

大概意思是：

> 在某个 `.te` 文件第 123 行定义的 `neverallow` 被你某条 `allow` 规则违反了。

关键要看两部分：

### 第一部分：哪个 `neverallow` 被违反

比如：

```text
neverallow on line 123 of system/sepolicy/private/domain.te
```

说明要去看：

```text
system/sepolicy/private/domain.te
```

第 123 行附近。

### 第二部分：是哪条 `allow` 违反了它

比如：

```text
violated by allow my_daemon system_file:file execute;
```

说明你有规则允许了：

```te
allow my_daemon system_file:file execute;
```

而这被 Android 禁止。

---

## 7. `neverallow` 常见场景

### 7.1 禁止普通进程修改系统文件

例如概念上类似：

```te
neverallow domain system_file:file write;
```

含义是：

> 大多数进程不能写 system 分区上的文件。

注意真实 Android 策略通常更复杂，会有排除项。

---

### 7.2 禁止普通 App 访问设备节点

```te
neverallow appdomain device:chr_file { read write open };
```

含义是：

> 普通 App 不能直接访问设备节点。

正确做法通常是：

```text
App -> Framework/System Service -> HAL/Native Daemon -> Device Node
```

而不是：

```text
App -> /dev/xxx
```

---

### 7.3 禁止随意执行非授权文件

```te
neverallow domain unlabeled:file execute;
```

含义是：

> 任何域都不应该执行没有正确标记的文件。

如果你遇到这种问题，多半是文件 label 配错了，而不是应该加 allow。

---

### 7.4 禁止 vendor 访问 system 私有类型

Android Treble 之后，system 和 vendor sepolicy 有明确边界。

如果 vendor 侧策略直接访问 system 私有类型，可能触发 `neverallow` 或兼容性检查。

---

## 8. `neverallow` 的本质：防止“乱加 allow”

很多 SELinux 新手遇到 AVC denied 日志后，会习惯性加：

```te
allow xxx yyy:file { read write open };
```

但 Android 不希望开发者靠“补洞式 allow”解决所有问题。

因为有些 denied 是合理的，代表系统阻止了危险行为。

`neverallow` 就是为了防止这种情况：

> 即使你想加 allow，也不允许你突破安全模型。

---

## 9. 遇到 neverallow 报错该怎么办？

不要第一反应就是删 `neverallow`。

应该按下面顺序排查。

---

### 第一步：看违反的是哪条 `allow`

编译日志一般会告诉你：

```text
violated by allow xxx yyy:class perm;
```

你要找到是谁写出了这条 `allow`。

可能是你直接写的，也可能是宏展开出来的。

例如你写了：

```te
r_dir_file(my_domain, system_file)
```

宏展开后可能包含多条 `allow`。

---

### 第二步：看 `neverallow` 原文

找到报错中提到的文件和行号，比如：

```text
system/sepolicy/private/domain.te
```

看那条 `neverallow` 为什么禁止。

很多 Android 原生策略会在附近写注释，解释安全原因。

---

### 第三步：判断是不是 label 错了

非常常见。

比如你有一个自定义可执行文件：

```text
/vendor/bin/mydaemon
```

但它没有正确标记，结果变成了：

```text
u:object_r:system_file:s0
```

你又试图让某个 domain 执行它：

```te
allow my_domain system_file:file execute;
```

这就可能违反 `neverallow`。

正确做法可能是给文件定义自己的类型：

```te
type mydaemon_exec, exec_type, vendor_file_type, file_type;
```

然后在 `file_contexts` 中标记：

```text
/vendor/bin/mydaemon u:object_r:mydaemon_exec:s0
```

再通过 domain transition 启动。

---

### 第四步：考虑架构是否错误

如果你的需求是：

> App 直接访问 `/dev/my_device`

这通常不是 Android 推荐架构。

更推荐：

```text
App
  ↓ Binder/AIDL
System Service
  ↓ Binder/HIDL/AIDL
HAL or native daemon
  ↓
/dev/my_device
```

让高权限访问集中在受控服务里，而不是直接给 App 放权限。

---

### 第五步：不要随便删除 AOSP 的 `neverallow`

在产品开发中，有人会想：

```te
# 注释掉 neverallow
```

这通常不是好做法。

原因：

1. 可能破坏 Android 安全模型；
2. 可能导致 CTS/VTS 失败；
3. 可能影响系统升级兼容性；
4. 可能隐藏真实设计问题；
5. 可能让设备存在安全风险。

---

## 10. 一个具体例子：执行文件触发 neverallow

假设你有一个服务 `foo`，想执行 `/data/local/tmp/test.sh`。

你加了：

```te
allow foo shell_data_file:file execute;
```

结果触发 `neverallow`。

这是因为 Android 通常不允许普通域执行 data 分区上的随意文件。这样可以防止攻击者把恶意程序写到可写目录后执行。

正确方案通常是：

- 把可执行文件放到 `/system/bin`、`/vendor/bin` 等只读分区；
- 给它正确的 exec type；
- 通过 init 启动；
- 定义对应 domain；
- 不要执行 `/data` 下临时文件。

---

## 11. `neverallow` 里的集合和排除

Android sepolicy 里经常能看到比较复杂的写法：

```te
neverallow {
    domain
    -init
    -vold
} block_device:blk_file write;
```

意思是：

> 对 `domain` 集合里的所有类型，除了 `init` 和 `vold`，都不允许写 `block_device`。

其中：

```te
-domain
```

不是减号的意思，而是在 SELinux type set 里表示**排除某个类型**。

更准确地说：

```te
{
    domain
    -init
    -vold
}
```

表示：

```text
所有 domain 类型，排除 init 和 vold
```

---

## 12. `neverallow` 会不会影响运行时？

间接影响。

`neverallow` 本身不是运行时规则，而是编译期约束。

运行时真正决定是否允许访问的是：

- `allow`
- 类型标签
- class
- permission
- MLS/MCS 等约束

但是由于 `neverallow` 禁止某些 `allow` 出现在最终策略中，所以它间接保证运行时不可能出现这类访问授权。

---

## 13. `neverallow` 和 permissive 有什么关系？

SELinux 有两种常见模式：

| 模式 | 含义 |
|---|---|
| enforcing | 拒绝非法访问 |
| permissive | 只记录日志，不真正拒绝 |

但 `neverallow` 是**编译期检查**，和运行时 permissive/enforcing 不完全一样。

即使某个 domain 是 permissive，如果你写的 `allow` 违反了 `neverallow`，仍然可能编译失败。

---

## 14. 新手记忆方式

你可以这样记：

```text
allow      = 可以这样做
deny       = 默认没有 allow 就拒绝
neverallow = 连 allow 都不准写
```

SELinux 默认是白名单模型：

> 没有 `allow` 就不允许。

而 `neverallow` 是更强的限制：

> 某些权限就算你想加白名单，也不准加。

---

## 15. 实战建议

遇到 neverallow，不要问：

> 我怎么绕过它？

而应该问：

> Android 为什么禁止这个访问？  
> 我的文件 label 是否正确？  
> 我的进程 domain 是否正确？  
> 这个功能是否应该通过系统服务或 HAL 间接实现？  
> 是否把文件放错了分区？  
> 是否用了过大的权限宏？  

---

## 16. 总结

`neverallow` 是 Android SELinux 中的**安全红线规则**。

它的核心作用是：

> 在编译阶段检查并禁止危险的 `allow` 权限出现。

一句话总结：

> `allow` 是授权，`neverallow` 是防止你授予某些不该有的权限。

作为 Android 系统开发新手，你可以先记住：

1. SELinux 默认拒绝，只有 `allow` 才放行；
2. `neverallow` 禁止某些 `allow` 出现；
3. 违反 `neverallow` 会导致编译失败；
4. 不要随便删 AOSP 的 `neverallow`；
5. 优先检查 label、domain、文件位置和系统架构设计。