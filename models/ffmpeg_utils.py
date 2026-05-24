import os
import platform

def get_ffmpeg_exe():
    exe_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    return os.environ.get("FFMPEG_BINARY", exe_name)

def get_ffprobe_exe():
    exe_name = "ffprobe.exe" if platform.system() == "Windows" else "ffprobe"
    return os.environ.get("FFPROBE_BINARY", exe_name)
