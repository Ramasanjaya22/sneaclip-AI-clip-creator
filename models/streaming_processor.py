import os
import time
import json
from models.job_store import get_job, transition_job, update_job
from models.chunked_upload import get_upload_status
from models.ffmpeg_utils import get_ffmpeg_exe

VIDEO_FOLDER = os.path.abspath("./static/uploads")
CLIP_FOLDER = os.path.abspath("./static/clips")
MODEL_PATH = os.path.abspath("./models/VideoAutoClipper.pt")
SCALER_PATH = os.path.abspath("./models/mfcc_scaler.joblib")

try:
    from models.model import VideoAutoClipper, load_model, get_directml_device
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def process_video_pipeline(job_id, video_path, config=None):
    try:
        job = get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if config is None:
            from main import config as app_config
            config = app_config
        
        transition_job(job_id, 'SEGMENTING_AUDIO', "Extracting audio segments...", progress=20)
        
        audio_segments = extract_audio_streaming(video_path, segment_length=config.segment_length)
        
        transition_job(job_id, 'ANALYZING_FRAME_STREAM', "Running ML prediction...", progress=40)
        
        all_scores = []
        for idx, segment_path in enumerate(audio_segments):
            progress = 40 + (idx / len(audio_segments)) * 20
            update_job(job_id, progress=progress, message=f"Processing segment {idx+1}/{len(audio_segments)}")
            
            scores = predict_segment(segment_path, config)
            all_scores.extend(scores)
        
        transition_job(job_id, 'TRIMMING_OUTPUT', "Finding best clips...", progress=65)
        
        import numpy as np
        from models.processing import find_clips
        
        clip_timestamps = find_clips(
            np.array(all_scores), 22050,
            config.minimum_clip_length,
            config.maximum_clip_length,
            config.number_of_clips,
            config.leniency,
            video_path=video_path
        )
        
        if not clip_timestamps:
            update_job(job_id, status='COMPLETE', progress=100, 
                      message="No clips found. Try lowering threshold.")
            return {"clips": [], "message": "No clips found"}
        
        transition_job(job_id, 'TRIMMING_OUTPUT', "Creating clip videos...", progress=75)
        
        output_folder = os.path.join(CLIP_FOLDER, time.strftime("%Y-%m-%d"))
        os.makedirs(output_folder, exist_ok=True)
        
        from models.processing import create_clips
        pad_start = config.pad_clip_start
        pad_end = config.pad_clip_end
        
        clip_paths = create_clips(
            video_path, 
            [(s, e) for s, e, _ in clip_timestamps],
            output_folder,
            pad_start,
            pad_end
        )
        
        static_folder = os.path.abspath("./static")
        clip_urls = [os.path.relpath(p, static_folder).replace("\\", "/") for p in clip_paths]
        
        result = {
            "clips": clip_urls,
            "timestamps": [(s, e, sc) for s, e, sc in clip_timestamps]
        }
        
        transition_job(job_id, 'COMPLETE', "Processing complete!", progress=100)
        update_job(job_id, result=result)
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        update_job(job_id, status='FAILED', error=error_msg, 
                  message=f"Error: {str(e)}")
        raise


def extract_audio_streaming(video_path, segment_length=300):
    import subprocess
    import glob
    
    output_base = video_path + "_audio_segment"
    ffmpeg_exe = get_ffmpeg_exe()
    
    cmd = [
        ffmpeg_exe, "-hide_banner", "-loglevel", "warning", "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "22050",
        "-ac", "1",
        "-f", "segment",
        "-segment_time", str(segment_length),
        "-threads", "0",
        "-y", f"{output_base}_%03d.wav"
    ]
    
    subprocess.run(cmd, check=True, timeout=3600, 
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return sorted(glob.glob(f"{output_base}_*.wav"))


def predict_segment(segment_path, config):
    import numpy as np
    import librosa
    
    audio, sr = librosa.load(segment_path, sr=22050, mono=True)
    
    if TORCH_AVAILABLE and config.get_device() != "cpu":
        from models.processing import make_prediction
        scaler = __import__('joblib').load(SCALER_PATH)
        scores, _ = make_prediction(
            None, scaler, segment_path,
            threshold=config.threshold,
            device=config.get_device()
        )
        return list(scores)
    else:
        rms = librosa.feature.rms(y=audio, frame_length=4096, hop_length=2048).squeeze()
        peak = float(np.max(rms))
        return list(rms / peak if peak > 0 else rms)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
        video_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        if not video_path:
            job = get_job(job_id)
            if job:
                metadata = job.get('metadata', {})
                video_path = metadata.get('final_path')
        
        if video_path:
            result = process_video_pipeline(job_id, video_path)
            print(json.dumps(result, indent=2))
        else:
            print("Usage: python streaming_processor.py <job_id> [video_path]")
