# Manim 动画编译（渲染）指导

> 本文档说明如何把 `animations/` 目录下的 Python 脚本渲染成视频/动图，
> 面向**首次使用 Manim** 的开发者。以 Windows 为主，附 macOS / Linux 差异。
>
> 这里的"编译"实际是**渲染**：Manim 读取 `.py` 场景脚本 → 计算每一帧 → 用 ffmpeg 合成 `.mp4`（或 `.gif`）。

---

## 一、Manim 是什么 / 用哪个版本

- Manim 是一个用 **Python 代码描述数学/示意动画**的库。
- 有两个分支：**Manim Community（manim，社区版，推荐）** 和 3b1b 原版（manimgl）。
  本项目脚本基于 **Manim Community v0.18+**，请勿安装 `manimlib`/`manimgl`。

本项目动画脚本（位于 `animations/`）：

| 文件 | 场景类（Scene） | 讲解内容 |
|------|----------------|----------|
| `concept_layers.py` | `LayerLookupOne` / `LayerLookupAll` | 多层查找：最高优先级命中 / 收集所有层 |
| `concept_cfgdir_memory.py` | `CfgDirMemory` | **核心**：CfgDir 的 paths[] 共用一块缓冲的内存原理 |
| `concept_cfgfiles_memory.py` | `CfgFilesMemory` | CfgFiles 每个 paths[i] 独立分配，与 CfgDir 对比 |
| `concept_followx.py` | `FollowXLookup` | Follow-X 运营商子目录插入原理 |

---

## 二、环境准备

### 2.1 前置依赖

| 依赖 | 是否必需 | 说明 |
|------|----------|------|
| Python 3.8+ | 必需 | 本机已是 Python 3.13，满足 |
| Manim Community | 必需 | `pip install manim` |
| ffmpeg | 必需 | 合成视频；Manim 不自带 |
| LaTeX（MiKTeX/TeX Live） | **不需要** | 本项目脚本用 `Text` 而非 `Tex/MathTex`，无需安装 LaTeX |

### 2.2 Windows 安装步骤

```powershell
# 1) 安装 ffmpeg（任选其一）
winget install Gyan.FFmpeg
#   或： scoop install ffmpeg
#   或： choco install ffmpeg

# 2) 验证 ffmpeg
ffmpeg -version

# 3) 安装 Manim（建议用虚拟环境，见 2.4）
py -m pip install --upgrade pip
py -m pip install manim

# 4) 验证 Manim
py -m manim --version
```

> 若 `winget`/`scoop`/`choco` 都没有，可从 https://www.gyan.dev/ffmpeg/builds/ 下载
> "release full" 压缩包，解压后把其中 `bin` 目录加入系统 PATH，再开新终端验证。

### 2.3 macOS / Linux 安装（参考）

```bash
# macOS
brew install ffmpeg
pip3 install manim

# Ubuntu/Debian
sudo apt update && sudo apt install -y ffmpeg
pip3 install manim
```

### 2.4 推荐：使用虚拟环境（避免污染全局）

```powershell
cd D:\projects\customization_config_policy
py -m venv .venv
.\.venv\Scripts\Activate.ps1      # 激活（PowerShell）
pip install manim
# 之后所有 manim 命令都在此环境内执行；退出用 deactivate
```

> 若 PowerShell 提示"禁止运行脚本"，先执行：
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## 三、渲染命令

### 3.1 基本格式

```
manim [质量/选项] <脚本文件.py> <场景类名>
```

也可用 `py -m manim ...`（等价，避免 PATH 问题）。

### 3.2 常用选项

| 选项 | 含义 |
|------|------|
| `-p` | 渲染完成后自动**预览播放**（preview） |
| `-q l` | 低质量 480p15（快，调试用） |
| `-q m` | 中质量 720p30 |
| `-q h` | 高质量 1080p60（交付用） |
| `-q k` | 4K 2160p60 |
| `-ql` / `-qh` | `-q l` / `-q h` 的简写，可与 `-p` 合并为 `-pqh` |
| `-a` | 渲染该文件中**所有**场景类 |
| `--format gif` | 输出 GIF 而非 mp4 |
| `-s` | 只渲染**最后一帧**为 PNG（快速预览构图） |
| `-o 名称` | 自定义输出文件名 |

### 3.3 针对本项目的渲染命令

在 `animations/` 目录下执行（或把路径写全）：

```powershell
cd D:\projects\customization_config_policy\animations

# 调试预览（低质量、自动播放）——先用这个确认效果
manim -pql concept_cfgdir_memory.py CfgDirMemory

# 交付渲染（1080p60 高质量）
manim -qh concept_layers.py          LayerLookupOne
manim -qh concept_layers.py          LayerLookupAll
manim -qh concept_cfgdir_memory.py   CfgDirMemory
manim -qh concept_cfgfiles_memory.py CfgFilesMemory
manim -qh concept_followx.py         FollowXLookup

# 一次渲染某文件里的所有场景
manim -qh concept_layers.py -a

# 导出 GIF（便于嵌入文档/PPT）
manim -qm concept_followx.py FollowXLookup --format gif

# 只看最后一帧构图（不生成视频，最快）
manim -sql concept_cfgdir_memory.py CfgDirMemory
```

---

## 四、输出文件在哪里

渲染产物默认在脚本同级的 `media/` 目录下：

```
animations/
└── media/
    ├── videos/
    │   └── concept_cfgdir_memory/
    │       └── 1080p60/
    │           └── CfgDirMemory.mp4      ← 视频在这里
    ├── images/                            ← -s 生成的 PNG
    └── Tex/  texts/                       ← 渲染中间产物
```

质量子目录名随 `-q` 变化（`480p15` / `720p30` / `1080p60` / `2160p60`）。
可用 `--media_dir <路径>` 改变输出根目录。

---

## 五、中文字体说明（重要）

脚本顶部定义了 `FONT = "Microsoft YaHei"`，并对路径/代码使用 `"Consolas"`。
这两种字体 Windows 默认自带，无需额外配置。

换平台时请修改各脚本顶部的 `FONT` 常量：

| 平台 | 建议字体 |
|------|----------|
| Windows | `Microsoft YaHei`（微软雅黑） |
| macOS | `PingFang SC` 或 `Heiti SC` |
| Linux | `Noto Sans CJK SC`（需先安装 `fonts-noto-cjk`） |

> 若渲染出的中文是空白方块/豆腐块，说明所选字体不含中文或系统未安装该字体，
> 改成本机已安装的中文字体名即可。可用以下命令查看可用字体：
> ```python
> py -c "from manim import *; import manimpango; print(manimpango.list_fonts())"
> ```

---

## 六、常见问题

### Q1：`manim 不是内部或外部命令`
Manim 的脚本目录未进 PATH。改用 `py -m manim ...`，或重新打开终端 / 检查 pip 安装路径。

### Q2：`Couldn't find ffmpeg` / 视频没生成
ffmpeg 未安装或不在 PATH。执行 `ffmpeg -version` 确认；装好后**重开终端**再渲染。

### Q3：中文显示为方块
见第五节，把 `FONT` 改为本机已安装的中文字体。

### Q4：渲染很慢
- 调试阶段用 `-ql`（低质量）或 `-sql`（只出最后一帧）；
- 确认未误装重型 LaTeX 渲染链（本项目不需要 LaTeX）。

### Q5：`No scenes found` / 场景名错误
场景类名区分大小写，必须与脚本中 `class Xxx(Scene)` 完全一致。
不确定时省略类名运行 `manim file.py`，Manim 会列出可选场景让你选择。

### Q6：PowerShell 无法激活虚拟环境
执行 `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` 后重试。

---

## 七、最小验证流程（建议首次按此走一遍）

```powershell
# 1. 进入项目并建虚拟环境
cd D:\projects\customization_config_policy
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 装依赖
pip install manim
ffmpeg -version          # 确认 ffmpeg 可用

# 3. 低质量预览核心动画（最快看到效果）
cd animations
manim -pql concept_cfgdir_memory.py CfgDirMemory

# 4. 看到效果后，高质量交付渲染
manim -qh concept_cfgdir_memory.py CfgDirMemory
# 产物：animations/media/videos/concept_cfgdir_memory/1080p60/CfgDirMemory.mp4
```

---

## 参考资料

- Manim Community 官方文档：https://docs.manim.community/
- 安装指南：https://docs.manim.community/en/stable/installation.html
- 命令行参数：https://docs.manim.community/en/stable/guides/configuration.html
- 配套动画脚本：本项目 `animations/` 目录
