# dex2oat 编译原理动画 — 制作与渲染指南

> 基于源码 `art/dex2oat` 的 4 场景 Manim 动画 + 中文离线旁白。
> 目标：在另一台 Windows 机器上复现完整渲染流程。

---

## 目录

1. [环境要求](#1-环境要求)
2. [文件清单与职责](#2-文件清单与职责)
3. [快速开始（5 分钟）](#3-快速开始5-分钟)
4. [详细步骤](#4-详细步骤)
5. [配音管线原理](#5-配音管线原理)
6. [自定义修改](#6-自定义修改)
7. [踩过的坑与解决方案](#7-踩过的坑与解决方案)
8. [命令参考](#8-命令参考)

---

## 1. 环境要求

### 必须

| 组件 | 最低版本 | 验证命令 |
|------|---------|---------|
| Windows 10/11 | — | — |
| **PowerShell 7** (pwsh) | 7.x | `pwsh -v` |
| Python | 3.10+ | `python --version` |
| pip | 随 Python | `python -m pip --version` |
| ffmpeg | 4.x+ | `ffmpeg -version` |

### Python 包

```bash
pip install manim manim-voiceover
# manim-voiceover 的 pyttsx3/sox 依赖会一并安装，但我们的配音方案不依赖它们。
```

### 中文语音（离线，必须）

本方案使用 **Windows SAPI** 的微软慧慧（zh-CN）音色，不依赖联网或第三方 TTS 引擎。

验证音色存在：

```powershell
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }
```

预期输出中必须包含：

```
Microsoft Huihui Desktop
```

> 如果缺这个音色：在 Windows 设置 → 时间和语言 → 语言 → 中文(简体) → 选项 → 语音包，安装中文语音包。

### 确认 pwsh 位置

配音脚本依赖 PowerShell 7 的可执行文件。确认路径：

```powershell
(Get-Command pwsh).Source
# 预期：C:\Program Files\PowerShell\7\pwsh.exe
```

如果你的 pwsh 在别处，需要修改 [`vo_service.py`](vo_service.py) 第 17 行的 `_PWSH` 变量。

---

## 2. 文件清单与职责

```
dex2oat_anim/
├── README.md                    # ← 本文档
├── dex2oat_scenes.py            # ★ 核心：4 个 Manim 场景脚本
├── vo_service.py                # 离线中文配音服务（SAPI + pwsh）
├── tts.ps1                      # 单句 TTS 合成器（被 vo_service.py 调用）
├── render.ps1                   # 一键渲染脚本
└── output/                      # 渲染好的 MP4 成品
    ├── 00_dex2oat编译原理_完整合集.mp4
    ├── 01_总览-管线与触发场景.mp4
    ├── 02_编译主流程各阶段.mp4
    ├── 03_并行编译模型与挂死.mp4
    └── 04_看门狗与超时.mp4
```

### 各文件详细说明

#### `dex2oat_scenes.py` — 场景脚本

包含 4 个 `VoiceoverScene` 子类：

| 类名 | 内容 | 对应源码行号 |
|------|------|-------------|
| `Scene1_Overview` | dex2oat 输入/输出/触发场景 | `dex2oat.cc:3182` |
| `Scene2_Phases` | 主流程 5 阶段 + Compile 内部展开 | `dex2oat.cc:1831` / `compiler_driver.cc:762` |
| `Scene3_Parallel` | 线程池 + 原子游标 + 挂死演示 | `compiler_driver.cc:1397/1414` |
| `Scene4_WatchDog` | 看门狗时间线 + 华为限速场景 | `dex2oat.cc:280/344` |

每个旁白段落使用 `with self.voiceover(text="..."):` 语法，文本嵌入在场景代码中。

辅助函数（可复用）：

- `cn(text, size, color)` — 创建微软雅黑中文 `Text` 对象
- `code(text, size, color)` — 创建 Consolas 等宽 `Text` 对象（用于代码引用）
- `box(label, w, h, fill, ...)` — 创建圆角矩形 + 居中标签的 `VGroup`
- `footnote(text)` — 创建底部灰色小字注释

配色方案（文件顶部常量）：

- `C_DEX = "#4FC3F7"` — 输入 dex（蓝）
- `C_TOOL = "#FFB74D"` — dex2oat 工具（橙）
- `C_OAT = "#81C784"` — 产物（绿）
- `C_PHASE = "#64B5F6"` — 阶段框
- `C_HOT = "#E57373"` — 热路径/危险（红）
- `C_HL = "#FFD54F"` — 高亮黄

#### `vo_service.py` — 配音服务

实现类 `SapiZhService(SpeechService)`，核心逻辑：

```
场景脚本 → with self.voiceover(text="...") →
  SapiZhService.generate_from_text() →
    1) 旁白文本写入 UTF-8(BOM) 临时文件
    2) 启动独立 pwsh 进程执行 tts.ps1，合成 WAV
    3) 读取 WAV 时长，返回给 manim-voiceover
    4) manim-voiceover 自动将 WAV 混入 MP4 音轨
```

关键参数：

- `make_zh_service(rate=1)` 中 `rate` 取值 -10..10，0=默认，正值=更快。

#### `tts.ps1` — TTS 合成器

独立 PowerShell 脚本，每次调用合成一句话。参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `-InFile` | 输入 UTF-8 文本文件 | `_t.txt` |
| `-OutFile` | 输出 WAV 路径 | `media/voiceovers/xxx.wav` |
| `-Rate` | 语速 -10..10 | `1` |
| `-Voice` | 音色名称 | `"Microsoft Huihui Desktop"` |

#### `render.ps1` — 一键渲染

带旁白渲染 + 合成合集，内部调 `manim render -qh`（1080p60）。

---

## 3. 快速开始（5 分钟）

```powershell
# 1) 安装依赖
pip install manim manim-voiceover

# 2) 进入目录
cd D:\Android12\dex2oat_anim

# 3) 一键渲染（1080p60，约 15-30 分钟）
.\render.ps1

# 4) 查看成品
ls output\
```

---

## 4. 详细步骤

### 4.1 首次渲染

首次渲染会执行以下流程：

1. **合成配音**：每个 `voiceover(text=...)` 段落触发一次 `tts.ps1` 生成一个 `.wav`，约 2-3 秒/句。全部 wav 缓存到 `media/voiceovers/`。
2. **渲染动画**：manim 逐帧渲染每个场景，同时将配音 wav 混合为 aac 音轨。
3. **整理输出**：4 个分场景 MP4 + 1 个合集 MP4 写入 `output/`。

总耗时约 **15-30 分钟**（取决于 CPU）。

### 4.2 二次渲染

如果只改了动画排版（未改旁白文本），配音缓存可复用，耗时约 **8-15 分钟**。

如果改了旁白文本，需要清除配音缓存让引擎重新合成：

```powershell
Remove-Item -Recurse -Force media\voiceovers
```

### 4.3 只渲染单个场景（调试用）

```bash
# 低质量快速预览（480p）
python -m manim render -ql --disable_caching dex2oat_scenes.py Scene1_Overview

# 1080p
python -m manim render -qh --disable_caching dex2oat_scenes.py Scene1_Overview
```

### 4.4 手动合成合集

```bash
cd media/videos/dex2oat_scenes/1080p60
printf "file '%s'\n" Scene1_Overview.mp4 Scene2_Phases.mp4 Scene3_Parallel.mp4 Scene4_WatchDog.mp4 > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy ../../../output/00_合集.mp4
```

---

## 5. 配音管线原理

### 为什么不用 pyttsx3 直接合成？

`pyttsx3` 在同一 Python 进程内反复调用 `runAndWait()` 会造成 **Windows SAPI 死锁**——合成 3-4 句后就卡住，进程 CPU 时间归零但永不退出。

我们的方案：**每句旁白起一个独立的 `pwsh` 进程**，进程结束后 SAPI 资源被 OS 回收，彻底避免死锁。

### 为什么必须用 PowerShell 7 而不是 Windows PowerShell 5.1？

Windows PowerShell 5.1 的 `Add-Type -AssemblyName System.Speech` 在 Python 的 `subprocess` 环境中**加载不到 System.Speech 程序集**。

PowerShell 7 (`pwsh`) 已修复此问题。

### 配音缓存机制

`manim-voiceover` 以 `{文本内容, 服务名, 语速}` 为 key 缓存 wav。同内容第二次渲染秒出。缓存位于 `media/voiceovers/`，可安全删除（下次自动重建）。

### 音轨混合

`manim-voiceover` 在渲染最后阶段调用 ffmpeg，将合成的 WAV 音轨与无声 MP4 视频流合并，输出带 aac 音轨的最终 MP4。

---

## 6. 自定义修改

### 6.1 调整语速

修改 [`vo_service.py`](vo_service.py) 第 63 行：

```python
def make_zh_service(rate: int = 1):   # 改为 -2(更慢) 或 3(更快)
```

或者在场景脚本中传入：

```python
self.set_speech_service(make_zh_service(rate=2))
```

### 6.2 修改旁白文本

在 [`dex2oat_scenes.py`](dex2oat_scenes.py) 中找到对应场景的 `voiceover(text=...)` 语句，直接改字符串。注意：

- 每句末尾不要加英文句号 `.`（SAPI 中文引擎会读出"点"）。
- 使用中文标点 `，。`。
- 一长段可以拆成多行 Python 字符串拼接，不影响合成结果。
- 改完后必须清除配音缓存：`Remove-Item -Recurse -Force media/voiceovers`

### 6.3 更换音色

修改 [`vo_service.py`](vo_service.py) 第 15 行 `ZH_VOICE_NAME`：

```python
ZH_VOICE_NAME = "Microsoft Huihui Desktop"  # 微软慧慧
# 可选的其它中文音色（取决于系统安装）：
# "Microsoft Kangkang Desktop"   # 微软康康（男声）
# "Microsoft Yaoyao Desktop"     # 微软瑶瑶
```

### 6.4 调整动画排版

所有 Manim 对象位置都用相对定位（`next_to`、`to_edge`、`arrange`、`shift`），修改单个坐标不影响整体。

常见操作：

```python
# 增大间距：改 buff
VGroup(a, b).arrange(DOWN, buff=0.35)   # 原来 0.25

# 整体左移：改 shift
rows.shift(LEFT * 1.3)                   # 原来 0.2

# 缩短框：改 w
box(label, w=6.2, h=0.78, tsize=21)    # w 缩小
```

修改后渲染 480p 预览快速看效果：

```bash
python -m manim render -ql --disable_caching dex2oat_scenes.py Scene1_Overview
```

### 6.5 添加新场景

按现有模式在 `dex2oat_scenes.py` 末尾添加新类：

```python
class Scene5_MyNewScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(make_zh_service())
        title = cn("我的新场景", size=38, color=C_HL).to_edge(UP, buff=0.35)
        with self.voiceover(text="这是配音文本。"):
            self.play(Write(title))
        self.wait(0.5)
```

然后在 `render.ps1` 的 `$scenes` 数组里加上 `'Scene5_MyNewScene'`。

---

## 7. 踩过的坑与解决方案

### 坑 1：pyttsx3 死锁（最严重）

**现象**：渲染到第 3-4 句旁白后卡死，Python CPU 时间归零，进程永不退出。

**根因**：pyttsx3 在同进程反复 `runAndWait()`，Windows SAPI COM 引擎挂起。

**解决**：放弃 pyttsx3，改用每句独立 `pwsh` 进程合成 WAV。见 `vo_service.py` + `tts.ps1`。

### 坑 2：NumberLine 触发 LaTeX

**现象**：`NumberLine(include_numbers=True)` 报 `FileNotFoundError` 找不到 tex。

**根因**：manim 的数字刻度用 LaTeX 渲染，而 Windows 通常没装 LaTeX。

**解决**：Scene4 用纯 `Line` + `Text` 手工画坐标轴，全程零 LaTeX 依赖。

### 坑 3：LaggedStartMap 参数错误

**现象**：`LaggedStartMap(lambda m: ..., items)` 报 `takes 1 positional argument but 2 were given`。

**根因**：manim 0.20.x 的 `LaggedStartMap` 会把 item 和 index 都传给回调。

**解决**：改用 `LaggedStart(*[FadeIn(m, ...) for m in items], lag_ratio=...)` 显式构造。

### 坑 4：manim-voiceover 的 pyttsx3 服务写 WAV 但命名 .mp3

**现象**：配音能合成但不能混入视频，报 `can't sync to MPEG frame`。

**根因**：`PyTTSX3Service.generate_from_text()` 调 `save_to_file` 输出 WAV 但文件名强制写 `.mp3`，后续 `mutagen.MP3()` 解析失败。

**解决**：自定义 `SapiZhService`，明确用 `.wav` 扩展名。见 `vo_service.py`。

### 坑 5：pwsh 与 powershell 的区别

**现象**：`subprocess.run(["powershell", ...])` 调 tts.ps1 报 `System.Speech.Synthesis.SpeechSynthesizer not found`。

**根因**：`powershell` 是 Windows PowerShell 5.1，`Add-Type -AssemblyName System.Speech` 在其 subprocess 环境中加载失败。

**解决**：指定全路径调用 PowerShell 7：`C:\Program Files\PowerShell\7\pwsh.exe`。

### 坑 6：进度条误判 100%

**现象**：进度条监视器在渲染刚开始就显示 100%。

**根因**：`media/videos/dex2oat_scenes/1080p60/` 目录残留了上一轮渲染的旧 MP4，监视器把它们计数成了"已完成"。

**解决**：每次重新渲染前清空视频目录。`render.ps1` 和快速开始步骤都已体现。

### 坑 7：中文文本在 SAPI 命令行中转义

**现象**：旁白 wav 里念出乱码。

**根因**：命令行传中文参数经过 cmd/pwsh 编码转换可能出错。

**解决**：不在命令行传文本，而是把文本写成 UTF-8(BOM) 临时文件，`tts.ps1` 用 `Get-Content -Encoding UTF8` 读取。见 `vo_service.py` 第 42-44 行。

---

## 8. 命令参考

### 渲染

```bash
# 480p15 快速预览（单个场景）
python -m manim render -ql --disable_caching dex2oat_scenes.py Scene1_Overview

# 720p30（中等质量）
python -m manim render -qm --disable_caching dex2oat_scenes.py Scene1_Overview

# 1080p60（高质量，最终输出用）
python -m manim render -qh --disable_caching dex2oat_scenes.py Scene1_Overview

# 4K60（最高质量，渲染很慢）
python -m manim render -qk --disable_caching dex2oat_scenes.py Scene1_Overview

# 渲染全部 4 个场景（1080p）
python -m manim render -qh --disable_caching dex2oat_scenes.py Scene1_Overview Scene2_Phases Scene3_Parallel Scene4_WatchDog
```

### 调试

```bash
# 检查配音合成是否正常（单句测试）
pwsh -NoProfile -ExecutionPolicy Bypass -File tts.ps1 -InFile <(echo "测试") -OutFile test.wav
ffprobe test.wav

# 检查视频音轨
ffprobe -v error -select_streams a -show_entries stream=codec_name -of default=nw=1:nk=1 output/01_总览-管线与触发场景.mp4
# 预期输出：aac

# 检查视频时长
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 output/01_总览-管线与触发场景.mp4
```

### 清理

```powershell
# 清除配音缓存（改旁白文本后必须执行）
Remove-Item -Recurse -Force media\voiceovers

# 清除视频缓存（改排版后建议执行，避免进度条误判）
Remove-Item -Recurse -Force media\videos\dex2oat_scenes

# 一键清空重新来
Remove-Item -Recurse -Force media
```

---

## 附录：场景时序表（方便定位修改）

| 场景 | 总时长 | 旁白句数 | 主要视觉元素 |
|------|--------|---------|-------------|
| Scene1_Overview | 1'48" | 5 句 | 左右三列（输入/工具/输出）→ 触发三方块 + installd 链 |
| Scene2_Phases | 1'25" | 4 句 | 顶部调用链 → 左侧 5 阶段流水线 → 右侧 Compile 内部面板 |
| Scene3_Parallel | 1'27" | 5 句 | 8 格任务队列 + 原子游标 → 4 worker → 主线程 Wait → worker2 卡死演示 |
| Scene4_WatchDog | 1'30" | 4 句 | 时间轴 + 两条虚线 → 正常 2min 绿条 → 华为限速红条 → 9.5min 爆炸 |
| **合集** | **6'09"** | **18 句** | — |
