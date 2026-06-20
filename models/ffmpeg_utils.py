import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        # Hanya tambahkan .exe jika path tidak memilikinya (dan tidak merusak absolute path custom)
        # Jika exe cuma "ffmpeg", jadi "ffmpeg.exe"
        if not os.path.exists(exe) and exe == "ffmpeg":
            return "ffmpeg.exe"
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe"):
        if not os.path.exists(exe) and exe == "ffprobe":
            return "ffprobe.exe"
    return exe
