import os
import shutil

def get_ffmpeg_exe():
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    env_path = os.environ.get("FFMPEG_BINARY")
    if env_path:
        return env_path

    # Check if ffmpeg is in PATH
    system_ffmpeg = shutil.which(exe_name)
    if system_ffmpeg:
        return system_ffmpeg

    return exe_name

def get_ffprobe_exe():
    exe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    env_path = os.environ.get("FFPROBE_BINARY")
    if env_path:
        return env_path

    # Check if ffprobe is in PATH
    system_ffprobe = shutil.which(exe_name)
    if system_ffprobe:
        return system_ffprobe

    return exe_name
