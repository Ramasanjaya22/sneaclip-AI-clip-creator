import os
import subprocess
from functools import lru_cache

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

@lru_cache(maxsize=128)
def has_audio_stream(video_path):
    try:
        cmd = [
            get_ffprobe_exe(), "-v", "error", "-show_streams",
            "-select_streams", "a", video_path
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(
            cmd, capture_output=True, text=True, creationflags=flags
        )
        return "codec_type=audio" in r.stdout or "codec_type=audio" in r.stderr
    except Exception:
        return True
