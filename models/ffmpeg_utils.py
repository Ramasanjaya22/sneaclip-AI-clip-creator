import os

def get_ffmpeg_exe():
    ffmpeg_bin = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not ffmpeg_bin.lower().endswith(".exe"):
        # Check if ffmpeg exists in path or is absolute. If it's just "ffmpeg", we might just append .exe
        # Actually, let's keep it simple: if nt and doesn't end with .exe and not a full path, append .exe.
        # But even a full path needs .exe on Windows. So just append .exe if it doesn't end with it.
        ffmpeg_bin += ".exe"
    return ffmpeg_bin

def get_ffprobe_exe():
    ffprobe_bin = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not ffprobe_bin.lower().endswith(".exe"):
        ffprobe_bin += ".exe"
    return ffprobe_bin
