import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe") and "ffmpeg" in exe.lower():
        # Check if the environment variable just said "ffmpeg", we might still need .exe
        # but if it's already an absolute path without .exe it might fail, usually it's "ffmpeg"
        if exe == "ffmpeg":
             return "ffmpeg.exe"
    return exe

def get_ffprobe_exe():
    # Similar logic for ffprobe. Sometimes FFMPEG_BINARY is set, but not FFPROBE_BINARY
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe") and "ffprobe" in exe.lower():
        if exe == "ffprobe":
             return "ffprobe.exe"
    return exe
