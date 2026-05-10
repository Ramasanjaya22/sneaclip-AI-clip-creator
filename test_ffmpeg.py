import sys
import subprocess
from models.ffmpeg_utils import get_ffmpeg_exe, get_ffprobe_exe

print(f"FFMPEG_EXE: {get_ffmpeg_exe()}")
print(f"FFPROBE_EXE: {get_ffprobe_exe()}")

try:
    subprocess.run([get_ffmpeg_exe(), "-version"], stdout=subprocess.PIPE, check=True)
    print("ffmpeg ok")
except Exception as e:
    print("ffmpeg failed", e)

try:
    subprocess.run([get_ffprobe_exe(), "-version"], stdout=subprocess.PIPE, check=True)
    print("ffprobe ok")
except Exception as e:
    print("ffprobe failed", e)
