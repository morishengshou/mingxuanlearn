下面是对 Android 中 vold（Volume Daemon）机制的系统性、较深入的介绍，涵盖职责、架构演进、关键组件、工作流程、配置与策略、调试排障及常见问题。

—  
一、vold 是什么

- vold（Volume Daemon）是 Android 的存储卷管理守护进程，负责：
  - 发现与管理块设备（内置/外置存储、U 盘、SD 卡、光盘镜像等）
  - 分区/格式化（ext4、f2fs、vfat、exfat 等）
  - 挂载/卸载及状态维护
  - Adoptable storage（可采用/合并的外部卡作为内部存储）
  - ASEC/OBB（Legacy，早期应用加密容器、Opaque Binary Blob 挂载）
  - 媒体扫描触发、存储策略（读写权限、加密）
  - 与框架层（MountService/StorageManager/StorageUserService）通信
  - 与磁盘加密/文件级加密（FBE/FDE）配合、Emulated storage 管理

—  
二、架构演进与整体框图

1) 早期（Android 2.x-4.x）
- Native 守护进程 vold 通过 socket 与 Java 层 MountService 通信。
- 主要依赖内核 uevent（netlink）发现块设备，调用工具（mkfs.*、mount/umount）进行操作。
- 支持 ASEC、OBB 的 loop 设备挂载。

2) Android 5.0-6.0
- 引入 Emulated storage（/storage/emulated/0 等），通过 sdcard（后为 sdcardfs）虚拟化多用户视角。
- 引入 Adoptable storage（将外置卡加密后并入内部存储，基于 dm-crypt/dm-default-key）。
- SELinux 强化，权限更细分。

3) Android 7.0-8.1
- sdcardfs 内核文件系统广泛使用，减少 FUSE 开销。
- vold 职责扩大：管理加密密钥、AIDL/HIDL 交互雏形。

4) Android 10+
- 引入“分区存储”（scoped storage），框架访问模型改变，但底层卷管理仍由 vold。
- FBE（File-Based Encryption）成为默认；metadata encryption（dm-default-key）加入。
- sdcardfs 后续被移除，回到 FUSE（GFNI），采用 passthrough 改善性能（Android 11 起的 EMM/FUSE 改进）。
- vold 代码持续维护于 system/vold，利用 libfs_mgr、fscrypt、keymaster 等库。

简化的框图（概念）：
- 应用层: Storage Access Framework / MediaStore / APIs
- 框架层: StorageManagerService、MountService (legacy)、StorageStats, OBB API
- Native 服务: vold（通过 Binder/HIDL/AIDL 或 Netlink 与框架交互）
- 内核: uevent/netlink、dm-crypt、fscrypt、FUSE、块层、ext4/f2fs/vfat 驱动
- 工具/库: mkfs.f2fs, mkfs.ext4, fsck.*, blkid, libfs_mgr, libvold

—  
三、关键组件与配置

- vold 守护进程
  - 路径：system/vold
  - 启动：init.rc 中的 service vold，通常在 early-boot/late-init 阶段启动
  - 权限：需要 CAP_SYS_ADMIN、CAP_SYS_MOUNT、原始块设备访问、SELinux 域 vold

- 配置文件
  - /system/etc/vold.fstab（非常早期；现代 Android 基本不用）
  - /system/etc/vold.conf（早期遗留）
  - 现代系统主要使用 fstab.*（vendor/etc/fstab.<hardware>）：通过 fs_mgr 驱动启动阶段挂载；vold 读取并配合管理可移除卷。
  - storage 序列表达：通过内核 uevent 探测块设备 + sysfs 属性，不再硬编码。

- 相关库/工具
  - libfs_mgr：解析 fstab、处理 dm-verity、metadata 加密
  - fscrypt / keymaster：文件级加密密钥派生与管理
  - mkfs/fsck：不同文件系统的格式化与检查
  - blkid/libblkid：探测分区类型

- 虚拟/逻辑设备
  - dm-crypt/dm-default-key：加密层
  - loop 设备（legacy for OBB/ASEC）
  - FUSE 守护（sdcard、sdcardfs、modern FUSE）

—  
四、vold 如何工作：核心流程

1) 设备发现
- 内核在插入/移除 SD 卡、U 盘时通过 uevent 发送通知（NETLINK_KOBJECT_UEVENT）。
- vold 监听并解析 uevent（ACTION=add/remove/change, DEVPATH, SUBSYSTEM=block, DEVNAME 等）。
- 通过 sysfs 读取块设备属性（可移动 removable、大小、分区表、fs 类型等）。

2) 盘与卷建模
- Disk: 对应一个物理/逻辑磁盘（如 mmcblk1、sda）。可包含多个分区。
- Volume: 对应可挂载的文件系统实体（分区、分区上的文件系统、或者映射后的 dm 设备）。
- Private vs Public:
  - Public: 外部介质以明文文件系统（vfat/exfat/ext4/f2fs）挂载到 /storage/XXXX-XXXX（UUID），可被多 App 通过 SAF 访问。
  - Private (Adoptable): 将外部介质格式化为受设备加密管理的“内部”存储，挂载到 /data/media 下的子树并受 FBE/密钥控制。

3) 文件系统判定与准备
- blkid 探测分区签名（GPT/MBR、ext/f2fs/vfat/exfat）。
- 必要时执行 fsck.* 进行一致性检查。
- 对 Public 卷：直接 mount 到 /mnt/media_rw/XXXX-XXXX，再通过 sdcard(FUSE)导出到 /storage/XXXX-XXXX，应用访问走 FUSE 层（权限与隔离）。
- 对 Private 卷：创建 dm-crypt 映射，派生密钥（keymaster/keystore），格式化为 ext4/f2fs，将其合并到 /data 分层（通常挂载到 /mnt/expand/UUID），然后通过 bind mount 或逻辑卷将 app 私有数据存储迁移到该卷。

4) Emulated storage
- 对内置存储（/data/media）通过 FUSE/sdcard 服务导出为 /storage/emulated/<userId>，多用户隔离。
- vold 管理 FUSE 守护进程的生命周期和参数（读写权限、uid/gid 映射、umask 等）。

5) OBB/ASEC（遗留）
- OBB 文件可通过 mount loop + aes-crypto（早期）方式挂载；现代系统多通过 StorageManager/PackageInstaller 和 SAF 替代，vold 保留兼容路径。

6) 卷状态机与通知
- 状态：NoMedia -> Pending -> Checking -> Mounted -> Unmounted/BadRemoval -> Ejecting -> Removed
- vold 将状态事件通过 Binder/套接字通知到框架层（StorageManagerService），再广播给应用（如 ACTION_MEDIA_MOUNTED，现代系统出于隐私已限制）。

7) 加密与解锁时序
- FDE（早期）：boot 阶段需要用户输入 PIN 解锁 /data；vold 负责调用 cryptfs，设置 dm-crypt。
- FBE（现代）：metadata 加密 + 文件级加密。vold 协助解锁 CE（Credential Encrypted）存储与 DE（Device Encrypted）存储分区；用户解锁后，CE key 解封，应用数据可访问。

—  
五、Adoptable Storage 流程（简述）

- 用户在设置中选择“作为内部存储”格式化外置卡：
  1) vold 擦除卡、创建分区布局（通常一个 private 分区，可选 public 分区）
  2) 生成随机密钥并通过硬件 Keymaster 绑定（防止离线迁移）
  3) 建立 dm-crypt 映射，mkfs 为 ext4 或 f2fs
  4) 挂载到 /mnt/expand/UUID，并将应用数据可迁移部分移动到该卷（PackageManager + installd 协作）
  5) 记录 metadata 到 /metadata 或 /data/misc/vold
- 移除时需要“迁移回内置存储”，否则数据不可在其他设备读取。

—  
六、权限与安全模型

- SELinux：vold 运行在 vold 域，访问块设备、dm-crypt、mount、ioctl 需要策略允许。
- App 访问受限：
  - 传统模式：外置 Public 卷通过 FUSE/sdcard 施加权限过滤（noexec、nodev、nosuid、uid/gid remap）。
  - 分区存储后：大多数直接路径访问受限，需通过 SAF/MediaStore 获取。
- 加密密钥管理：使用 keystore/keymaster 派生、存储（通常不以明文落盘），与用户凭据绑定（FBE）。

—  
七、调试与常用命令

- 查看卷与磁盘
  - adb shell sm list-disks
  - adb shell sm list-volumes [public|private|emulated|all]
  - adb shell sm has-adoptable
  - adb shell sm set-force-adoptable true/false（开发测试）
- 格式化/分区
  - adb shell sm partition <diskId> public|private|mixed <ratio>
  - adb shell sm forget <volumeUuid>（遗忘 adoptable 卷密钥）
- 挂载点观察
  - adb shell mount | grep -E 'storage|mnt'
  - adb shell ls -l /dev/block | /sys/block
  - adb shell cat /proc/mounts
- 日志
  - logcat -b events -b system | grep -i vold
  - dmesg | grep -i vold 或 block/ufs/mmc
- fsck/mkfs
  - 在 recovery/用户空间谨慎使用 mkfs.f2fs, fsck.f2fs, e2fsck, fsck.exfat

—  
八、代码结构（概览，可能随版本变动）

- system/vold/
  - VolumeManager：整体管理器，处理事件、维护卷列表
  - Disk, PublicVolume, PrivateVolume, EmulatedVolume, StubVolume 类
  - Devmapper：dm-crypt 映射相关
  - FsCrypt/FsCryptKeyManager：FBE 相关
  - Process.cpp：管理 FUSE 守护等子进程
  - Check.cpp/Fsck.cpp：文件系统检查
  - VoldNativeService（binder 接口）
  - cryptfs.c/Ext4Crypt.cpp（历史遗留与过渡）
- external/fsck, system/core/fs_mgr：配套库

—  
九、典型事件链路示意

- 插入一张 exFAT 的 SD 卡（Public 模式）：
  1) 内核 uevent: ACTION=add, SUBSYSTEM=block, DEVNAME=mmcblk1
  2) vold 识别 Disk(mmcblk1)，读取分区表 -> 分区 mmcblk1p1
  3) blkid 判断 fs=exfat；先 fsck.exfat（若需要）
  4) mount 到 /mnt/media_rw/XXXX-XXXX（opts: nodev,nosuid,dirsync,uid/gid=media_rw）
  5) 启动/配置 FUSE，导出到 /storage/XXXX-XXXX
  6) StorageManager 通知系统与用户（通知面板显示“可用于传输文件”）

—  
十、常见问题与排障思路

- 无法识别外置卡
  - 检查 dmesg 是否有块设备识别；查看 /sys/block/mmcblk1 removable、size
  - 看 uevent 是否到达 vold（logcat: vold: ...）
  - SELinux 拒绝（audit avc denied）需看策略
- 挂载失败
  - fsck 输出错误；尝试备份后重新格式化
  - 文件系统内核模块缺失（exfat 驱动）或用户态工具缺失
- Adoptable 卷丢失
  - 换机后不可读属正常（密钥绑定）；需“迁移数据”再移除
  - metadata 匹配失败：sm forget + 重新格式化
- 性能问题
  - FUSE 开销：Android 11 之后已优化；查看 sdcard daemon/FUSE 线程 CPU
  - exFAT 实现不同版本性能差异
- 启动慢
  - FBE 解锁时序、fsck 时长、媒体扫描（MediaProvider）影响

—  
十一、与分区存储和多用户的关系

- 多用户：/storage/emulated/<userId> 由 FUSE 导出，vold 知道当前前台/解锁用户，按需切换可见性。
- 分区存储：vold 提供卷与挂载基础，访问控制主要在框架与内核层；应用通过 SAF/MediaStore 访问公有媒体目录。

—  
十二、实践建议

- 定制 ROM 或移植平台：
  - 确保 fstab 与分区表正确，fs_mgr 能挂载基础分区
  - 在 vendor 清单中声明所需文件系统支持、内核配置启用 dm-crypt/fscrypt/FUSE
  - 提供对应 mkfs/fsck 工具
  - 调整 SELinux 策略以允许 vold 必要操作
- App 开发：
  - 针对外部存储，使用 SAF/MediaStore，而非直接文件路径
  - 监听 StorageVolume 回调而非老的广播

如果你有特定 Android 版本、设备或问题场景（如 Adoptable storage 挂载失败、FBE 解锁顺序、exFAT 支持），我可以基于该上下文提供更针对性的流程与命令。