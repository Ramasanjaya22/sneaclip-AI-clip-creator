import os
import subprocess

def get_ffmpeg_exe():
    """Returns the FFmpeg executable path."""
    return os.environ.get("FFMPEG_BINARY", "ffmpeg")

def get_ffprobe_exe():
    """Returns the FFprobe executable path."""
    ffmpeg_exe = get_ffmpeg_exe()
    if ffmpeg_exe == "ffmpeg":
        return "ffprobe"
    dir_name = os.path.dirname(ffmpeg_exe)
    base_name = os.path.basename(ffmpeg_exe)
    if base_name.lower().endswith(".exe"):
        return os.path.join(dir_name, "ffprobe.exe")
    return os.path.join(dir_name, "ffprobe")

def has_audio_stream(video_path):
    """Detects if a video has an audio stream using ffprobe efficiently."""
    try:
        cmd = [
            get_ffprobe_exe(),
            "-v", "error",
            "-show_streams",
            "-select_streams", "a",
            video_path
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
        return "codec_type=audio" in r.stdout
    except Exception:
        return True
