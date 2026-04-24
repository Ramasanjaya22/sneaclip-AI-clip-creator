from moviepy import VideoFileClip
import numpy as np
import librosa
import math
import os
from models.clip_editor import process_clip, VIDEO_WRITE_KWARGS

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


def process_video(video_file, segment_length, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    video = VideoFileClip(video_file)
    audio = video.audio

    try:
        duration = audio.duration
        segment_start = 0
        segment_end = segment_length
        segment_name = 0

        output_paths = []
        while segment_start < duration:
            if segment_end > duration:
                segment_end = duration

            segment = audio.subclipped(segment_start, segment_end)
            output_path = os.path.join(output_dir, f"segment_{segment_name}.wav")
            segment.write_audiofile(output_path, fps=None, logger=None, codec="pcm_s16le")

            segment_start = segment_end
            segment_end += segment_length

            output_paths.append(output_path)
            segment_name += 1

        return output_paths

    finally:
        video.close()


def make_prediction(model, scaler, video_path, threshold=0.5, device="cpu"):
    audio, sr = librosa.load(video_path, sr=22050, mono=True)
    if TORCH_AVAILABLE and not getattr(model, "is_fallback", False):
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40, n_fft=4096, hop_length=2048)

        mfcc = torch.Tensor(scaler.transform(mfcc.T).transpose(-1, 0)).unsqueeze(0)

        try:
            mfcc = mfcc.to(device)
        except Exception:
            device = "cpu"
            mfcc = mfcc.to(device)
            model = model.cpu()

        with torch.no_grad():
            scores = torch.sigmoid(model(mfcc)).squeeze().detach().cpu().numpy()

        if scores.ndim == 0:
            scores = np.array([scores])

        return scores, sr

    rms = librosa.feature.rms(y=audio, frame_length=4096, hop_length=2048).squeeze()
    if rms.size == 0:
        return np.array([], dtype=float), sr

    peak = float(np.max(rms))
    scores = rms / peak if peak > 0 else rms
    return scores.astype(float), sr


def _compute_energy_profile(video_path, hop_length=2048, sr=22050):
    try:
        audio, _ = librosa.load(video_path, sr=sr, mono=True)
        rms = librosa.feature.rms(y=audio, frame_length=4096, hop_length=hop_length).squeeze()
        if rms.size == 0:
            return np.array([0.0])
        peak = float(np.max(rms))
        return rms / peak if peak > 0 else rms
    except Exception:
        return np.array([0.0])


def _smooth_scores(scores, window=5):
    if len(scores) <= window:
        return scores
    kernel = np.ones(window) / window
    return np.convolve(scores, kernel, mode="same")


def _prefix_sum(arr):
    ps = np.zeros(len(arr) + 1)
    for i in range(len(arr)):
        ps[i + 1] = ps[i] + arr[i]
    return ps


def _window_avg(ps, start, end):
    return (ps[end] - ps[start]) / max(1, end - start)


def find_clips(scores, sr, minimum_length, maximum_length, number_of_clips, leniency, video_path=None):
    if len(scores) == 0:
        return []

    hop_length = 2048
    frames_per_sec = sr / hop_length

    min_frames = max(3, math.ceil(minimum_length * frames_per_sec))
    max_frames = int(maximum_length * frames_per_sec)

    if min_frames > len(scores):
        center = len(scores) // 2
        return [(max(0, (center - min_frames // 2) / frames_per_sec),
                 min(len(scores) / frames_per_sec, (center + min_frames // 2) / frames_per_sec))]

    smooth_window = max(3, int(frames_per_sec * 0.5))
    smoothed = _smooth_scores(scores, window=smooth_window)

    ps = _prefix_sum(smoothed)

    step = max(1, min_frames // 4)
    candidates = []

    for start in range(0, len(smoothed) - min_frames + 1, step):
        best_score = -1
        best_end = min(start + min_frames, len(smoothed))

        for end in range(start + min_frames, min(start + max_frames + 1, len(smoothed) + 1), step):
            avg = _window_avg(ps, start, end)
            peak = float(np.max(smoothed[start:end]))
            score = 0.6 * avg + 0.4 * peak
            if score > best_score:
                best_score = score
                best_end = end

        avg = _window_avg(ps, start, best_end)
        peak = float(np.max(smoothed[start:best_end]))
        final_score = 0.6 * avg + 0.4 * peak

        candidates.append({
            "start": start / frames_per_sec,
            "end": best_end / frames_per_sec,
            "score": float(final_score),
            "start_frame": start,
            "end_frame": best_end,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)

    selected = []
    for cand in candidates:
        if len(selected) >= number_of_clips:
            break

        overlaps = False
        for sel in selected:
            if cand["start"] < sel["end"] and cand["end"] > sel["start"]:
                overlaps = True
                break

        if not overlaps:
            selected.append(cand)

    if len(selected) < number_of_clips:
        best_idx = int(np.argmax(smoothed))
        center_time = best_idx / frames_per_sec
        half = (min_frames / frames_per_sec) / 2
        fallback = (max(0, center_time - half), min(len(scores) / frames_per_sec, center_time + half))

        already = False
        for sel in selected:
            if fallback[0] < sel["end"] and fallback[1] > sel["start"]:
                already = True
                break
        if not already and len(selected) < number_of_clips:
            selected.append({"start": fallback[0], "end": fallback[1], "score": 0.0})

    selected.sort(key=lambda c: c["start"])

    return [(c["start"], c["end"], c.get("score", 0.0)) for c in selected]


def create_clips(video_file, clip_timestamps, output_dir, pad_clip_start, pad_clip_end, editor_options=None):
    os.makedirs(output_dir, exist_ok=True)
    clip_paths = []

    video = VideoFileClip(video_file)
    clip_number = int(len(os.listdir(output_dir)))

    try:
        for start_time, end_time in clip_timestamps:
            start_time = max(0, start_time - pad_clip_start)
            end_time = min(video.duration, end_time + pad_clip_end)

            if end_time - start_time < 0.5:
                continue

            subclip = video.subclipped(start_time, end_time)
            if editor_options:
                subclip = process_clip(subclip, editor_options)

            output_path = os.path.join(output_dir, f"{clip_number}.mp4")
            subclip.write_videofile(output_path, **VIDEO_WRITE_KWARGS)
            subclip.close()

            clip_paths.append(output_path)
            clip_number += 1

        return clip_paths

    finally:
        video.close()
