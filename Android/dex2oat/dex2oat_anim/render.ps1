# 渲染 dex2oat 带中文旁白动画为 1080p MP4，并合成完整合集。
# 用法：在本目录执行  ./render.ps1
# 依赖：manim 0.20.x + manim-voiceover；离线中文配音用 vo_service.py(pwsh + System.Speech / Huihui)
$ErrorActionPreference = "Stop"
$scenes = @('Scene1_Overview','Scene2_Phases','Scene3_Parallel','Scene4_WatchDog')

# 如需重新合成配音，取消下一行注释清掉配音缓存（否则复用已生成的 wav，更快）
# Get-ChildItem -Recurse -Directory -Filter voiceovers | Remove-Item -Recurse -Force

# 渲染（-qh = 1080p60；改 -ql 可快速预览，-qk 出 4K）
py -m manim render -qh --disable_caching dex2oat_scenes.py @scenes

# 整理输出
$src = "media/videos/dex2oat_scenes/1080p60"
New-Item -ItemType Directory -Force output | Out-Null
Copy-Item "$src/Scene1_Overview.mp4"  "output/01_总览-管线与触发场景_旁白版.mp4"  -Force
Copy-Item "$src/Scene2_Phases.mp4"    "output/02_编译主流程各阶段_旁白版.mp4"      -Force
Copy-Item "$src/Scene3_Parallel.mp4"  "output/03_并行编译模型与挂死_旁白版.mp4"    -Force
Copy-Item "$src/Scene4_WatchDog.mp4"  "output/04_看门狗与超时_旁白版.mp4"          -Force

# 合成完整合集
$list = $scenes | ForEach-Object { "file '$src/$_.mp4'" }
$list | Set-Content -Encoding ascii concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy "output/00_dex2oat编译原理_完整合集_旁白版.mp4"
Write-Host "完成，见 output/ 目录" -ForegroundColor Green
