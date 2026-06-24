import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe") and not os.path.exists(exe):
        # Allow default string to be just "ffmpeg", but try to make it work if running directly on windows shell
        # Usually standard path resolution works, but let's be safe.
        pass
    return exe

def get_ffprobe_exe():
    # Similar to FFMPEG_BINARY, typically imageio or users might set this.
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    return exe
