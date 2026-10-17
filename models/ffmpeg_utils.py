import os

def get_ffmpeg_exe():
    return os.environ.get("FFMPEG_BINARY", "ffmpeg")

def get_ffprobe_exe():
    return os.environ.get("FFPROBE_BINARY", "ffprobe")
