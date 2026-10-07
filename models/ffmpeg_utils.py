import os
import subprocess

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

def get_ffprobe_exe():
    ffmpeg_exe = get_ffmpeg_exe()
    if ffmpeg_exe.lower().endswith("ffmpeg.exe"):
        exe = ffmpeg_exe[:-10] + "ffprobe.exe"
    elif ffmpeg_exe.lower().endswith("ffmpeg"):
        exe = ffmpeg_exe[:-6] + "ffprobe"
    else:
        exe = "ffprobe"
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        exe += ".exe"
    return exe

def has_audio_stream(video_path):
    try:
        r = subprocess.run(
            [get_ffprobe_exe(), "-v", "error", "-show_streams", "-select_streams", "a", video_path],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return "codec_type=audio" in r.stdout
    except Exception:
        return True
