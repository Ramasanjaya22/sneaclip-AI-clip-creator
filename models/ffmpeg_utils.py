import os
import shutil

def get_ffmpeg_exe():
    ffmpeg_bin = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not ffmpeg_bin.lower().endswith(".exe") and not shutil.which(ffmpeg_bin):
        # On Windows, try appending .exe if just 'ffmpeg' is provided and not directly found
        exe_path = shutil.which(ffmpeg_bin + ".exe")
        if exe_path:
            return exe_path
        # Fallback to appending .exe anyway in case it's in the working dir or a weird path
        return ffmpeg_bin + ".exe"
    return ffmpeg_bin

def get_ffprobe_exe():
    ffprobe_bin = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not ffprobe_bin.lower().endswith(".exe") and not shutil.which(ffprobe_bin):
        exe_path = shutil.which(ffprobe_bin + ".exe")
        if exe_path:
            return exe_path
        return ffprobe_bin + ".exe"
    return ffprobe_bin
