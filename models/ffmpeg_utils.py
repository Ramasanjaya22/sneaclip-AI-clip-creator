import os

def get_ffmpeg_exe():
    ffmpeg = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not ffmpeg.endswith(".exe"):
        ffmpeg += ".exe"
    return ffmpeg

def get_ffprobe_exe():
    ffmpeg = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    # If FFMPEG_BINARY is an absolute path to ffmpeg executable,
    # we should try to derive ffprobe from it
    if os.path.dirname(ffmpeg):
        ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
    else:
        ffprobe = "ffprobe"

    if os.name == "nt" and not ffprobe.endswith(".exe"):
        ffprobe += ".exe"
    return ffprobe
