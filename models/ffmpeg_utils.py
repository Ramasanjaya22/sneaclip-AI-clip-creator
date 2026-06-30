import os

def get_ffmpeg_exe():
    return os.environ.get("FFMPEG_BINARY", "ffmpeg")

def get_ffprobe_exe():
    ffmpeg_path = get_ffmpeg_exe()
    if ffmpeg_path == "ffmpeg":
        return "ffprobe"
    if ffmpeg_path.lower().endswith("ffmpeg.exe"):
        return ffmpeg_path[:-10] + "ffprobe.exe"
    if ffmpeg_path.lower().endswith("ffmpeg"):
        return ffmpeg_path[:-6] + "ffprobe"
    return "ffprobe"
