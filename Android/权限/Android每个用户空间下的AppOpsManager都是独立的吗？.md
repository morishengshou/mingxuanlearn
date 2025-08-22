简要结论：
- AppOpsManager 作为框架服务的客户端接口不是“每个用户空间独立的一份实现”；它是所有用户共用的系统服务（AppOpsService）的前端代理。
- 但“操作状态”(ops) 是按 userId 分区管理的：同一台设备上不同用户（Android 多用户/工作资料）对同一应用的 AppOps 结果可以不同且相互隔离。

展开说明：
- AppOpsManager 是应用进程内的一个 Java 客户端类，实际通过 Binder 调用 system_server 里的 AppOpsService。
- AppOpsService 在内部以 uid（包含 userId 前缀）为键来记录与判定各类 op（如录音、读取剪贴板、位置等）的模式与历史。因此：
  - 不同 Android 用户（user 0/10/11…）即便安装了同一个包名，因其 uid 不同（uid = userId*100000 + appId），AppOps 记录是分开的。
  - 主用户与工作资料（work profile，属于不同的 profile user）同理相互隔离。
- 因此，从“服务实例”角度：不是独立的（同一个系统服务）。
- 从“数据与权限判定”角度：是按用户隔离的（每个 user/profile 的 ops 独立存储与生效）。

开发者注意点：
- 使用 AppOpsManager 时，传参中的 uid/package 会决定查询或设置的是哪个用户空间下的记录。
- adb/shell 工具如 appops set/get 默认针对当前 user，可用 --user <id> 指定目标用户。
- 在设备所有者/配置文件所有者场景下，策略可分别对不同用户或工作资料设置 AppOps，不会互相影响。