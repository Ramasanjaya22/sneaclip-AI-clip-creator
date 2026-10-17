import sys
import subprocess
import os

from models.ffmpeg_utils import get_ffmpeg_exe
from models.processing import process_video
from models.clip_editor import generate_preview_frame
from models.ffmpeg_export import export_video_ffmpeg

# Ensure directories exist
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/clips", exist_ok=True)
os.makedirs("static/exports", exist_ok=True)

test_video = "static/uploads/mock_video.mp4"
test_output_dir = "static/clips/test_segments"
test_export = "static/exports/test_export.mp4"

# 1. Generate a mock video/audio using FFmpeg lavfi
cmd_generate = [
    get_ffmpeg_exe(), "-y", "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
    "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
    "-c:v", "libx264", "-c:a", "aac", test_video
]

try:
    print("Generating mock video...")
    subprocess.run(cmd_generate, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Mock video generated at {test_video}")

    # 2. Test processing video (audio segmentation)
    print("Testing audio segmentation...")
    segments = process_video(test_video, segment_length=2, output_dir=test_output_dir)
    print(f"Segments generated: {segments}")

    # 3. Test generate_preview_frame
    print("Testing generate_preview_frame...")
    img = generate_preview_frame(test_video, {"aspect_ratio": "9:16"}, t=1.0)
    print(f"Preview generated. Image size: {img.size}")

    # 4. Test export_video_ffmpeg
    print("Testing export_video_ffmpeg...")
    clips = [{"start": 1.0, "end": 4.0}]
    editor_opts = {
        "aspect_ratio": "9:16",
        "blur_background": True,
        "fade": {"fade_in": 0.5, "fade_out": 0.5}
    }
    success = export_video_ffmpeg(test_video, clips, editor_opts, test_export)
    print(f"Export success: {success}")

finally:
    # Cleanup
    print("Cleaning up mock files...")
    for f in [test_video, test_export]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(test_output_dir):
        for f in os.listdir(test_output_dir):
            os.remove(os.path.join(test_output_dir, f))
        os.rmdir(test_output_dir)

    print("Cleanup complete.")
