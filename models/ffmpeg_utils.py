import os

def get_ffmpeg_exe():
    ffmpeg_exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not ffmpeg_exe.endswith(".exe"):
        ffmpeg_exe += ".exe"
    return ffmpeg_exe

def get_ffprobe_exe():
    ffprobe_exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not ffprobe_exe.endswith(".exe"):
        ffprobe_exe += ".exe"
    return ffprobe_exe
