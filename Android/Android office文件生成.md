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

# Java版本B1方案
下面给你一套 **Android 12（S/API 31）** 用 **Java + build.gradle（Groovy）** 实现的 **B1 方案**：  
**用户输入绝对路径（或从预置路径下拉选择）→ 使用 `File` API 直接在该目录生成 `.docx` / `.doc` 文件**，用于**调试压测**，并尽可能覆盖更多存储路径。

> 关键点：Android 12 要想“随便写 `/storage/...` 的绝对路径”，基本必须用 **`MANAGE_EXTERNAL_STORAGE`（所有文件访问权限）**。此权限 Play 上架限制非常严，仅适合你说的“调试压测”。

---

## 0) Android 12 限制说明（B1 方案真实边界）

即使有 `MANAGE_EXTERNAL_STORAGE`：

- ✅ 通常可读写：
  - `/storage/emulated/0/...`（主共享存储）
  - `/storage/<XXXX-XXXX>/...`（可移除 SD 卡，若设备有）
  - 大多数公共目录（Download/Documents/Pictures 等）
  - 很多机型上也可访问 `/storage/emulated/0/Android/data/其它包/`（但不同 ROM 可能更严）
- ❌ 仍然不能随意访问：
  - `/data/`、`/system/` 等系统受保护分区（除非 root）
  - 某些厂商定制的受限挂载点
- ⚠️ 路径覆盖“更多”的实践做法：
  - 运行时扫描 `/storage/` 下的挂载卷（如 `emulated`, `self`, `XXXX-XXXX`）
  - 允许手动输入任意绝对路径
  - 预置常见目录一键填充（Download/Documents/DCIM/Android/data 等）

---

## 1) Gradle（Groovy）配置

### `app/build.gradle`
```groovy
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.example.wordstress'
    compileSdk 35

    defaultConfig {
        applicationId "com.example.wordstress"
        minSdk 21
        targetSdk 31   // 你指定 Android 12；也可以更高，但逻辑不变
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        debug {
            debuggable true
            minifyEnabled false
        }
        release {
            // 压测调试用也可不混淆；如要 release 安装，建议也关闭
            minifyEnabled false
            debuggable false
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_11
        targetCompatibility JavaVersion.VERSION_11
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.7.0'
    implementation 'com.google.android.material:material:1.12.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.2.0'
}
```

### `gradle.properties`（可选，提升大文件写入性能/稳定性）
```properties
org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8
android.useAndroidX=true
```

---

## 2) Manifest：开启“所有文件访问权限”

### `src/main/AndroidManifest.xml`
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.wordstress">

    <!-- 核心：Android 11+ 特殊权限（需要用户去设置页手动开） -->
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />

    <!-- 可选：历史权限（Android 12 上基本不起作用，但对更低版本/某些机型调试不碍事）
         注意：如果你坚持仅 Android 12，可不加 -->
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28"/>

    <application
        android:label="WordStress"
        android:allowBackup="true"
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

## 3) 页面布局：绝对路径输入 + 预置路径下拉 + 文件大小/数量参数

### `res/layout/activity_main.xml`
```xml
<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="16dp">

        <Button
            android:id="@+id/btnGrant"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="授予所有文件访问权限(跳转设置)" />

        <TextView
            android:id="@+id/tvPerm"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="权限状态：unknown"
            android:paddingTop="8dp"/>

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="预置路径（尽可能覆盖常见挂载点）"
            android:paddingTop="12dp"/>

        <Spinner
            android:id="@+id/spPaths"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"/>

        <EditText
            android:id="@+id/etDir"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="输出目录绝对路径，例如 /storage/emulated/0/Download/word_demo"
            android:inputType="text"
            android:paddingTop="8dp"/>

        <EditText
            android:id="@+id/etBaseName"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="文件名前缀，例如 stress"
            android:inputType="text"/>

        <EditText
            android:id="@+id/etFileCount"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="生成文件数量，例如 10"
            android:inputType="number"/>

        <EditText
            android:id="@+id/etCharCount"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:hint="每个文件字符数量，例如 100000"
            android:inputType="number"/>

        <RadioGroup
            android:id="@+id/rgExt"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:paddingTop="8dp">

            <RadioButton
                android:id="@+id/rbDocx"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:checked="true"
                android:text=".docx"/>

            <RadioButton
                android:id="@+id/rbDoc"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text=".doc (RTF内容)"/>
        </RadioGroup>

        <Button
            android:id="@+id/btnRun"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="开始生成(压测)" />

        <TextView
            android:id="@+id/tvLog"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="日志"
            android:paddingTop="12dp"/>
    </LinearLayout>
</ScrollView>
```

---

## 4) Java 代码（核心）：权限检查 + 多路径覆盖 + 生成 doc/docx（流式写入，避免 OOM）

### `MainActivity.java`
```java
package com.example.wordstress;

import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {

    private Button btnGrant, btnRun;
    private TextView tvPerm, tvLog;
    private Spinner spPaths;
    private EditText etDir, etBaseName, etFileCount, etCharCount;
    private RadioButton rbDocx, rbDoc;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        btnGrant = findViewById(R.id.btnGrant);
        btnRun = findViewById(R.id.btnRun);
        tvPerm = findViewById(R.id.tvPerm);
        tvLog = findViewById(R.id.tvLog);
        spPaths = findViewById(R.id.spPaths);
        etDir = findViewById(R.id.etDir);
        etBaseName = findViewById(R.id.etBaseName);
        etFileCount = findViewById(R.id.etFileCount);
        etCharCount = findViewById(R.id.etCharCount);
        rbDocx = findViewById(R.id.rbDocx);
        rbDoc = findViewById(R.id.rbDoc);

        etBaseName.setText("stress");
        etFileCount.setText("5");
        etCharCount.setText("100000");

        // 构建“尽可能覆盖更多”的路径列表
        List<String> paths = StoragePaths.collectLikelyPaths(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, paths);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spPaths.setAdapter(adapter);

        // 默认填充第一项（通常是 /storage/emulated/0/Download/...）
        if (!paths.isEmpty()) {
            etDir.setText(paths.get(0));
        }

        spPaths.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, android.view.View view, int position, long id) {
                etDir.setText(paths.get(position));
            }
            @Override public void onNothingSelected(AdapterView<?> parent) {}
        });

        btnGrant.setOnClickListener(v -> openAllFilesAccessSettings());
        btnRun.setOnClickListener(v -> runGenerate());

        refreshPermStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshPermStatus();
    }

    private void refreshPermStatus() {
        boolean ok = Environment.isExternalStorageManager();
        tvPerm.setText("权限状态：MANAGE_EXTERNAL_STORAGE = " + ok);
    }

    private void openAllFilesAccessSettings() {
        try {
            Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
            intent.setData(Uri.parse("package:" + getPackageName()));
            startActivity(intent);
        } catch (ActivityNotFoundException e) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION);
            startActivity(intent);
        }
        toast("请在设置中打开“所有文件访问权限”，返回后再开始生成");
    }

    private void runGenerate() {
        if (!Environment.isExternalStorageManager()) {
            toast("未授予所有文件访问权限");
            openAllFilesAccessSettings();
            return;
        }

        String dirPath = etDir.getText().toString().trim();
        if (dirPath.isEmpty()) { toast("请输入输出目录绝对路径"); return; }

        String base = etBaseName.getText().toString().trim();
        if (base.isEmpty()) { toast("请输入文件名前缀"); return; }

        int fileCount;
        long charCount;
        try {
            fileCount = Integer.parseInt(etFileCount.getText().toString().trim());
            charCount = Long.parseLong(etCharCount.getText().toString().trim());
        } catch (Exception e) {
            toast("数量输入不合法");
            return;
        }

        if (fileCount <= 0) { toast("文件数量需 > 0"); return; }
        if (charCount < 0) { toast("字符数量需 >= 0"); return; }

        boolean docx = rbDocx.isChecked();
        String ext = docx ? "docx" : "doc";

        File dir = new File(dirPath);
        if (!dir.exists() && !dir.mkdirs()) {
            log("目录创建失败: " + dir.getAbsolutePath());
            toast("目录创建失败");
            return;
        }
        if (!dir.isDirectory()) {
            log("不是目录: " + dir.getAbsolutePath());
            toast("不是目录");
            return;
        }

        // 压测：循环生成多个文件
        long start = System.currentTimeMillis();
        int ok = 0;
        for (int i = 1; i <= fileCount; i++) {
            String name = base + "_" + System.currentTimeMillis() + "_" + i + "." + ext;
            File out = new File(dir, name);

            try {
                if (docx) {
                    WordWriters.writeDocxRandom(out, charCount);
                } else {
                    WordWriters.writeDocRtfRandom(out, charCount);
                }
                ok++;
            } catch (Exception e) {
                log("生成失败: " + out.getAbsolutePath() + "\n" + e);
                // 不中断：继续压测
            }
        }
        long cost = System.currentTimeMillis() - start;
        log("完成：成功 " + ok + "/" + fileCount +
                "\n目录=" + dir.getAbsolutePath() +
                "\n每文件字符数=" + charCount +
                "\n耗时(ms)=" + cost);
        toast("完成，成功 " + ok + "/" + fileCount);
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_SHORT).show();
    }

    private void log(String s) {
        tvLog.setText(s);
    }
}
```

---

### `StoragePaths.java`（尽可能覆盖更多可写路径：主存储 + 公共目录 + /storage 扫描 + SD 卡）
```java
package com.example.wordstress;

import android.content.Context;
import android.os.Environment;

import java.io.File;
import java.util.*;

public final class StoragePaths {

    private StoragePaths(){}

    public static List<String> collectLikelyPaths(Context ctx) {
        LinkedHashSet<String> set = new LinkedHashSet<>();

        // 1) 主共享存储（传统常见）
        set.add("/storage/emulated/0/Download/word_stress");
        set.add("/storage/emulated/0/Documents/word_stress");
        set.add("/storage/emulated/0/word_stress");
        set.add("/sdcard/Download/word_stress");   // 有的机型仍有这个软链接
        set.add("/sdcard/word_stress");

        // 2) Environment 公共目录（仍返回主共享存储路径）
        tryAdd(set, new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "word_stress"));
        tryAdd(set, new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS), "word_stress"));
        tryAdd(set, new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM), "word_stress"));

        // 3) App 专属（即使不需要也提供一个“肯定能写”的兜底）
        File appExt = ctx.getExternalFilesDir(null);
        if (appExt != null) tryAdd(set, new File(appExt, "word_stress"));

        // 4) 扫描 /storage 下的卷（可移除 SD 卡一般是 /storage/XXXX-XXXX）
        scanAndAdd(set, new File("/storage"));

        // 5) 某些设备还有 /mnt/media_rw（可移除卷真实挂载点）
        scanAndAdd(set, new File("/mnt/media_rw"));

        return new ArrayList<>(set);
    }

    private static void scanAndAdd(Set<String> set, File root) {
        File[] children = root.listFiles();
        if (children == null) return;
        for (File f : children) {
            if (f == null) continue;
            String name = f.getName();
            // 跳过明显无用项
            if ("emulated".equalsIgnoreCase(name) || "self".equalsIgnoreCase(name)) continue;
            // 尝试把每个卷都加上常见子目录
            tryAdd(set, new File(f, "Download/word_stress"));
            tryAdd(set, new File(f, "Documents/word_stress"));
            tryAdd(set, new File(f, "word_stress"));
        }
    }

    private static void tryAdd(Set<String> set, File file) {
        if (file == null) return;
        set.add(file.getAbsolutePath());
    }
}
```

---

### `WordWriters.java`（流式写入：不把随机文本全部放内存）
```java
package com.example.wordstress;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public final class WordWriters {
    private WordWriters(){}

    public static void writeDocRtfRandom(File outFile, long charCount) throws IOException {
        // 这里写的是 RTF 内容，但文件扩展名用 .doc（Word/WPS 可打开，适合压测）
        try (OutputStream os = new BufferedOutputStream(new FileOutputStream(outFile, false))) {
            String header = "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}\\fs22\n";
            os.write(header.getBytes(StandardCharsets.UTF_8));

            RandomTextStreamer.writeRtfText(os, charCount);

            String tail = "\n}";
            os.write(tail.getBytes(StandardCharsets.UTF_8));
        }
    }

    public static void writeDocxRandom(File outFile, long charCount) throws IOException {
        try (OutputStream fos = new BufferedOutputStream(new FileOutputStream(outFile, false));
             ZipOutputStream zip = new ZipOutputStream(fos)) {

            // [Content_Types].xml
            zip.putNextEntry(new ZipEntry("[Content_Types].xml"));
            zip.write(DocxTemplates.contentTypesXml().getBytes(StandardCharsets.UTF_8));
            zip.closeEntry();

            // _rels/.rels
            zip.putNextEntry(new ZipEntry("_rels/.rels"));
            zip.write(DocxTemplates.relsXml().getBytes(StandardCharsets.UTF_8));
            zip.closeEntry();

            // word/_rels/document.xml.rels
            zip.putNextEntry(new ZipEntry("word/_rels/document.xml.rels"));
            zip.write(DocxTemplates.wordDocumentRelsXml().getBytes(StandardCharsets.UTF_8));
            zip.closeEntry();

            // word/document.xml（流式写入正文）
            zip.putNextEntry(new ZipEntry("word/document.xml"));
            OutputStreamWriter w = new OutputStreamWriter(zip, StandardCharsets.UTF_8);

            w.write(DocxTemplates.documentXmlHeader());

            // 每段写 800 字符，写成多段落，避免极端超长 run
            RandomTextStreamer.writeDocxBody(w, charCount, 800);

            w.write(DocxTemplates.documentXmlFooter());
            w.flush();

            zip.closeEntry();
        }
    }
}
```

---

### `DocxTemplates.java`
```java
package com.example.wordstress;

public final class DocxTemplates {
    private DocxTemplates(){}

    public static String contentTypesXml() {
        return ""
            + "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            + "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n"
            + "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n"
            + "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n"
            + "  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\n"
            + "</Types>\n";
    }

    public static String relsXml() {
        return ""
            + "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
            + "  <Relationship Id=\"rId1\"\n"
            + "    Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\"\n"
            + "    Target=\"word/document.xml\"/>\n"
            + "</Relationships>\n";
    }

    public static String wordDocumentRelsXml() {
        return ""
            + "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n"
            + "</Relationships>\n";
    }

    public static String documentXmlHeader() {
        return ""
            + "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
            + "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\n"
            + "  <w:body>\n";
    }

    public static String documentXmlFooter() {
        return ""
            + "    <w:sectPr/>\n"
            + "  </w:body>\n"
            + "</w:document>\n";
    }
}
```

---

### `RandomTextStreamer.java`（随机字符流式生成：高性能、可压测大文件）
```java
package com.example.wordstress;

import java.io.IOException;
import java.io.OutputStream;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;

public final class RandomTextStreamer {

    // 为了避免 docx XML 转义成本，字符集刻意不包含 < > & " '
    private static final char[] ALPHABET = (
            "abcdefghijklmnopqrstuvwxyz" +
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
            "0123456789" +
            "     "   // 增加空格概率
    ).toCharArray();

    private static final SecureRandom RND = new SecureRandom();

    private RandomTextStreamer(){}

    public static void writeRtfText(OutputStream os, long charCount) throws IOException {
        // RTF 里换段用 \par；这里每 1000 字符插一个 \par
        byte[] par = "\\par\n".getBytes(StandardCharsets.UTF_8);
        byte[] buf = new byte[16 * 1024];

        long remaining = charCount;
        long sincePar = 0;

        while (remaining > 0) {
            int n = (int) Math.min(remaining, buf.length);
            for (int i = 0; i < n; i++) {
                char c = ALPHABET[RND.nextInt(ALPHABET.length)];
                buf[i] = (byte) c; // 仅 ASCII
            }
            os.write(buf, 0, n);

            remaining -= n;
            sincePar += n;

            if (sincePar >= 1000 && remaining > 0) {
                os.write(par);
                sincePar = 0;
            }
        }
    }

    public static void writeDocxBody(Writer w, long charCount, int paragraphSize) throws IOException {
        // 以多个段落写入：<w:p><w:r><w:t xml:space="preserve"> ... </w:t></w:r></w:p>
        long remaining = charCount;

        if (remaining <= 0) {
            w.write("    <w:p><w:r><w:t xml:space=\"preserve\"></w:t></w:r></w:p>\n");
            return;
        }

        char[] chunk = new char[Math.max(256, Math.min(paragraphSize, 8192))];

        while (remaining > 0) {
            int toWrite = (int) Math.min(remaining, chunk.length);

            for (int i = 0; i < toWrite; i++) {
                chunk[i] = ALPHABET[RND.nextInt(ALPHABET.length)];
            }

            w.write("    <w:p><w:r><w:t xml:space=\"preserve\">");
            w.write(chunk, 0, toWrite);
            w.write("</w:t></w:r></w:p>\n");

            remaining -= toWrite;
        }
    }
}
```

---

## 5) 如何“尽快授予极高权限”（调试压测常用）

### 方式 1：App 内按钮跳设置页（已实现）
点击“授予所有文件访问权限(跳转设置)”→ 打开 → 返回即可。

### 方式 2：ADB（有些机型可用，适合批量测试机）
```bash
adb shell appops set --uid com.example.wordstress MANAGE_EXTERNAL_STORAGE allow
```
然后重启 App 再看 `Environment.isExternalStorageManager()` 是否为 true。  
> 不同 ROM 对 appops 支持不完全；不生效就用方式 1。

---

## 6) 你要“覆盖更多路径选择”的进一步增强（如需要我可继续补）
当前已做到：
- 预置主存储常见目录
- 扫描 `/storage`、`/mnt/media_rw` 下卷并追加候选
- 允许手工输入任意绝对路径

如果你还想更极限一点（压测定位问题）：
- 增加“递归创建多级深路径”“并发生成（多线程）”“文件大小从 1KB~1GB 梯度”
- 输出落盘性能统计（吞吐 MB/s、失败路径列表、异常分类 EACCES/ENOSPC 等）

你告诉我：压测希望 **单文件最大字符数**、**并发线程数**、以及是否需要 **生成到 SD 卡根目录**（`/storage/XXXX-XXXX/`），我可以把并发与统计也补全。

