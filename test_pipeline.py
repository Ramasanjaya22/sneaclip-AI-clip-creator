import os
import subprocess
from models.ffmpeg_utils import get_ffmpeg_exe
from models.processing import process_video
from models.ffmpeg_export import _has_audio_stream, export_video_ffmpeg

print("Generating mock video...")
mock_video = "mock.mp4"
subprocess.run([
    get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "warning",
    "-f", "lavfi", "-i", "testsrc=duration=2:size=1280x720:rate=30",
    "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
    "-c:v", "libx264", "-c:a", "aac",
    mock_video
], check=True)

print("Testing _has_audio_stream...")
assert _has_audio_stream(mock_video) == True

print("Testing process_video (segmentation)...")
output_dir = "mock_segments"
segments = process_video(mock_video, 1, output_dir)
print(f"Generated segments: {segments}")
assert len(segments) > 0

print("Testing export_video_ffmpeg (with blur)...")
clips = [{"start": 0.5, "end": 1.5}]
editor_opts = {"aspect_ratio": "9:16", "blur_background": True}
output_export = "./mock_export.mp4"
try:
    ok = export_video_ffmpeg(mock_video, clips, editor_opts, output_export)
    if not ok:
        print("Export failed!")
        # Rerun manually to get stdout
        from models.ffmpeg_export import _build_filter_complex, FFMPEG_EXE
        inputs, filters, v_stream, a_stream = _build_filter_complex(mock_video, clips, editor_opts)
        filter_str = ";".join(filters)
        args = inputs + ["-filter_complex", filter_str, "-map", v_stream, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart", "-threads", "0", "-map", a_stream, "-c:a", "aac", "-b:a", "128k", "-shortest", output_export]
        cmd = [FFMPEG_EXE, "-y"] + args
        r = subprocess.run(cmd, capture_output=True, text=True)
        print("FFmpeg Error:\n", r.stderr)
        assert False
except Exception as e:
    print(e)
    raise

print("Cleaning up...")
os.remove(mock_video)
for f in segments:
    os.remove(f)
os.rmdir(output_dir)
os.remove(output_export)
print("Test passed successfully!")
