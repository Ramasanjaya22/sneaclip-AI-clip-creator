import os

def get_ffmpeg_exe():
    exe = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    if os.name == "nt" and not exe.lower().endswith(".exe") and exe != "ffmpeg":
        # Check if the exe file without .exe exists, if so return it directly. Otherwise append .exe.
        # This is a bit tricky, but generally if we got a custom path in Windows, it should end with .exe or we append it
        if not os.path.exists(exe):
            return exe + ".exe"
    # Even if it's just 'ffmpeg', on Windows it implicitly searches for .exe.
    # To be safer with exact paths, if the user gave FFMPEG_BINARY=C:\path\to\ffmpeg
    # we want C:\path\to\ffmpeg.exe
    return exe

def get_ffprobe_exe():
    exe = os.environ.get("FFPROBE_BINARY", "ffprobe")
    if os.name == "nt" and not exe.lower().endswith(".exe") and exe != "ffprobe":
        if not os.path.exists(exe):
            return exe + ".exe"
    return exe
