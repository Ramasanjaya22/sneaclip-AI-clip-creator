import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        # Only append if it's just the command name without extension
        # or if the user provided a path without extension (less common, but possible)
        # To be safe, if it's exactly "ffmpeg" we change it to "ffmpeg.exe"
        if exe == "ffmpeg":
            exe = "ffmpeg.exe"
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        if exe == "ffprobe":
            exe = "ffprobe.exe"
    return exe
