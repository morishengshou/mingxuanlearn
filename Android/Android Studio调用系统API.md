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

# 基于Android 12的实现
下面给你 **Android 12（S / API 31）** 下“两套实现”，并把各自的限制说清楚。两套都沿用你之前的生成逻辑（`.docx` 最小 OOXML / `.doc` 用 RTF 内容但后缀为 doc）。

---

## 方案 A：SAF（Storage Access Framework）选择目录写入（推荐）

### 特点
- 适用 Android 12：**稳定、合规、无需存储权限**
- 可以写入：用户在系统文件选择器里**明确授权**的任意目录（Downloads、Documents、SD 卡目录等）
- 你拿到的是 `treeUri`（不是绝对路径），通过 `DocumentFile` 写入

### 版本/限制说明（Android 12）
- 不需要 `WRITE_EXTERNAL_STORAGE`（该权限在 Android 11+ 基本无效）
- 写入范围只限于：**用户选择并授权的目录树**
- 不能直接用 `File("/storage/...")` 访问该目录（SAF 是 URI 模型）

> 你之前那套 `ACTION_OPEN_DOCUMENT_TREE + DocumentFile + openOutputStream()` 就是这个方案，Android 12 最推荐。

---

## 方案 B：用户输入“绝对路径”直接用 File API 写入（两种落地方式）

因为 Android 12 的 **Scoped Storage**，你想“任意指定目录 + 绝对路径写入”只有两条路：

### B1（强力但不推荐上架）：申请“所有文件访问权限” `MANAGE_EXTERNAL_STORAGE`
- 可以写入：几乎所有外部存储路径（例如 `/storage/emulated/0/xxx/...`）
- 代价：需要在设置页给“所有文件访问权限”，并且 **Google Play 严格限制**，一般调试/企业内测可用

**Android 12 限制**
- 不能弹系统运行时权限对话框直接授予；必须跳转系统设置页让用户手动打开
- Play 上架基本不让随便用（除非你属于文件管理/备份等少数豁免类别）
- 某些厂商 ROM 可能额外限制

### B2（合规但范围有限）：只允许写入“App 专属目录”或通过 MediaStore 写到公共集合
- **App 专属目录**：`getExternalFilesDir(null)` 下任意子目录  
  - 无需权限  
  - 但目录固定在：`/storage/emulated/0/Android/data/<pkg>/files/...`（卸载会清）
- **MediaStore Downloads/Documents**：可以写到公共 Downloads（可指定相对路径 `RELATIVE_PATH`）  
  - 不能保证“任意绝对路径”，只能写到系统集合里

> 你要“用户指定绝对路径任意目录”这一点，严格对应的是 **B1**。

---

# 代码落地：在 Demo 里提供两套实现（A + B1）

下面是在你现有 Demo 基础上加一个“写入模式”，并实现 **SAF** 和 **绝对路径（B1）** 两种写入。

## 1) UI 增加：模式选择 + 绝对路径输入框

在 `activity_main.xml` 里加一点控件（放在“选择目录”下面即可）：

```xml
<RadioGroup
    android:id="@+id/rgMode"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="horizontal"
    android:paddingTop="8dp">

    <RadioButton
        android:id="@+id/rbModeSaf"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:checked="true"
        android:text="SAF选目录" />

    <RadioButton
        android:id="@+id/rbModePath"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="绝对路径(File API)" />
</RadioGroup>

<EditText
    android:id="@+id/etAbsPath"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:hint="绝对路径目录，如 /storage/emulated/0/Download/word_demo"
    android:inputType="text" />
```

> SAF 模式时 `etAbsPath` 可以不填；Path 模式时不需要点“选择目录”。

---

## 2) Manifest：加入 MANAGE_EXTERNAL_STORAGE（用于 B1）

`AndroidManifest.xml` 增加（仅当你要启用 B1）：

```xml
<manifest ... xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />

    <application ...>
        ...
    </application>
</manifest>
```

---

## 3) MainActivity：增加“跳转设置授予所有文件访问权限”逻辑 + 按模式写入

把下面代码合并进你之前的 `MainActivity.kt`（重点看 `generate()` 分支）：

```kotlin
import android.content.ActivityNotFoundException
import android.net.Uri
import android.os.Environment
import android.provider.Settings
import java.io.File
import java.io.FileOutputStream

// 需要新增的控件引用
private lateinit var rbModeSaf: RadioButton
private lateinit var rbModePath: RadioButton
private lateinit var etAbsPath: EditText

override fun onCreate(savedInstanceState: Bundle?) {
    ...
    rbModeSaf = findViewById(R.id.rbModeSaf)
    rbModePath = findViewById(R.id.rbModePath)
    etAbsPath = findViewById(R.id.etAbsPath)

    etAbsPath.setText("/storage/emulated/0/Download/word_demo")
    ...
}

private fun ensureAllFilesAccessOrOpenSettings(): Boolean {
    if (Environment.isExternalStorageManager()) return true

    // 打开“所有文件访问权限”设置页
    try {
        val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
            data = Uri.parse("package:$packageName")
        }
        startActivity(intent)
    } catch (e: ActivityNotFoundException) {
        // 兜底到全局页
        val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
        startActivity(intent)
    }
    toast("请在设置中授予“所有文件访问”权限，然后返回重试")
    return false
}

private fun generate() {
    val baseName = etFileName.text?.toString()?.trim().orEmpty()
    if (baseName.isBlank()) { toast("请输入文件名"); return }

    val charCount = etCharCount.text?.toString()?.trim()?.toIntOrNull()
    if (charCount == null || charCount < 0) { toast("请输入正确的字符数量(>=0)"); return }

    val isDocx = rbDocx.isChecked
    val ext = if (isDocx) "docx" else "doc"
    val fileName = "$baseName.$ext"
    val randomText = RandomText.generate(charCount)

    if (rbModeSaf.isChecked) {
        // ===== 方案A：SAF =====
        val folderUri = pickedFolderUri
        if (folderUri == null) { toast("请先选择输出目录(SAF)"); return }

        val mime = if (isDocx)
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else
            "application/msword"

        val folder = androidx.documentfile.provider.DocumentFile.fromTreeUri(this, folderUri)
        if (folder == null || !folder.isDirectory) { toast("目录不可用"); return }

        folder.findFile(fileName)?.delete()
        val outFile = folder.createFile(mime, fileName) ?: run {
            toast("创建文件失败"); return
        }

        try {
            contentResolver.openOutputStream(outFile.uri, "w").use { os ->
                requireNotNull(os)
                if (isDocx) MinimalDocxWriter.writeDocx(os, randomText)
                else MinimalRtfWriter.writeRtfAsDoc(os, randomText)
            }
            toast("生成成功(SAF)：$fileName")
            log("SAF写入成功：$fileName\nuri=${outFile.uri}\n字符数=$charCount")
        } catch (e: Exception) {
            toast("生成失败：${e.message}")
            log(e.stackTraceToString())
        }

    } else {
        // ===== 方案B1：绝对路径 + MANAGE_EXTERNAL_STORAGE =====
        if (!ensureAllFilesAccessOrOpenSettings()) return

        val dirPath = etAbsPath.text?.toString()?.trim().orEmpty()
        if (dirPath.isBlank()) { toast("请输入绝对路径目录"); return }

        val dir = File(dirPath)
        if (!dir.exists()) dir.mkdirs()
        if (!dir.exists() || !dir.isDirectory) { toast("目录不可用/无法创建"); return }

        val outFile = File(dir, fileName)
        try {
            FileOutputStream(outFile, false).use { fos ->
                if (isDocx) MinimalDocxWriter.writeDocx(fos, randomText)
                else MinimalRtfWriter.writeRtfAsDoc(fos, randomText)
            }
            toast("生成成功(File)：${outFile.absolutePath}")
            log("File写入成功：${outFile.absolutePath}\n字符数=$charCount")
        } catch (e: Exception) {
            toast("生成失败：${e.message}")
            log(e.stackTraceToString())
        }
    }
}
```

---

# 两套实现的选择建议（Android 12）

| 方案 | 能写入任意目录？ | 是否需要权限 | 合规/上架风险 | 推荐用途 |
|---|---:|---:|---:|---|
| A：SAF 选目录 | 用户选到哪就能写哪 | 不需要存储权限（靠授权 URI） | 低 | **强烈推荐**，调试/正式都行 |
| B1：绝对路径 + MANAGE_EXTERNAL_STORAGE | 基本是 | 需要“所有文件访问”（设置里开） | 高（Play 严格限制） | **仅调试/企业/内测**，用于验证路径写入、压力测试 |
| B2：App 专属目录 / MediaStore | 不算“任意目录” | 通常不需要 | 低 | 合规但不满足“任意绝对路径” |

---

## 你确认两个点，我可以把 Demo 再补齐成“可直接拷贝工程”的完整版本
1) 你要的“指定目录”是指：  
- **必须**支持用户输入 `/storage/emulated/0/xxx` 这种路径（那就是 B1），还是  
- 允许只写到 **Downloads/Document**（MediaStore）也算？

2) 生成字符量的上限你预期多少？（比如 1e6 / 1e7）  
字符量很大时建议改成**流式写入**（边生成边写，不在内存拼超大 String），我也可以顺手给你把 `.docx` 改成分段流式输出，避免 OOM。