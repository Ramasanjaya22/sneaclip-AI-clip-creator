import os
import shutil

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.endswith(".exe"):
        # If it's just 'ffmpeg', shutil.which might find it.
        # But if we want to be safe about the extension.
        resolved = shutil.which(exe)
        if resolved:
            return resolved
        return exe + ".exe"
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.endswith(".exe"):
        resolved = shutil.which(exe)
        if resolved:
            return resolved
        return exe + ".exe"
    return exe
