import os
import sys

def get_ffmpeg_exe():
    if "FFMPEG_BINARY" in os.environ:
        return os.environ["FFMPEG_BINARY"]
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

def get_ffprobe_exe():
    ffmpeg_exe = get_ffmpeg_exe()
    if ffmpeg_exe.endswith("ffmpeg.exe"):
        return ffmpeg_exe.replace("ffmpeg.exe", "ffprobe.exe")
    elif ffmpeg_exe.endswith("ffmpeg"):
        return ffmpeg_exe[:-6] + "ffprobe"
    return "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
