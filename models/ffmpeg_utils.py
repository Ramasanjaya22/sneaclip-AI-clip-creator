import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe
