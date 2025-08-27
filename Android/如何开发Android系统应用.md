要在系统应用中调用被注解为 @SystemApi 的接口，你需要同时满足“编译期可见”和“运行期可用”两件事。概要步骤如下：

一、准备系统级开发环境
- 使用与目标设备/ROM版本匹配的 AOSP 源码或官方公开的 system APIs stub。
- 使用 platform 签名对你的 APK 进行签名（与系统镜像相同的证书）。否则很多 @SystemApi 即便可编译，也会在运行时因签名/权限校验失败。
- 将应用放入 /system/priv-app 或 /system/app（依接口要求选择），并在清单中声明为 privileged（放置到 priv-app 即可获得特权，不需要额外标记）。

二、为 Android Studio 配置可见的 System API
Android Studio/Gradle 默认只提供 public SDK，不能直接引用 @SystemApi。你有几种方式：

方式 A：使用 AOSP 提供的 system SDK stubs（推荐）
- 从已同步的 AOSP 源码中，使用 out/soong/.intermediates/frameworks/base/framework/android_system_stubs_current/android_system_stubs_current.jar（或对应平台版本的 system stubs，路径会随版本略有差异）。
- 在模块的 build.gradle 中添加该 jar 为 compileOnly 依赖：
  - 将该 jar 复制到项目的 libs/，或通过本地 file 引用。
  - 示例：
    ```
    dependencies {
        compileOnly files('libs/android_system_stubs.jar')
        // 可选：compileOnly files('libs/hiddenapi-stubs.jar') 仅当你确有必要引用 @hide（非 SystemApi）时
    }
    ```
- 将 compileSdkVersion 设为与你的 stubs 匹配的 API 级别（如 34/35）。

方式 B：使用 sdk/system 预构建（某些 ROM 提供）
- 某些厂商或定制 ROM 会提供 system SDK 包（包含 android.jar 的 system 变体）。
- 配置方法与方式 A 类似，作为 compileOnly 或 provided 依赖引入。

方式 C：在 AOSP 源内直接编译应用（Soong/Make 集成）
- 如果你的应用随系统一起编译，使用 Android.bp/Android.mk 中的相关标签：
  - 在 Android.bp 中声明 sdk_version: "system_current" 或具体版本 "system_34"。
  - 如需 @hide（不建议），可使用 sdk_version: "core_platform"（需要明确审批，且对 CTS 兼容性有风险）。
- 这种方式不依赖 Android Studio 的 Gradle 解析，推荐系统内置应用采用。

三、清单与权限
- 将应用放置到 priv-app 目录，以获得 privileged 权限授予资格。
- 在 AndroidManifest.xml 中声明需要的 system 权限：
  - 例如：
    ```
    <uses-permission android:name="android.permission.INTERACT_ACROSS_USERS_FULL"/>
    <uses-permission android:name="android.permission.MANAGE_USERS"/>
    ```
- 如果某些 @SystemApi 接口标注了 RequiresPermission 或 @RequiresPermission(allOf/anyOf=...)，确保在清单中声明并且设备在安装时授予。priv-app 中常见权限会被默认授予，但也受权限保护级别和允许列表限制。
- Android 10+ 还有 privileged-permissions allowlist：需要在系统镜像的 etc/permissions/privapp-permissions-*.xml 中为你的包名列出要自动授予的权限。

四、签名与安装
- 使用平台签名（platform.pk8/.x509.pem）签名 APK。Gradle 的 debug/release 签名不行。
- 将 APK 放到 /system/priv-app/YourApp/YourApp.apk，重新打包系统镜像或以 root 将其推入（需与目标系统版本匹配），并确保文件权限/SELinux 标签正确。
- 验证：adb shell pm list packages -U | grep your.package，adb shell dumpsys package your.package 检查签名与权限授予。

五、Gradle/Studio 示例配置
- build.gradle:
  ```
  android {
      compileSdkVersion 34
      defaultConfig {
          minSdkVersion 28
          targetSdkVersion 34
      }
      compileOptions {
          sourceCompatibility JavaVersion.VERSION_17
          targetCompatibility JavaVersion.VERSION_17
      }
  }
  dependencies {
      compileOnly files('libs/android_system_stubs.jar')
      // 如果需要 LauncherApps 等也在 public，正常 implementation 即可
      // 不要把 system stubs 作为 implementation，避免打包进 APK
  }
  ```
- 将 system stubs jar 放入 libs/ 并确保不随 APK 打包（compileOnly 已满足）。

六、避免误区
- 仅把 hidden API 或反射作为最后手段。Android P 之后对隐藏 API 有严格的灰名单/黑名单限制，未加入白名单会在运行时报错。
- @SystemApi 也分 test 和 public/system scopes，不同版本可见性有所变化，注意选择匹配平台版本的 stubs。
- 仅有编译期可见不等于可调用：运行时还需权限、AppOps、签名校验通过。
- 不要把修改过的 android.jar 直接替换 SDK；改用 compileOnly 的 stubs 最安全。
- 若你的应用需要在系统构建中参与，优先使用 Soong 方式并设置 sdk_version: "system_X"；这是谷歌官方构建对 SystemApi 的标准路径。

七、简要流程清单
- 获取目标平台版本的 system stubs jar。
- 在 Android Studio 用 compileOnly 引入，设置匹配的 compileSdk。
- 使用平台证书签名并安装到 priv-app。
- 在系统权限白名单中为你的包配置需要的 privileged 权限。
- 在设备上验证接口可调用与权限授予。

如果你说明目标 Android 版本、你是否能访问 AOSP 源/平台签名、是随系统编译还是单独安装，我可以给出更具体的文件路径与脚本示例。