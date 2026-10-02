import os
import shutil
import sys

def _get_executable_path(env_var_name, default_name):
    """
    Helper to get the executable path.
    1. Checks environment variable (e.g. FFMPEG_BINARY)
    2. Falls back to shutil.which to find it in PATH
    3. Returns default name (e.g. 'ffmpeg') if not found.
    Handles .exe extension on Windows implicitly via shutil.which if needed.
    """
    env_path = os.environ.get(env_var_name)
    if env_path:
        return env_path

    # Try finding it in the system PATH
    system_path = shutil.which(default_name)
    if system_path:
        return system_path

    return default_name

def get_ffmpeg_exe():
    return _get_executable_path("FFMPEG_BINARY", "ffmpeg")

def get_ffprobe_exe():
    return _get_executable_path("FFPROBE_BINARY", "ffprobe")
