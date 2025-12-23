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