import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        # We append .exe only if it's an absolute path that exists without .exe,
        # or if it's just 'ffmpeg' we might let subprocess find it, but it's safer
        # to ensure it resolves if it's a direct path.
        if os.path.exists(exe + ".exe"):
            exe += ".exe"
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        if os.path.exists(exe + ".exe"):
            exe += ".exe"
    return exe
