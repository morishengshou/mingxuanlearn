param(
    [Parameter(Mandatory=$true)][string]$InFile,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [int]$Rate = -1,
    [string]$Voice = "Microsoft Huihui Desktop"
)
# 每次以独立进程合成一句中文旁白为 WAV，避免 pyttsx3 引擎复用死锁。
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try { $s.SelectVoice($Voice) } catch { }   # 找不到指定音色则用默认
$s.Rate = $Rate
$txt = Get-Content -Raw -Encoding UTF8 $InFile
$s.SetOutputToWaveFile($OutFile)
$s.Speak($txt)
$s.SetOutputToNull()
$s.Dispose()
