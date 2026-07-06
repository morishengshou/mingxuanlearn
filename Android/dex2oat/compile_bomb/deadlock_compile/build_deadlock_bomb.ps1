# 编译死锁炸弹 smali -> dex 并部署到设备触发
# 用法：在 D:\Android12 执行  .\build_deadlock_bomb.ps1
# 前置条件：smali.jar 在 PATH 或 AOSP prebuilts 中；adb 已连接 Android 12 设备

param(
    [string]$SmaliJar = "",    # smali.jar 路径，留空则自动查找
    [int]$Threads = 8,         # dex2oat 并行线程数
    [int]$WatchdogMs = 600000  # 看门狗超时（ms），默认 10 分钟
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- 1. 生成 smali 文件 ---
Write-Host "[1/4] 生成 smali 文件..." -ForegroundColor Cyan
py gen_deadlock_bomb.py
$smaliCount = (Get-ChildItem smali -Filter *.smali).Count
Write-Host "  生成 $smaliCount 个 smali 文件" -ForegroundColor Green

# --- 2. 查找 smali.jar ---
if ($SmaliJar -and (Test-Path $SmaliJar)) {
    # 用户指定了，直接用
} else {
    # 自动查找：AOSP prebuilts > 当前目录 > 下载
    $candidates = @(
        (Resolve-Path "$env:ANDROID_BUILD_TOP\prebuilts\build-tools\common\framework\smali.jar" -ErrorAction SilentlyContinue),
        (Resolve-Path "$PSScriptRoot\smali.jar" -ErrorAction SilentlyContinue),
        (Get-Command smali -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

    if ($candidates) {
        $SmaliJar = $candidates
    } else {
        Write-Host "未找到 smali.jar。尝试从 GitHub 下载..." -ForegroundColor Yellow
        $url = "https://github.com/google/smali/releases/download/v3.0.5/smali-3.0.5.jar"
        try {
            Invoke-WebRequest -Uri $url -OutFile "smali.jar" -TimeoutSec 30
            $SmaliJar = "smali.jar"
        } catch {
            Write-Host "下载失败，请手动指定 smali.jar 路径：.\build_deadlock_bomb.ps1 -SmaliJar <path>" -ForegroundColor Red
            exit 1
        }
    }
}
Write-Host "[2/4] smali.jar: $SmaliJar" -ForegroundColor Green

# --- 3. 编译 dex ---
Write-Host "[3/4] 编译 smali -> deadlock_bomb.dex..." -ForegroundColor Cyan
$dex = "deadlock_bomb.dex"
Remove-Item $dex -Force -ErrorAction SilentlyContinue
& java -jar $SmaliJar assemble smali/ -o $dex
if ($LASTEXITCODE -ne 0) {
    Write-Host "smali 编译失败 (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
$dexSize = (Get-Item $dex).Length / 1KB
Write-Host "  生成 $dex ($([math]::Round($dexSize,1)) KB)" -ForegroundColor Green

# --- 4. 部署并触发 ---
Write-Host "[4/4] 部署到设备并触发..." -ForegroundColor Cyan
$devicePath = "/data/local/tmp/deadlock_bomb.dex"
$oatPath = "/data/local/tmp/deadlock_bomb.oat"

# 检查 adb
$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    Write-Host "未找到 adb，请手动执行以下命令：" -ForegroundColor Yellow
    Write-Host "  adb push $dex $devicePath"
    Write-Host "  adb shell dex2oat --dex-file=$devicePath --oat-file=$oatPath --compiler-filter=speed -j$Threads --watchdog-timeout=$WatchdogMs"
    exit 0
}

# 推送 dex
adb push $dex $devicePath
if ($LASTEXITCODE -ne 0) {
    Write-Host "adb push 失败" -ForegroundColor Red
    exit 1
}

# 执行 dex2oat
Write-Host ""
Write-Host "======================================"  -ForegroundColor DarkYellow
Write-Host "  开始触发死锁炸弹"  -ForegroundColor DarkYellow
Write-Host "  线程数: $Threads"  -ForegroundColor DarkYellow
Write-Host "  看门狗: $($WatchdogMs/1000)s"  -ForegroundColor DarkYellow
Write-Host "  预期：10 分钟内 dex2oat 挂死 → 看门狗 Fatal exit(1)"  -ForegroundColor DarkYellow
Write-Host "  同时开另一个终端执行："  -ForegroundColor DarkYellow
Write-Host "    adb shell top -H -p `$(pidof dex2oat)"  -ForegroundColor DarkYellow
Write-Host "    adb shell debuggerd -b `$(pidof dex2oat)"  -ForegroundColor DarkYellow
Write-Host "======================================"  -ForegroundColor DarkYellow
Write-Host ""

$cmd = "dex2oat --dex-file=$devicePath --oat-file=$oatPath --compiler-filter=speed -j$Threads --watchdog-timeout=$WatchdogMs"
Write-Host "执行: adb shell $cmd" -ForegroundColor White
adb shell $cmd

$exitCode = $LASTEXITCODE
Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "dex2oat 正常完成（未触发死锁，可尝试增加线程数 -Threads 16）" -ForegroundColor Yellow
} else {
    Write-Host "dex2oat 异常退出 (exit $exitCode)" -ForegroundColor Red
    Write-Host "如果是看门狗超时，logcat 中应有：" -ForegroundColor Red
    Write-Host "  'dex2oat did not finish after $WatchdogMs milliseconds'" -ForegroundColor Red
}
