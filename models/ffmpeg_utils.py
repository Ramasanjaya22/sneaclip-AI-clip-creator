import os

def get_ffmpeg_exe():
    ffmpeg_exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not ffmpeg_exe.endswith(".exe") and ffmpeg_exe == "ffmpeg":
        ffmpeg_exe = "ffmpeg.exe"
    return ffmpeg_exe

def get_ffprobe_exe():
    ffprobe_exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not ffprobe_exe.endswith(".exe") and ffprobe_exe == "ffprobe":
        ffprobe_exe = "ffprobe.exe"
    return ffprobe_exe
