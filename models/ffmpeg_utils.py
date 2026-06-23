import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

def get_ffprobe_exe():
    # If FFMPEG_BINARY is set, try to derive FFPROBE_BINARY if not explicitly set
    ffmpeg_exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    default_ffprobe = "ffprobe"
    if ffmpeg_exe != "ffmpeg":
        # Guess ffprobe path based on ffmpeg path
        dir_name = os.path.dirname(ffmpeg_exe)
        default_ffprobe = os.path.join(dir_name, "ffprobe")

    exe = os.environ.get("FFPROBE_BINARY", default_ffprobe)
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe
