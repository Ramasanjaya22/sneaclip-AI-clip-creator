import os
import numpy as np
from PIL import Image
from models.ffmpeg_utils import get_ffmpeg_exe, get_ffprobe_exe
from models.ffmpeg_export import _has_audio_stream
from models.clip_editor import _blur_frame_fast

def run_tests():
    print("Testing ffmpeg utils...")
    ffmpeg_exe = get_ffmpeg_exe()
    ffprobe_exe = get_ffprobe_exe()
    print(f"FFmpeg path: {ffmpeg_exe}")
    print(f"FFprobe path: {ffprobe_exe}")
    assert isinstance(ffmpeg_exe, str), "ffmpeg_exe should be a string"
    assert isinstance(ffprobe_exe, str), "ffprobe_exe should be a string"

    print("Testing _blur_frame_fast...")
    dummy_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
    try:
        blurred = _blur_frame_fast(dummy_frame)
        print(f"Blurred frame shape: {blurred.shape}")
        assert blurred.shape == (1080, 1920, 3), "Output shape should match input for _blur_frame_fast"
    except Exception as e:
        print(f"Failed during _blur_frame_fast: {e}")
        raise

    print("Testing _has_audio_stream (dummy fallback behavior)...")
    has_audio = _has_audio_stream("nonexistent_file.mp4")
    print(f"Has audio fallback for nonexistent file: {has_audio}")

    print("All tests passed!")

if __name__ == "__main__":
    run_tests()
