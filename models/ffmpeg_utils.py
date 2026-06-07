import os
import shutil

def _get_executable(name, env_var):
    exe_path = os.environ.get(env_var)
    if exe_path:
        return exe_path

    # Check if Windows
    if os.name == 'nt':
        exe_path = shutil.which(f"{name}.exe")
        if exe_path:
            return exe_path

    exe_path = shutil.which(name)
    if exe_path:
        return exe_path

    return name

def get_ffmpeg_exe():
    return _get_executable("ffmpeg", "FFMPEG_BINARY")

def get_ffprobe_exe():
    return _get_executable("ffprobe", "FFPROBE_BINARY")
