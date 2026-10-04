import os
import subprocess

def get_ffmpeg_exe():
    return os.environ.get("FFMPEG_BINARY", "ffmpeg.exe" if os.name == "nt" else "ffmpeg")

def get_ffprobe_exe():
    return os.environ.get("FFPROBE_BINARY", "ffprobe.exe" if os.name == "nt" else "ffprobe")

def has_audio_stream(video_path):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(
            [get_ffprobe_exe(), "-v", "error", "-show_streams", "-select_streams", "a", video_path],
            capture_output=True, text=True, creationflags=flags
        )
        return "codec_type=audio" in r.stdout
    except Exception:
        return True
