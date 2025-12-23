下面给你一套**可直接在 Android Studio 创建并运行的 Demo 工程代码**（Kotlin），用于调试生成 Office Word 文件：

- 在**用户指定目录**（通过系统“选择文件夹”/SAF）创建 `.docx` 或 `.doc`
- 文件内容为**随机字符**
- 可设置**任意字符数量**（例如 10、1000、100000…）
- **不依赖第三方库**：  
  - `.docx`：生成最小可打开的 OOXML 结构（Zip + XML），Word/WPS 可正常打开  
  - `.doc`：用 **RTF 格式内容**保存，但扩展名用 `.doc`（Word 可打开；严格意义上不是老式二进制 DOC，但满足“后缀 doc 且可被 Word 打开”的调试需求）

> 我无法在对话里直接给你打包好的 APK，但下面代码你复制进去即可一键运行并生成文件。

---

## 1) 新建工程建议

- Android Studio：新建 **Empty Views Activity**（XML 布局，最省事）
- minSdk：建议 **21+**
- targetSdk：随你（34/35 都可以）

---

## 2) `AndroidManifest.xml`

无需存储权限（SAF 选择目录后系统授权），只要默认即可：

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest package="com.example.wordgendemo"
    xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="true"
        android:label="WordGenDemo"
        android:supportsRtl="true">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>

</manifest>
```

---

## 3) `activity_main.xml`

`app/src/main/res/layout/activity_main.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:padding="16dp"
        android:orientation="vertical">

        <Button
            android:id="@+id/btnPickFolder"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="选择输出目录(文件夹)" />

        <TextView
            android:id="@+id/tvFolder"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="未选择目录"
            android:paddingTop="8dp" />

        <EditText
            android:id="@+id/etFileName"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="文件名(不含后缀)，例如 test_001"
            android:inputType="text" />

        <EditText
            android:id="@+id/etCharCount"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="随机字符数量，例如 1000"
            android:inputType="number" />

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:paddingTop="8dp">

            <RadioGroup
                android:id="@+id/rgExt"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal">

                <RadioButton
                    android:id="@+id/rbDocx"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:checked="true"
                    android:text=".docx (OOXML)" />

                <RadioButton
                    android:id="@+id/rbDoc"
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:text=".doc (RTF内容)" />
            </RadioGroup>
        </LinearLayout>

        <Button
            android:id="@+id/btnGenerate"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="生成 Word 文件" />

        <TextView
            android:id="@+id/tvLog"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="日志输出..."
            android:paddingTop="12dp" />

    </LinearLayout>
</ScrollView>
```

---

## 4) `MainActivity.kt`（核心逻辑：选目录 + 生成 doc/docx）

`app/src/main/java/com/example/wordgendemo/MainActivity.kt`

```kotlin
package com.example.wordgendemo

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.DocumentsContract
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.documentfile.provider.DocumentFile

class MainActivity : AppCompatActivity() {

    private var pickedFolderUri: Uri? = null

    private lateinit var btnPickFolder: Button
    private lateinit var tvFolder: TextView
    private lateinit var etFileName: EditText
    private lateinit var etCharCount: EditText
    private lateinit var rbDocx: RadioButton
    private lateinit var rbDoc: RadioButton
    private lateinit var btnGenerate: Button
    private lateinit var tvLog: TextView

    private val pickFolderLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val data = result.data
            if (result.resultCode == RESULT_OK && data != null) {
                val uri = data.data ?: return@registerForActivityResult
                // 记住权限
                val flags = data.flags and
                    (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                contentResolver.takePersistableUriPermission(uri, flags)

                pickedFolderUri = uri
                tvFolder.text = "已选择目录: $uri"
                log("已持久化授权，可在该目录生成文件")
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        btnPickFolder = findViewById(R.id.btnPickFolder)
        tvFolder = findViewById(R.id.tvFolder)
        etFileName = findViewById(R.id.etFileName)
        etCharCount = findViewById(R.id.etCharCount)
        rbDocx = findViewById(R.id.rbDocx)
        rbDoc = findViewById(R.id.rbDoc)
        btnGenerate = findViewById(R.id.btnGenerate)
        tvLog = findViewById(R.id.tvLog)

        etFileName.setText("test_${System.currentTimeMillis()}")
        etCharCount.setText("1000")

        btnPickFolder.setOnClickListener { openFolderPicker() }
        btnGenerate.setOnClickListener { generate() }
    }

    private fun openFolderPicker() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
            addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            // 可选：尽量从主存储打开
            putExtra(DocumentsContract.EXTRA_INITIAL_URI, null as Uri?)
        }
        pickFolderLauncher.launch(intent)
    }

    private fun generate() {
        val folderUri = pickedFolderUri
        if (folderUri == null) {
            toast("请先选择输出目录")
            return
        }

        val baseName = etFileName.text?.toString()?.trim().orEmpty()
        if (baseName.isBlank()) {
            toast("请输入文件名")
            return
        }

        val charCount = etCharCount.text?.toString()?.trim()?.toIntOrNull()
        if (charCount == null || charCount < 0) {
            toast("请输入正确的字符数量(>=0)")
            return
        }

        val isDocx = rbDocx.isChecked
        val ext = if (isDocx) "docx" else "doc"
        val mime = if (isDocx)
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else
            "application/msword"

        val folder = DocumentFile.fromTreeUri(this, folderUri)
        if (folder == null || !folder.isDirectory) {
            toast("目录不可用")
            return
        }

        val fileName = "$baseName.$ext"
        // 如果同名已存在，先删掉（调试用）
        folder.findFile(fileName)?.delete()

        val outFile = folder.createFile(mime, fileName)
        if (outFile == null) {
            toast("创建文件失败")
            return
        }

        try {
            contentResolver.openOutputStream(outFile.uri, "w").use { os ->
                if (os == null) throw RuntimeException("openOutputStream 返回 null")

                val randomText = RandomText.generate(charCount)
                if (isDocx) {
                    MinimalDocxWriter.writeDocx(os, randomText)
                } else {
                    MinimalRtfWriter.writeRtfAsDoc(os, randomText)
                }
            }
            toast("生成成功：$fileName")
            log("生成成功：$fileName\nuri=${outFile.uri}\n字符数=$charCount\n格式=${if (isDocx) "DOCX" else "DOC(RTF)"}")
        } catch (e: Exception) {
            e.printStackTrace()
            toast("生成失败：${e.message}")
            log("生成失败：${e.stackTraceToString()}")
        }
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    private fun log(msg: String) {
        tvLog.text = msg
    }
}
```

---

## 5) 随机字符生成 `RandomText.kt`

`app/src/main/java/com/example/wordgendemo/RandomText.kt`

```kotlin
package com.example.wordgendemo

import java.security.SecureRandom

object RandomText {
    private val rnd = SecureRandom()
    private val alphabet = ("abcdefghijklmnopqrstuvwxyz" +
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
            "0123456789" +
            "     ").toCharArray()

    fun generate(charCount: Int): String {
        if (charCount <= 0) return ""
        val sb = StringBuilder(charCount)
        repeat(charCount) {
            sb.append(alphabet[rnd.nextInt(alphabet.size)])
        }
        return sb.toString()
    }
}
```

---

## 6) 生成最小 DOCX（不用 POI）`MinimalDocxWriter.kt`

`app/src/main/java/com/example/wordgendemo/MinimalDocxWriter.kt`

```kotlin
package com.example.wordgendemo

import java.io.OutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object MinimalDocxWriter {

    fun writeDocx(outputStream: OutputStream, text: String) {
        ZipOutputStream(outputStream).use { zip ->
            // 1) [Content_Types].xml
            zip.putNextEntry(ZipEntry("[Content_Types].xml"))
            zip.write(contentTypesXml().toByteArray(Charsets.UTF_8))
            zip.closeEntry()

            // 2) _rels/.rels
            zip.putNextEntry(ZipEntry("_rels/.rels"))
            zip.write(relsXml().toByteArray(Charsets.UTF_8))
            zip.closeEntry()

            // 3) word/document.xml
            zip.putNextEntry(ZipEntry("word/document.xml"))
            zip.write(documentXml(text).toByteArray(Charsets.UTF_8))
            zip.closeEntry()

            // 4) word/_rels/document.xml.rels
            zip.putNextEntry(ZipEntry("word/_rels/document.xml.rels"))
            zip.write(wordDocumentRelsXml().toByteArray(Charsets.UTF_8))
            zip.closeEntry()
        }
    }

    private fun contentTypesXml(): String = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
        </Types>
    """.trimIndent()

    private fun relsXml(): String = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1"
            Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
            Target="word/document.xml"/>
        </Relationships>
    """.trimIndent()

    private fun wordDocumentRelsXml(): String = """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        </Relationships>
    """.trimIndent()

    private fun documentXml(text: String): String {
        // Word 段落可很长；这里按每 500 字符断一段，避免极端长 run
        val escapedChunks = text.chunked(500).map { escapeXml(it) }
        val paragraphs = if (escapedChunks.isEmpty()) {
            """<w:p><w:r><w:t xml:space="preserve"></w:t></w:r></w:p>"""
        } else {
            escapedChunks.joinToString("\n") { chunk ->
                // xml:space="preserve" 保留空格
                """<w:p><w:r><w:t xml:space="preserve">$chunk</w:t></w:r></w:p>"""
            }
        }

        return """
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                $paragraphs
                <w:sectPr/>
              </w:body>
            </w:document>
        """.trimIndent()
    }

    private fun escapeXml(s: String): String =
        buildString(s.length) {
            for (ch in s) {
                when (ch) {
                    '&' -> append("&amp;")
                    '<' -> append("&lt;")
                    '>' -> append("&gt;")
                    '"' -> append("&quot;")
                    '\'' -> append("&apos;")
                    else -> append(ch)
                }
            }
        }
}
```

---

## 7) 生成 `.doc`（RTF 内容）`MinimalRtfWriter.kt`

`app/src/main/java/com/example/wordgendemo/MinimalRtfWriter.kt`

```kotlin
package com.example.wordgendemo

import java.io.OutputStream

object MinimalRtfWriter {

    fun writeRtfAsDoc(outputStream: OutputStream, text: String) {
        val safe = escapeRtf(text)

        // 按 1000 字符换一段
        val chunks = safe.chunked(1000)
        val body = if (chunks.isEmpty()) "" else chunks.joinToString("\\par\n")

        val rtf = """
            {\rtf1\ansi\deff0
            {\fonttbl{\f0 Calibri;}}
            \fs22
            $body
            }
        """.trimIndent()

        outputStream.write(rtf.toByteArray(Charsets.UTF_8))
    }

    private fun escapeRtf(s: String): String {
        val sb = StringBuilder(s.length)
        for (ch in s) {
            when (ch) {
                '\\' -> sb.append("\\\\")
                '{' -> sb.append("\\{")
                '}' -> sb.append("\\}")
                '\n' -> sb.append("\\par ")
                '\r' -> {} // ignore
                else -> {
                    // RTF 对非 ASCII 可用 \uN?；这里简单处理常见范围
                    if (ch.code in 0x20..0x7E) sb.append(ch)
                    else sb.append("\\u${ch.code}?")
                }
            }
        }
        return sb.toString()
    }
}
```

---

## 8) 运行与验证

1. 运行 App
2. 点击“选择输出目录”，选一个文件夹（比如 Download 或你自建目录）
3. 输入文件名、字符数量
4. 选择 `.docx` 或 `.doc`
5. 点击生成
6. 用 Word/WPS 打开生成文件确认内容

---

## 可选增强（你需要的话我再给你加）
- 一次生成 N 个文件（批量压力测试）
- 文件名自动递增（test_0001…）
- 支持指定字符集（纯数字/纯字母/包含中文）
- 直接写入“指定绝对路径”（Android 11+ 需要 `MANAGE_EXTERNAL_STORAGE`，仅建议调试机使用）

---

如果你希望“指定目录”是**用户直接输入 `/storage/emulated/0/xxx` 这种路径**而不是 SAF 选目录，告诉我你的 **Android 版本范围（比如 8~14）**，我可以给你两套实现（传统 File API / 全文件访问权限 / MediaStore），并说明各版本限制。

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