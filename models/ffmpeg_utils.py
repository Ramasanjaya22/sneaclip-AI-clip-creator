import os
import subprocess
from functools import lru_cache

def get_ffmpeg_exe():
    return os.environ.get("FFMPEG_BINARY", "ffmpeg")

def get_ffprobe_exe():
    return os.environ.get("FFPROBE_BINARY", "ffprobe")

@lru_cache(maxsize=128)
def has_audio_stream(video_path):
    try:
        r = subprocess.run(
            [get_ffprobe_exe(), "-v", "error", "-show_streams", "-select_streams", "a", video_path],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return "codec_type=audio" in r.stdout
    except Exception:
        return True
