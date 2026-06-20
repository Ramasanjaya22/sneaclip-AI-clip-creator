import os
import subprocess
from models.ffmpeg_export import export_video_ffmpeg

# Generate mock video with lavfi
mock_video_path = "./mock_video.mp4"
output_path = "./mock_output.mp4"

subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
    "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
    "-c:v", "libx264", "-c:a", "aac", "-shortest", mock_video_path
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

clips = [{"start": 0, "end": 2}, {"start": 2, "end": 4}]
editor_options = {
    "aspect_ratio": "9:16",
    "blur_background": True,
    "watermark": {"enabled": False},
    "audio": {"music_path": "", "music_volume": 0.25, "original_volume": 1.0},
    "fade": {"fade_in": 0.5, "fade_out": 0.5}
}

try:
    success = export_video_ffmpeg(mock_video_path, clips, editor_options, output_path)
    if success and os.path.exists(output_path):
        print("Export test passed successfully!")
    else:
        print("Export test failed!")
finally:
    pass
