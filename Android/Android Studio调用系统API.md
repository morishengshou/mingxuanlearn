简要结论
- @SystemApi 只面向“系统组件/受信任应用”。普通第三方应用无法直接调用；即便反射成功，常会被权限或 SELinux 拦截。
- 想“正常调用且在 Android Studio 不报错/有补全”，需要使用系统 SDK（system image 的 stub-jar），并把应用做成系统/priv-app，或与平台同签并声明对应 signature 权限。

可行路径概览
1) 开源平台源码环境（AOSP/ROM/OEM 开发）：
   - 使用 platform/system SDK（含 @SystemApi stub）。
   - 用平台签名编译并安装到 /system/priv-app。
   - 在 manifest 中声明相关 signature 权限。
   - 这种情况下，Android Studio 会识别并补全 @SystemApi API，不会标红。

2) 普通应用商店 App：
   - 基本不可用。即使通过反射调用，运行时也会因缺少 signature 权限或被灰名单阻断。

如何在 Android Studio 正确引用 @SystemApi
你有两种主要方式：使用 system SDK（公共）或使用完整平台源码编译的 SDK（推荐在 AOSP 环境）。

方案A：使用“System SDK”依赖（官方 system-stubs）
- Google 从 Android 10 起在 SDK 中提供了 system API 的 stubs（称为 “System SDK”），但不会随普通 compileSdk 自动暴露，需单独添加。
- 在 Gradle 中配置：
  - compileSdkVersion/targetSdkVersion 设为与你设备一致的版本（如 34）。
  - 添加系统 stubs 作为 compileOnly（仅编译期）依赖。

Gradle 示例（AGP 8.x，Kotlin DSL 伪例，Groovy 同理）：
```groovy
android {
  namespace "com.example.systemapidemo"
  compileSdkVersion 34
  defaultConfig {
    minSdkVersion 29
    targetSdkVersion 34
  }
}

dependencies {
  // systemApis 是 Google 在 SDK 中提供的 stubs 库名（Android 11+ 可用，具体坐标由 SDK 管理，不走 Maven）
  // 在普通外部工程里不能直接用坐标拉取。常见做法有两种：
  // 1) 在本机 Android SDK/platforms/android-34/ 里手动引用 android_system_stubs.jar
  // 2) 或使用 AOSP prebuilts 的 system-stubs jar

  compileOnly files("${android.sdkDirectory}/platforms/android-34/optional/org.apache.http.legacy.jar") // 示例：演示如何引用本机 SDK 文件
  // 关键：把 system stubs jar 加入 compileOnly（路径举例，见下文“获取 stubs”）
  compileOnly files("${android.sdkDirectory}/platforms/android-34/system.jar") // 若存在 system stubs；不同 SDK 结构名称可能为 android-system.jar 或 framework-system-stubs.jar
}
```

获取 system stubs 的正确方式
- AOSP 编译产物：
  - out/soong/.intermediates/frameworks/base/framework/android_system_stubs_current/android_common/combined/android_system_stubs_current.jar
  - 或 prebuilts/sdk/<api>/system/android.jar（不同版本路径名称略有差异）
- 已安装的官方 SDK：
  - ${ANDROID_HOME}/platforms/android-<api>/framework-system-stubs.jar 或 android_system_stubs.jar（新版本）
  - 注意：SDK 目录结构会变，实际文件名请在该目录搜索 “system” “stubs”。

为什么用 compileOnly
- 这些 jar 仅提供编译期符号，最终运行时以系统镜像中的 framework 实现为准；不应打包进 APK。

让 Studio 不再标红的步骤
- 将 system stubs jar 加入模块的依赖（compileOnly）。
- 如果还需访问隐藏 API（@UnsupportedAppUsage / @hide），需要 hidden API stubs（framework telephony stubs 等），同理以 compileOnly 引用相应 stubs jar。
- 在 Project Structure 或 Gradle sync 后，AS 会识别符号，代码不再报错，补全也可用。

运行时前置条件（否则即使编译过也会失败）
- 你的 App 必须具备调用该 @SystemApi 所需的权限，绝大多是 signature 或 system 权限：
  - App 必须放在 /system/priv-app（或 /system/app），并在 privapp-permissions-*.xml 中被白名单授权；
  - 或与平台同签（platform certificate）从而自然获得 signature 权限。
- 某些 API 还受到 SELinux 域限制，仅 system_server/privileged app 可用。
- Android P+ 对“非 SDK 接口”有灰名单/黑名单限制。如果你通过反射访问隐藏 API，会触发 hidden API enforcement。@SystemApi 本身是 SDK 内公开的，不受该限制；但其参数/返回类型如果依赖 @hide 类，仍可能被限制。

Manifest 与权限示例
- 假设你要调用 AppOpsManager#setMode（需要 MANAGE_APP_OPS_MODES）：
```xml
<manifest ...>
  <uses-permission android:name="android.permission.MANAGE_APP_OPS_MODES"/>
  <application ... />
</manifest>
```
- 对于 telephony、device policy、statsd 等系统域 API，请查其对应的 signature 权限。

在 AOSP/ROM 开发中的推荐流程
- 在 AOSP 中编译你的系统 App（make 或 Soong/Gradle with Soong）。
- 在 app 的 Android.bp 里添加 uses_libs/ sdk_version = "system_current" 或 "system_X"：
  - Android.bp 示例：
    - sdk_version: "system_current"
  - 这会自动链接 system stubs，并在编译期提供 @SystemApi 符号。
- 使用平台私钥签名并放置到 /system/priv-app，必要时添加 privapp-permissions 以授予 signature 权限。

常见问题
- 编译通过、运行崩溃 SecurityException：
  - 缺少 signature 权限或不在 priv-app 白名单。
- 编译器仍找不到符号：
  - 你引用的是 public android.jar 而非 system stubs。检查 Gradle 依赖路径是否指向 system stubs。
- 通过反射“能跑”但行为异常：
  - 多数系统服务会在 Binder 层再做权限/uid 校验，反射并不能绕过。

最小可行示例
- 目标：调用 @SystemApi 的 AppOpsManager.setMode（Java）
  1) 在 Gradle 中以 compileOnly 引入 framework-system-stubs.jar。
  2) 代码正常 import android.app.AppOpsManager 并调用 setMode。
  3) Manifest 声明 MANAGE_APP_OPS_MODES。
  4) 用平台签名并安装为 priv-app；授予签名权限。
  5) 在设备上执行，调用成功。

总结
- 想在 Android Studio “看见/用到” @SystemApi，需要用 system stubs 进行编译。
- 想在设备“跑得通”，你的 App 必须是系统/受信任应用并持有对应 signature 权限，有时还需 SELinux 放行。
- 普通第三方 App 不具备这些条件。