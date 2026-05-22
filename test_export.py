from models.ffmpeg_export import export_video_ffmpeg
import os

clips = [{"start": 0, "end": 2}]
options = {
    "aspect_ratio": "9:16",
    "blur_background": True,
    "audio": {
        "original_volume": 1.0
    }
}
ok = export_video_ffmpeg("test_video.mp4", clips, options, "./test_out.mp4", job_id="test_1")
print("Export OK:", ok)
