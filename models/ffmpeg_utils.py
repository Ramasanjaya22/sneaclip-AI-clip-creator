import os
import shutil

def get_ffmpeg_exe():
    env_bin = os.environ.get("FFMPEG_BINARY")
    if env_bin:
        return env_bin

    # Cek di PATH
    path_bin = shutil.which("ffmpeg")
    if path_bin:
        return path_bin

    return "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

def get_ffprobe_exe():
    env_bin = os.environ.get("FFMPEG_BINARY")
    if env_bin:
        # Jika user set FFMPEG_BINARY, kita asumsikan ffprobe ada di folder yang sama
        dir_path = os.path.dirname(env_bin)
        ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        env_ffprobe = os.path.join(dir_path, ffprobe_name) if dir_path else ffprobe_name
        if shutil.which(env_ffprobe):
            return env_ffprobe

    path_bin = shutil.which("ffprobe")
    if path_bin:
        return path_bin

    return "ffprobe.exe" if os.name == "nt" else "ffprobe"
