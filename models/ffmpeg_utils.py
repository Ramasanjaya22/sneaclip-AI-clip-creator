import os

def _get_exe(name):
    env_var = "FFMPEG_BINARY" if name == "ffmpeg" else "FFPROBE_BINARY"
    exe_path = os.environ.get(env_var, name)

    if os.name == "nt":
        if not exe_path.lower().endswith(".exe"):
            exe_path += ".exe"
    return exe_path

def get_ffmpeg_exe():
    return _get_exe("ffmpeg")

def get_ffprobe_exe():
    return _get_exe("ffprobe")
