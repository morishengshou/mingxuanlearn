# -*- coding: utf-8 -*-
"""离线中文配音服务（Windows SAPI / Microsoft Huihui），稳健版。

每句旁白用一个独立的 PowerShell 进程调用 System.Speech 合成 WAV，
彻底避开 pyttsx3 在同进程内反复 runAndWait() 造成的 SAPI 死锁。
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path

from manim_voiceover.services.base import SpeechService, initialize_speech_service

_TTS_PS1 = str(Path(__file__).with_name("tts.ps1"))
ZH_VOICE_NAME = "Microsoft Huihui Desktop"
# 必须用 PowerShell 7 (pwsh)：Windows PowerShell 5.1 的 Add-Type System.Speech 加载不到该程序集
_PWSH = r"C:\Program Files\PowerShell\7\pwsh.exe"


class SapiZhService(SpeechService):
    """用独立 PowerShell 进程做离线中文 TTS。"""

    def __init__(self, rate: int = -1, voice: str = ZH_VOICE_NAME, **kwargs):
        self.rate = rate
        self.voice = voice
        initialize_speech_service(self, kwargs)

    def generate_from_text(self, text, cache_dir=None, path=None, **kwargs):
        if cache_dir is None:
            cache_dir = self.cache_dir
        input_data = {"input_text": text, "service": "sapi-ps",
                      "voice": self.voice, "rate": self.rate}
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached

        audio_path = (self.get_audio_basename(input_data) + ".wav") if path is None else str(path)
        out_file = str(Path(cache_dir) / audio_path)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)

        # 旁白文本写成 UTF-8(BOM) 临时文件，供 PowerShell 以 UTF8 读取，避免命令行中文乱码
        txt_file = out_file + ".txt"
        with open(txt_file, "w", encoding="utf-8-sig") as f:
            f.write(text)

        subprocess.run(
            [_PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _TTS_PS1,
             "-InFile", txt_file, "-OutFile", out_file,
             "-Rate", str(self.rate), "-Voice", self.voice],
            check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if not os.path.exists(out_file):
            raise RuntimeError(f"TTS 失败，未生成音频: {out_file}")
        try:
            os.remove(txt_file)
        except OSError:
            pass

        return {"input_text": text, "input_data": input_data, "original_audio": audio_path}


def make_zh_service(rate: int = 1):
    """rate 取 -10..10，0 为默认语速，1 略快更紧凑。"""
    return SapiZhService(rate=rate)
