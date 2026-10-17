import os

def get_ffmpeg_exe():
    ffmpeg_binary = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not ffmpeg_binary.lower().endswith(".exe"):
        return ffmpeg_binary + ".exe"
    return ffmpeg_binary

def get_ffprobe_exe():
    ffprobe_binary = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not ffprobe_binary.lower().endswith(".exe"):
        return ffprobe_binary + ".exe"
    return ffprobe_binary
