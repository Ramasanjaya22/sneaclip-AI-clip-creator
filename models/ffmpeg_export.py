from functools import lru_cache
import os
import subprocess

import threading

from models.ffmpeg_utils import get_ffmpeg_exe

FFMPEG_EXE = get_ffmpeg_exe()

_export_jobs = {}
_job_counter = 0
_job_lock = threading.Lock()


def _get_job_id():
    global _job_counter
    with _job_lock:
        _job_counter += 1
        return str(_job_counter)


def _run_ffmpeg(args, job_id=None):
    cmd = [FFMPEG_EXE, "-y", "-hide_banner"] + args
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE, universal_newlines=True, creationflags=flags
    )
    if job_id:
        _export_jobs[job_id]["proc"] = proc

    duration = None
    for line in proc.stdout:
        line = line.strip()
        if job_id:
            if "Duration:" in line:
                parts = line.split("Duration: ")[1].split(",")[0].strip().split(":")
                duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            if "time=" in line and duration:
                t = line.split("time=")[1].split()[0].split(":")
                current = float(t[0]) * 3600 + float(t[1]) * 60 + float(t[2])
                _export_jobs[job_id]["progress"] = min(int((current / duration) * 100), 99)

    proc.wait()
    return proc.returncode == 0


def _escape_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _build_filter_complex(video_path, clips, editor_options):
    opts = editor_options or {}
    aspect = opts.get("aspect_ratio", "original")
    target_w, target_h = 1080, 1920
    inputs = []
    filters = []
    has_audio = _has_audio_stream(video_path)
    total_duration = sum(min(99999, c.get("end", 99999)) - max(0, c.get("start", 0)) for c in clips)

    for i, c in enumerate(clips):
        start = max(0, c.get("start", 0))
        end = min(99999, c.get("end", 99999))
        inputs += ["-ss", str(start), "-t", str(end - start), "-i", video_path]

    if len(clips) > 1:
        concat_str = "".join(f"[{idx}:v:0]" for idx in range(len(clips)))
        if has_audio:
            concat_str += "".join(f"[{idx}:a:0]" for idx in range(len(clips)))
            filters.append(f"{concat_str}concat=n={len(clips)}:v=1:a=1[concat_v][concat_a]")
            v_stream, a_stream = "[concat_v]", "[concat_a]"
        else:
            filters.append(f"{concat_str}concat=n={len(clips)}:v=1:a=0[concat_v]")
            v_stream, a_stream = "[concat_v]", None
    else:
        v_stream = "[0:v:0]"
        a_stream = "[0:a:0]" if has_audio else None

    if aspect == "9:16":
        blur_bg = opts.get("blur_background", True)
        if blur_bg:
            bg_target_w = target_w // 4
            bg_target_h = target_h // 4
            filters.append(
                f"{v_stream}split[fg_full][bg_full];"
                f"[bg_full]scale={bg_target_w}:{bg_target_h}:flags=fast_bilinear:force_original_aspect_ratio=increase,crop={bg_target_w}:{bg_target_h},boxblur=luma_radius=min(h\\,w)/18:luma_power=1,scale={target_w}:{target_h}:flags=fast_bilinear[bg];"
                f"[fg_full]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto[vert_v]"
            )
        else:
            filters.append(
                f"{v_stream}scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2[vert_v]"
            )
        v_stream = "[vert_v]"

    fade_cfg = opts.get("fade", {})
    fade_in = float(fade_cfg.get("fade_in", 0))
    fade_out = float(fade_cfg.get("fade_out", 0))
    if fade_in > 0:
        filters.append(f"{v_stream}fade=t=in:st=0:d={fade_in}[fade_v]")
        v_stream = "[fade_v]"
        if a_stream:
            filters.append(f"{a_stream}afade=t=in:st=0:d={fade_in}[fade_a]")
            a_stream = "[fade_a]"
    if fade_out > 0:
        fade_out_start = max(0.1, total_duration - fade_out)
        filters.append(f"{v_stream}fade=t=out:st={fade_out_start}:d={fade_out}:alpha=1[fade2_v]")
        v_stream = "[fade2_v]"
        if a_stream:
            filters.append(f"{a_stream}afade=t=out:st={fade_out_start}:d={fade_out}[fade2_a]")
            a_stream = "[fade2_a]"

    wm_cfg = opts.get("watermark", {})
    if wm_cfg.get("enabled", False):
        if wm_cfg.get("type") == "text":
            text = _escape_drawtext(wm_cfg.get("text", ""))
            pos = wm_cfg.get("position", "bottom-right")
            fontsize = int(wm_cfg.get("fontsize", 48))
            opacity = float(wm_cfg.get("opacity", 0.7))
            pos_map = {
                "bottom-right": f"x=w-tw-{fontsize}:y=h-th-{fontsize//2}",
                "bottom-left": f"x={fontsize//2}:y=h-th-{fontsize//2}",
                "top-right": f"x=w-tw-{fontsize}:y={fontsize//2}",
                "top-left": f"x={fontsize//2}:y={fontsize//2}",
                "center": "x=(w-tw)/2:y=(h-th)/2",
            }
            xy = pos_map.get(pos, pos_map["bottom-right"])
            alpha_expr = str(float(opacity))
            filters.append(
                f"{v_stream}drawtext=text='{text}':{xy}:"
                f"fontsize={fontsize}:fontcolor=white:"
                f"alpha={alpha_expr}:"
                f"borderw=2:bordercolor=black[wm_v]"
            )
            v_stream = "[wm_v]"
        elif wm_cfg.get("type") == "image":
            image_path = wm_cfg.get("image_path", "")
            if image_path and os.path.exists(image_path):
                overlay_idx = len(clips)
                height = int(wm_cfg.get("height", 100))
                opacity = float(wm_cfg.get("opacity", 0.7))
                pad = max(12, height // 3)
                pos = wm_cfg.get("position", "bottom-right")
                pos_map = {
                    "bottom-right": f"x=W-w-{pad}:y=H-h-{pad}",
                    "bottom-left": f"x={pad}:y=H-h-{pad}",
                    "top-right": f"x=W-w-{pad}:y={pad}",
                    "top-left": f"x={pad}:y={pad}",
                    "center": "x=(W-w)/2:y=(H-h)/2",
                }
                xy = pos_map.get(pos, pos_map["bottom-right"])
                inputs += ["-loop", "1", "-i", image_path]
                filters.append(
                    f"[{overlay_idx}:v:0]format=rgba,scale=-1:{height},colorchannelmixer=aa={opacity}[wm_img]"
                )
                filters.append(f"{v_stream}[wm_img]overlay={xy}:format=auto[wm_v]")
                v_stream = "[wm_v]"

    audio_cfg = opts.get("audio", {})
    music_path = audio_cfg.get("music_path", "")
    music_vol = float(audio_cfg.get("music_volume", 0.25))
    orig_vol = float(audio_cfg.get("original_volume", 1.0))

    if music_path and os.path.exists(music_path):
        music_idx = len(clips)
        if wm_cfg.get("enabled", False) and wm_cfg.get("type") == "image" and wm_cfg.get("image_path", "") and os.path.exists(wm_cfg.get("image_path", "")):
            music_idx += 1
        inputs += ["-stream_loop", "-1", "-i", music_path]
        filters.append(
            f"[{music_idx}:a:0]atrim=start=0[endless];[endless]aloop=loop=-1:size=2e+09[music_long];"
            f"[music_long]volume={music_vol}[music_vol]"
        )
        if a_stream and orig_vol < 1.0:
            filters.append(f"{a_stream}volume={orig_vol}[orig_vol]")
            a_stream = "[orig_vol]"
        if a_stream:
            filters.append(f"{a_stream}[music_vol]amix=inputs=2:duration=first:dropout_transition=0[final_a]")
            a_stream = "[final_a]"
        else:
            filters.append(f"[music_vol]anull[final_a]")
            a_stream = "[final_a]"
    elif a_stream and orig_vol < 1.0:
        filters.append(f"{a_stream}volume={orig_vol}[final_a]")
        a_stream = "[final_a]"

    filters.append(f"{v_stream}format=yuv420p[final_v]")
    v_stream = "[final_v]"

    return inputs, filters, v_stream, a_stream


@lru_cache(maxsize=128)
def _has_audio_stream(video_path):
    try:
        import subprocess
        r = subprocess.run(
            [FFMPEG_EXE, "-hide_banner", "-i", video_path],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return "Stream #0:1" in r.stderr or "Audio:" in r.stderr
    except Exception:
        return True


def export_video_ffmpeg(video_path, clips, editor_options, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    inputs, filters, v_stream, a_stream = _build_filter_complex(video_path, clips, editor_options)
    filter_str = ";".join(filters)
    has_audio = _has_audio_stream(video_path)
    args = inputs + [
        "-filter_complex", filter_str,
        "-map", v_stream,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-movflags", "+faststart",
        "-threads", "0",
    ]
    if has_audio:
        args += ["-map", a_stream, "-c:a", "aac", "-b:a", "128k"]
    else:
        args += ["-an"]
    args += ["-shortest", output_path]
    return _run_ffmpeg(args)


def start_export_job(video_path, clips, editor_options, output_path):
    job_id = _get_job_id()
    _export_jobs[job_id] = {
        "progress": 0,
        "status": "running",
        "output_path": output_path,
        "download_url": None,
        "error": None,
        "proc": None,
    }

    def _run():
        try:
            ok = export_video_ffmpeg(video_path, clips, editor_options, output_path)
            if ok and os.path.exists(output_path):
                _export_jobs[job_id]["status"] = "done"
                _export_jobs[job_id]["progress"] = 100
            else:
                _export_jobs[job_id]["status"] = "error"
                _export_jobs[job_id]["error"] = "FFmpeg export failed"
        except Exception as e:
            _export_jobs[job_id]["status"] = "error"
            _export_jobs[job_id]["error"] = str(e)

    threading.Thread(target=_run, daemon=True).start()
    return job_id


def get_job_status(job_id):
    return _export_jobs.get(job_id, {"status": "unknown"})


def cleanup_job(job_id):
    if job_id in _export_jobs:
        del _export_jobs[job_id]
