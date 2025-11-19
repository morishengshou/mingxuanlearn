要让这款「U 盘占用」工具拥有系统级、跨目录乃至跨用户空间的读写能力，核心在于**将它打包成系统/特权应用并匹配合适的权限与 SELinux 策略**。下面给出整体思路：

---

## 1. 安装位置与签名

1. **系统分区部署**  
   * 将 APK 放入 `/system/priv-app/UsbHammer/UsbHammer.apk`（或 `/system/app`，但跨用户访问通常需要 priv-app）。
   * 重新打包 system image 或在已 root 的测试设备上 remount `/system` 后拷贝。

2. **签名要求**  
   * 使用与整机相同的 **platform key** 重新签名，让应用被系统识别为可信特权 app。
   * Gradle 编译后，用 `apksigner` 对产物进行二次签名：  
     ```bash
     apksigner sign --ks platform.keystore --ks-key-alias platform UsbHammer.apk
     ```

3. **Manifest 中声明系统共享 UID（可选）**  
   * 若需要共享 system server 的 UID（谨慎使用），可在 `AndroidManifest.xml` 增加：  
     ```xml
     <manifest ... android:sharedUserId="android.uid.system">
     ```
   * 这需要与 platform key 匹配，否则安装失败。

---

## 2. 权限声明

系统/特权应用可以使用只对 priv-app 开放的签名级权限：

```xml
<uses-permission android:name="android.permission.MOUNT_UNMOUNT_FILESYSTEMS" />
<uses-permission android:name="android.permission.MOUNT_FORMAT_FILESYSTEMS" />
<uses-permission android:name="android.permission.WRITE_MEDIA_STORAGE" tools:ignore="ProtectedPermissions" />
<uses-permission android:name="android.permission.INTERACT_ACROSS_USERS_FULL" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

关键点：

- **`INTERACT_ACROSS_USERS_FULL`**：允许访问其他用户的数据与服务。
- **`WRITE_MEDIA_STORAGE`**（系统签名权限）：绕过分区存储限制，访问所有外部存储卷。
- Android 11+ 的 `MANAGE_EXTERNAL_STORAGE` 对系统 app 而言不是必须，但保留无妨。

---

## 3. SELinux 策略

若需要访问特定路径（如 `/mnt/user/<userId>/` 或 `/data/media/`），必须在设备的 `sepolicy` 中放行：

1. 创建新的 domain（例如 `usbhammer_app`），在 `seapp_contexts` 里将应用包名映射到该 domain。
   ```
   user=system seinfo=platform name=com.example.usbhammer domain=usbhammer_app type=app_data_file levelFrom=all
   ```

2. 在 `.te` 文件中添加允许规则，例如：
   ```te
   allow usbhammer_app mnt_user_file:dir { open read write add_name remove_name search };
   allow usbhammer_app storage_file:dir { read write search open };
   allow usbhammer_app fuseblk_file:file { read write open create getattr setattr unlink };
   ```

3. 重新编译 vendor/system image 并刷机，以生效新的 SELinux 策略。

---

## 4. 跨用户空间访问

有了 `INTERACT_ACROSS_USERS_FULL` + 对应 SELinux 允许后，可通过 `Context#createPackageContextAsUser`、`StorageManager` API 或直接访问 `/mnt/user/<id>/`/`/storage/emulated/<id>` 来操作其它用户的外部存储。

示例（遍历所有用户的外部卷）：

```java
UserManager userManager = (UserManager) getSystemService(USER_SERVICE);
StorageManager storageManager = getSystemService(StorageManager.class);

for (UserHandle user : userManager.getUserHandles(true)) {
    List<StorageVolume> volumes = storageManager.getStorageVolumes();
    for (StorageVolume volume : volumes) {
        File userPath = volume.getDirectoryForUser(user.getIdentifier());
        // 对 userPath 执行业务逻辑
    }
}
```

---

## 5. 调试与验证

1. **确认 UID**：`adb shell dumpsys package com.example.usbhammer | grep userId`.
2. **确认权限**：`adb shell pm dump com.example.usbhammer | grep grantedPermissions`.
3. **SELinux 监控**：运行时使用 `adb logcat | grep denied` 确认无拒绝记录，如有则迭代策略。
4. **跨用户测试**：在多用户环境（或 work profile）下，验证能否同时写入不同用户挂载的同一 U 盘卷。

---

### 重要提示

- 此类系统权限仅适用于自研 ROM、测试设备或经授权的设备管理场景。若在商用 Android 设备上未经 OEM 许可尝试，安装时会被拒绝或违反安全策略。
- 请谨慎处理跨用户与全盘访问，以避免误删或泄露数据；测试完成后及时卸载。

如需要具体的 `sepolicy` 补丁或集成脚本，可继续说明目标平台（AOSP 版本、SoC 供应商等），我可以给出更贴合的示例。