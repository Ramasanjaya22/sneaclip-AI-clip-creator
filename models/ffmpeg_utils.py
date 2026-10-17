import os
import sys

def _get_exe_name(base_name):
    """Appends .exe to the base executable name if running on Windows."""
    if os.name == 'nt' and not base_name.lower().endswith('.exe'):
        return base_name + '.exe'
    return base_name

def get_ffmpeg_exe():
    """Retrieves the path to the ffmpeg executable."""
    env_bin = os.environ.get("FFMPEG_BINARY")
    if env_bin:
        return _get_exe_name(env_bin)
    return _get_exe_name("ffmpeg")

def get_ffprobe_exe():
    """Retrieves the path to the ffprobe executable."""
    env_bin = os.environ.get("FFPROBE_BINARY")
    if env_bin:
        return _get_exe_name(env_bin)

    # Try to infer ffprobe from ffmpeg path
    ffmpeg_path = os.environ.get("FFMPEG_BINARY")
    if ffmpeg_path:
        base_dir = os.path.dirname(ffmpeg_path)
        return os.path.join(base_dir, _get_exe_name("ffprobe"))

    return _get_exe_name("ffprobe")
