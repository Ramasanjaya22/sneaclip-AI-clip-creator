import os
import shutil

def get_ffmpeg_exe():
    """
    Retrieves the FFmpeg executable path, considering environment variables
    and appending .exe on Windows if necessary.
    """
    exe_name = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe_name.lower().endswith(".exe"):
        # Use shutil.which to verify or just append .exe if it doesn't have it
        return f"{exe_name}.exe"
    return exe_name

def get_ffprobe_exe():
    """
    Retrieves the FFprobe executable path, considering environment variables
    and appending .exe on Windows if necessary.
    """
    exe_name = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe_name.lower().endswith(".exe"):
        return f"{exe_name}.exe"
    return exe_name
