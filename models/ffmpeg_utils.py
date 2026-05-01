import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

def get_ffprobe_exe():
    # If FFMPEG_BINARY is set and points to an executable, try to infer ffprobe
    # Otherwise just use "ffprobe" (or "ffprobe.exe" on Windows)
    ffmpeg_exe = os.environ.get("FFMPEG_BINARY")
    if ffmpeg_exe:
        base_dir = os.path.dirname(ffmpeg_exe)
        ffprobe_exe = os.path.join(base_dir, "ffprobe")
    else:
        ffprobe_exe = "ffprobe"

    if os.name == "nt" and not ffprobe_exe.lower().endswith(".exe"):
        ffprobe_exe += ".exe"
    return ffprobe_exe
