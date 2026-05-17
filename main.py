import sys
import os
import traceback
import logging
import gzip
import io
import hashlib
import time
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.processing import process_video, make_prediction, find_clips, create_clips
from flask import Flask, render_template, request, jsonify, send_file, make_response
from models.model import VideoAutoClipper, load_model, get_directml_device
from werkzeug.utils import secure_filename
from datetime import datetime
import numpy as np
import joblib
import json
import re

from models.job_store import get_job, get_all_jobs, transition_job, update_job
from models.chunked_upload import init_upload, receive_chunk, finalize_upload, get_upload_status

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

log_file_path = os.path.abspath("./app.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ── Performance: Metrics endpoint rate limiter ──────────────────────────
class MetricsRateLimiter:
    """Simple in-memory rate limiter for the /metrics endpoint.

    Allows up to *max_requests* requests per *window_seconds* per IP.
    Thread-safe via a lock. Entries older than the window are pruned
    on every check to prevent unbounded memory growth.
    """

    def __init__(self, max_requests=60, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._store = {}
        self._lock = threading.Lock()

    def is_allowed(self, key):
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            timestamps = self._store.get(key, [])
            timestamps = [t for t in timestamps if t > cutoff]
            self._store[key] = timestamps
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(now)
            return True


_metrics_limiter = MetricsRateLimiter(max_requests=60, window_seconds=60)


class Config:
    _cached_config = None
    _config_mtime = 0

    def __init__(self, config_file_path):
        self._config_file_path = config_file_path
        self._load_config()

    def _load_config(self):
        config_default = {
            "use_gpu": False,
            "auto_load_model": False,
            "segment_length": 300,
            "minimum_clip_length": 5,
            "maximum_clip_length": 9,
            "pad_clip_start": 1.0,
            "pad_clip_end": 1.0,
            "number_of_clips": 2,
            "threshold": 0.7,
            "leniency": 2,
            "max_file_size_mb": 10240,
            "max_segment_length": 300,
            "max_ram_usage_mb": 4096,
            "use_streaming_audio": True,
            "upload_chunk_size_mb": 50,
            "temp_file_ttl_hours": 24,
            "enable_background_jobs": True,
            "frame_sample_fps": 0.5,
            "sliding_window_overlap": 2
        }

        if not os.path.exists(self._config_file_path):
            with open(self._config_file_path, "w") as f:
                json.dump(config_default, f, indent="\t")

        with open(self._config_file_path, "r") as f:
            config = json.load(f)

        self.use_gpu = config.get("use_gpu", False)
        self.auto_load_model = config.get("auto_load_model", False)
        self.segment_length = config.get("segment_length", 600)

        self.minimum_clip_length = config.get("minimum_clip_length", 5)
        self.maximum_clip_length = config.get("maximum_clip_length", 30)
        self.pad_clip_start = config.get("pad_clip_start", 1.0)
        self.pad_clip_end = config.get("pad_clip_end", 1.0)
        self.number_of_clips = config.get("number_of_clips", 2)

        self.threshold = config.get("threshold", 0.7)
        self.leniency = config.get("leniency", 2)

        self.max_file_size_mb = config.get("max_file_size_mb", 10240)
        self.max_segment_length = config.get("max_segment_length", 300)
        self.max_ram_usage_mb = config.get("max_ram_usage_mb", 4096)
        self.use_streaming_audio = config.get("use_streaming_audio", True)
        self.upload_chunk_size_mb = config.get("upload_chunk_size_mb", 50)
        self.temp_file_ttl_hours = config.get("temp_file_ttl_hours", 24)
        self.enable_background_jobs = config.get("enable_background_jobs", True)
        self.frame_sample_fps = config.get("frame_sample_fps", 0.5)
        self.sliding_window_overlap = config.get("sliding_window_overlap", 2)

        Config._cached_config = config
        try:
            Config._config_mtime = os.path.getmtime(self._config_file_path)
        except OSError:
            Config._config_mtime = 0

    def reload_if_changed(self):
        try:
            current_mtime = os.path.getmtime(self._config_file_path)
            if current_mtime != Config._config_mtime:
                self._load_config()
                logger.info("Config reloaded from disk (file changed)")
        except OSError:
            pass

    def get_device(self):
        if self.use_gpu:
            dml = get_directml_device()
            if dml:
                try:
                    test = torch.zeros(1).to(dml)
                    del test
                    return dml
                except Exception:
                    logger.warning("DirectML device found but not working, falling back to CPU.")
            if TORCH_AVAILABLE and torch.cuda.is_available():
                return "cuda"
            return "cpu"
        return "cpu"


class SimpleCache:
    def __init__(self, default_ttl=120):
        self._cache = {}
        self._default_ttl = default_ttl

    def get(self, key):
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires"]:
            del self._cache[key]
            return None
        return entry["value"]

    def set(self, key, value, ttl=None):
        self._cache[key] = {
            "value": value,
            "expires": time.time() + (ttl if ttl is not None else self._default_ttl),
        }

    def invalidate(self, key):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()


api_cache = SimpleCache(default_ttl=120)


def get_folder_name():
    return datetime.now().strftime("%Y-%m-%d")


def numerical_sort(value):
    numbers = re.findall(r"\d+", value)
    return int(numbers[0]) if numbers else 0


def get_files(clip_folder):
    folder_list = os.listdir(clip_folder)
    all_files = {}

    for folder in folder_list:
        folder_path = os.path.join(clip_folder, folder)
        files = sorted(os.listdir(folder_path), key=numerical_sort)
        all_files[folder] = files

    return all_files


app = Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.jinja_env.auto_reload = False

import os as __os # just in case
# Security configurations
is_prod = __os.environ.get('FLASK_ENV') == 'production' or __os.environ.get('NODE_ENV') == 'production'

app.secret_key = __os.environ.get('FLASK_SECRET_KEY', __os.urandom(32))

app.config.update(
    SESSION_COOKIE_SECURE=is_prod,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=10240 * 1024 * 1024 # 10GB max length to match config
)

def safe_error(e):
    if is_prod:
        return "Internal Server Error"
    return str(e)

ALLOWED_EXTENSIONS_VIDEO = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
ALLOWED_EXTENSIONS_MUSIC = {'mp3', 'wav', 'm4a', 'ogg', 'flac'}
ALLOWED_EXTENSIONS_IMAGE = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file_extension(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

# ── Performance: Gzip compression middleware ──────────────────────────
# Compresses text/html, application/json, text/css, application/javascript
# responses > 500 bytes. Reduces network transfer ~60-80% for text assets.
class GzipMiddleware:
    """WSGI middleware that gzip-compresses text-based responses."""

    # MIME types worth compressing (already-compressed formats like images excluded)
    COMPRESSIBLE = {
        "text/html", "text/css", "text/javascript", "text/plain",
        "application/json", "application/javascript", "application/xml",
        "text/xml", "application/manifest+json",
    }

    def __init__(self, app, minimum_size=500):
        self.app = app
        self.minimum_size = minimum_size

    def __call__(self, environ, start_response):
        # Check if client accepts gzip
        accept_encoding = environ.get("HTTP_ACCEPT_ENCODING", "")
        if "gzip" not in accept_encoding:
            return self.app(environ, start_response)

        # Capture response headers to decide whether to compress
        captured = []
        def custom_start_response(status, headers, exc_info=None):
            captured.extend([status, headers, exc_info])
            return lambda s: None  # dummy write

        body_iter = self.app(environ, custom_start_response)
        status, headers, exc_info = captured

        # Determine content-type and content-length from headers
        content_type = ""
        content_length = 0
        for name, value in headers:
            if name.lower() == "content-type":
                content_type = value.split(";")[0].strip().lower()
            elif name.lower() == "content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    pass

        # Only compress compressible MIME types above minimum size
        should_compress = (
            content_type in self.COMPRESSIBLE
            and content_length >= self.minimum_size
        )

        if not should_compress:
            # Pass through uncompressed
            start_response(status, headers, exc_info)
            return body_iter

        # Gzip-compress the response body
        compressed = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed, mode="wb") as gz:
            for chunk in body_iter:
                gz.write(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        compressed_body = compressed.getvalue()

        new_headers = [
            (name, value) for name, value in headers
            if name.lower() not in ("content-length",)
        ]
        new_headers.append(("Content-Length", str(len(compressed_body))))
        new_headers.append(("Content-Encoding", "gzip"))
        new_headers.append(("Vary", "Accept-Encoding"))

        start_response(status, new_headers, exc_info)
        return [compressed_body]


# Wrap the Flask app with gzip compression
app.wsgi_app = GzipMiddleware(app.wsgi_app)


# ── Performance: Cache-Control headers ───────────────────────────────
# Static assets (CSS, JS, images) get long-lived cache (1 year) since
# they rarely change. HTML pages get no-cache so users always get fresh
# content. This reduces repeat visits to near-zero latency.
@app.after_request
def set_cache_headers(response):
    # Determine if this is a static asset request
    path = request.path

    # Static assets with content hashes or infrequently changed files
    if path.startswith("/static/"):
        # Check if this is a static file with a content-based path
        # (e.g., /static/clips/..., /static/exports/... are dynamic)
        static_subdirs_dynamic = ("/static/clips/", "/static/uploads/",
                                  "/static/exports/", "/static/previews/")
        if any(path.startswith(d) for d in static_subdirs_dynamic):
            # Dynamic user-generated content — short cache, must revalidate
            response.cache_control.max_age = 60
            response.cache_control.must_revalidate = True
        else:
            # Immutable assets (CSS, JS, lib) — cache for 1 year
            response.cache_control.max_age = 31536000
            response.cache_control.public = True
            response.headers["X-Content-Type-Options"] = "nosniff"
    else:
        # HTML pages and API responses — no cache, always revalidate
        response.cache_control.no_cache = True
        response.cache_control.must_revalidate = True

    # Global security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.plyr.io; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:;"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


video_folder = os.path.abspath("./static/uploads")
clip_folder = os.path.abspath("./static/clips")
static_folder = os.path.abspath("./static")
output_folder = os.path.abspath(os.path.join(clip_folder, get_folder_name()))

os.makedirs(video_folder, exist_ok=True)
os.makedirs(clip_folder, exist_ok=True)
music_folder = os.path.abspath("./static/uploads/music")
watermark_folder = os.path.abspath("./static/watermarks")
os.makedirs(music_folder, exist_ok=True)
os.makedirs(watermark_folder, exist_ok=True)

model_path = os.path.abspath("./models/VideoAutoClipper.pt")
scaler_path = os.path.abspath("./models/mfcc_scaler.joblib")

config_file_path = os.path.abspath("./config.json")
config = Config(config_file_path)

if config.auto_load_model:
    model, model_device = load_model(VideoAutoClipper(), model_path, device=config.get_device())
else:
    model = False
    model_device = "cpu"

@app.route("/", methods=["GET", "POST"])
def main():
    global model, model_device

    if request.method == "POST":
        if "video" in request.files:
            try:
                video = request.files["video"]
                if video and allowed_file_extension(video.filename, ALLOWED_EXTENSIONS_VIDEO):
                    print("Processing video...")

                    filename = secure_filename(video.filename)
                    video_path = os.path.join(video_folder, filename)
                    video.save(video_path)

                    if not model:
                        model, model_device = load_model(VideoAutoClipper(), model_path, device=config.get_device())

                    video_paths = process_video(video_path, config.segment_length, video_folder)
                    all_scores = []

                    print("Making predictions...")

                    for path in video_paths:
                        scores, sr = make_prediction(model, joblib.load(scaler_path), path, threshold=config.threshold, device=model_device)
                        all_scores.extend(scores)

                    print("Finding best clips...")

                    clip_timestamps = find_clips(
                        np.array(all_scores), sr,
                        config.minimum_clip_length,
                        config.maximum_clip_length,
                        config.number_of_clips,
                        config.threshold,
                        video_path=video_path,
                    )

                    info_msg = None
                    if not clip_timestamps:
                        info_msg = "No clips found. Try lowering the Threshold or adjusting the Minimum/Maximum Clip Length in settings."

                    clip_starts_ends = [(s, e) for s, e, _ in clip_timestamps]
                    clip_paths = create_clips(video_path, clip_starts_ends, output_folder, config.pad_clip_start, config.pad_clip_end)
                    clip_urls = [os.path.relpath(clip_path, static_folder).replace("\\", "/") for clip_path in clip_paths]
                    poster_urls = _generate_clip_posters(video_path, clip_timestamps) if clip_timestamps else []

                    logger.info(f"Done! Generated {len(clip_urls)} clip(s).")

                    editor_clips = [
                        {
                            "start": round(s, 2),
                            "end": round(e, 2),
                            "score": round(sc, 2),
                            "poster_url": poster_urls[idx] if idx < len(poster_urls) else ""
                        }
                        for idx, (s, e, sc) in enumerate(clip_timestamps)
                    ]
                    video_rel = os.path.relpath(video_path, static_folder).replace("\\", "/")
                    editor_data = {
                        "video_url": "/static/" + video_rel,
                        "clips": editor_clips,
                    }

                    return render_template(
                        "index.html",
                        config=config,
                        clips=clip_urls,
                        info=info_msg,
                        editor_data=editor_data,
                        folders=get_files(clip_folder),
                    )

            except Exception as e:
                error_msg = traceback.format_exc()
                logger.error(f"Error processing video: {error_msg}")
                return render_template(
                    "index.html",
                    config=config,
                    error=safe_error(e),
                    folders=get_files(clip_folder)
                )

            finally:
                for path in os.listdir(video_folder):
                    full_path = os.path.join(video_folder, path)
                    if os.path.isfile(full_path) and "segment_" in path:
                        os.remove(full_path)

    return render_template("index.html", config=config, folders=get_files(clip_folder))


@app.route("/get-config", methods=["POST"])
def get_config():
    try:
        global model, model_device
        config.reload_if_changed()
        previous_device = config.use_gpu

        config.use_gpu = request.form.get("use-gpu") == "on"
        config.auto_load_model = request.form.get("auto-load-model") == "on"
        config.segment_length = int(request.form.get("segment-length"))

        config.minimum_clip_length = int(request.form.get("minimum-clip-length"))
        config.maximum_clip_length = int(request.form.get("maximum-clip-length"))
        config.pad_clip_start = float(request.form.get("pad-clip-start"))
        config.pad_clip_end = float(request.form.get("pad-clip-end"))
        config.number_of_clips = int(request.form.get("number-of-clips"))

        config.threshold = float(request.form.get("threshold"))
        config.leniency = int(request.form.get("leniency"))
        if previous_device != config.use_gpu and model:
            model, model_device = load_model(VideoAutoClipper(), model_path, device=config.get_device())

    except ValueError as e:
        print(e)

    finally:
        return jsonify({"status": "success", "message": "Settings succesfully updated"})


@app.route("/save-config", methods=["POST"])
def save_config():
    with open(config_file_path, "w") as f:
        json.dump(config.__dict__, f, indent="\t")
    Config._config_mtime = 0
    return jsonify({"status": "success", "message": "Settings succesfully updated"})


def _resolve_static_path(url_path):
    if not url_path:
        return ""
    rel = url_path.replace("/static/", "").lstrip("/")
    resolved_path = os.path.abspath(os.path.join(static_folder, rel))
    static_abs = os.path.abspath(static_folder)
    if os.path.commonpath([static_abs, resolved_path]) != static_abs:
        raise ValueError("Invalid path traversal detected")
    return resolved_path


def _normalize_editor_options_paths(editor_options):
    if not editor_options:
        return editor_options

    normalized = dict(editor_options)

    if normalized.get("audio", {}).get("music_path"):
        normalized["audio"] = dict(normalized["audio"])
        music_url = normalized["audio"].get("music_path", "")
        if music_url:
            normalized["audio"]["music_path"] = _resolve_static_path(music_url)

    if normalized.get("watermark", {}).get("image_path"):
        normalized["watermark"] = dict(normalized["watermark"])
        image_url = normalized["watermark"].get("image_path", "")
        if image_url:
            normalized["watermark"]["image_path"] = _resolve_static_path(image_url)

    return normalized


def _generate_clip_posters(video_path, clip_timestamps):
    from models.clip_editor import generate_preview_frame

    preview_subdir = os.path.join(static_folder, "previews", get_folder_name())
    os.makedirs(preview_subdir, exist_ok=True)

    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    safe_stem = secure_filename(video_stem) or "video"
    run_token = datetime.now().strftime("%H%M%S")
    poster_urls = []

    for idx, clip in enumerate(clip_timestamps):
        start, end = clip[0], clip[1]
        midpoint = start + max(0.1, (end - start) / 2)
        image = generate_preview_frame(video_path, {}, t=midpoint)
        poster_name = f"{safe_stem}_{run_token}_{idx}.png"
        poster_path = os.path.join(preview_subdir, poster_name)
        image.save(poster_path)
        rel_path = os.path.relpath(poster_path, static_folder).replace("\\", "/")
        poster_urls.append("/static/" + rel_path)

    return poster_urls


@app.route("/export-edit", methods=["POST"])
def export_edit():
    try:
        data = request.get_json(force=True)
        video_url = data.get("video_url", "")
        clips = data.get("clips", [])
        editor_options = data.get("editor_options", None)

        if not video_url or not clips:
            return jsonify({"success": False, "error": "Missing video or clips"}), 400

        video_path = _resolve_static_path(video_url)
        if not os.path.exists(video_path):
            return jsonify({"success": False, "error": "Video file not found"}), 404

        from models.ffmpeg_export import start_export_job, cleanup_job

        export_name = "edited_" + datetime.now().strftime("%H%M%S") + ".mp4"
        export_dir = os.path.join(static_folder, "exports")
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, export_name)

        editor_options = _normalize_editor_options_paths(editor_options)

        job_id = start_export_job(video_path, clips, editor_options, export_path)
        download_url = "/static/exports/" + export_name
        return jsonify({"success": True, "job_id": job_id, "download_url": download_url})

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": safe_error(e)}), 500


@app.route("/export-status/<job_id>", methods=["GET"])
def export_status(job_id):
    from models.ffmpeg_export import get_job_status, cleanup_job
    status = get_job_status(job_id)
    if status.get("status") in ("done", "error"):
        cleanup_job(job_id)
    return jsonify(status)


@app.route("/upload-music", methods=["POST"])
def upload_music():
    try:
        if "music" not in request.files:
            return jsonify({"success": False, "error": "No music file provided"}), 400
        file = request.files["music"]
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "Empty file"}), 400
        if not allowed_file_extension(file.filename, ALLOWED_EXTENSIONS_MUSIC):
            return jsonify({"success": False, "error": "Invalid file type"}), 400
        filename = secure_filename(file.filename)
        save_path = os.path.join(music_folder, filename)
        file.save(save_path)
        api_cache.invalidate("list_music")
        return jsonify({"success": True, "music_url": "/static/uploads/music/" + filename})
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": safe_error(e)}), 500


@app.route("/list-music", methods=["GET"])
def list_music():
    try:
        cached = api_cache.get("list_music")
        if cached is not None:
            response = make_response(cached["data"])
            response.headers["X-Cache"] = "HIT"
        else:
            files = []
            for f in os.listdir(music_folder):
                if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
                    files.append({"name": f, "url": "/static/uploads/music/" + f})
            data = {"success": True, "music": files}
            response = make_response(jsonify(data))
            response.headers["X-Cache"] = "MISS"
            api_cache.set("list_music", {"data": data}, ttl=120)

        response.headers["Cache-Control"] = "max-age=120, public"
        response.headers["Vary"] = "Accept-Encoding"
        etag = hashlib.md5(
            (response.get_data(as_text=True)).encode("utf-8")
        ).hexdigest()
        response.headers["ETag"] = f'"{etag}"'
        if request.headers.get("If-None-Match") == f'"{etag}"':
            return make_response("", 304)
        return response
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": safe_error(e)}), 500


@app.route("/upload-watermark", methods=["POST"])
def upload_watermark():
    try:
        if "watermark" not in request.files:
            return jsonify({"success": False, "error": "No watermark file provided"}), 400
        file = request.files["watermark"]
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "Empty file"}), 400
        if not allowed_file_extension(file.filename, ALLOWED_EXTENSIONS_IMAGE):
            return jsonify({"success": False, "error": "Invalid file type"}), 400
        filename = secure_filename(file.filename)
        save_path = os.path.join(watermark_folder, filename)
        file.save(save_path)
        return jsonify({"success": True, "watermark_url": "/static/watermarks/" + filename})
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": safe_error(e)}), 500


@app.route("/preview-clip", methods=["POST"])
def preview_clip():
    try:
        data = request.get_json(force=True)
        video_url = data.get("video_url", "")
        editor_options = data.get("editor_options", {})
        t = data.get("t")

        if not video_url:
            return jsonify({"success": False, "error": "Missing video"}), 400

        video_path = _resolve_static_path(video_url)
        if not os.path.exists(video_path):
            return jsonify({"success": False, "error": "Video file not found"}), 404

        editor_options = _normalize_editor_options_paths(editor_options)

        from models.clip_editor import generate_preview_frame
        if t is not None:
            t = float(t)
        img = generate_preview_frame(video_path, editor_options, t=t)

        preview_dir = os.path.join(static_folder, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        preview_name = "preview_" + datetime.now().strftime("%H%M%S") + ".png"
        preview_path = os.path.join(preview_dir, preview_name)
        img.save(preview_path)

        return jsonify({"success": True, "preview_url": "/static/previews/" + preview_name})
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": safe_error(e)}), 500


from flask import send_from_directory

@app.route("/static/exports/<path:filename>")
def serve_export(filename):
    export_dir = os.path.join(static_folder, "exports")
    # Using send_from_directory safely handles path traversal
    return send_from_directory(
        export_dir,
        filename,
        as_attachment=True,
        mimetype="video/mp4",
    )


@app.route("/static/previews/<path:filename>")
def serve_preview(filename):
    preview_dir = os.path.join(static_folder, "previews")
    return send_from_directory(preview_dir, filename, mimetype="image/png")


@app.route("/metrics", methods=["POST"])
def collect_metrics():
    client_ip = request.remote_addr or "unknown"
    if not _metrics_limiter.is_allowed(client_ip):
        return "", 429
    try:
        data = request.get_json(silent=True)
        if not data or "metrics" not in data:
            return "", 400
        url = data.get("url", "")
        ua = data.get("ua", "")
        ts = data.get("ts", 0)
        for m in data["metrics"]:
            name = m.get("name", "unknown")
            value = m.get("value", 0)
            rating = m.get("rating", "")
            source = m.get("source", "")
            detail = m.get("detail", "")
            logger.info(
                "METRIC name=%s value=%s rating=%s source=%s url=%s ua=%s ts=%s detail=%s",
                name, value, rating, source, url, ua, ts, detail,
            )
    except Exception:
        logger.debug("Metrics payload could not be parsed")
    return "", 204



@app.route("/upload-chunk", methods=["POST"])
def upload_chunk():
    upload_id = request.headers.get("X-Upload-Id")
    chunk_index = request.headers.get("X-Chunk-Index")
    
    if not upload_id or chunk_index is None:
        return jsonify({"error": "Missing X-Upload-Id or X-Chunk-Index"}), 400
    
    upload_id = secure_filename(upload_id)
    try:
        chunk_index = int(chunk_index)
    except ValueError:
        return jsonify({"error": "Invalid chunk index"}), 400
    
    if "chunk" not in request.files:
        return jsonify({"error": "No chunk provided"}), 400
    
    chunk_file = request.files["chunk"]
    chunk_data = chunk_file.read()
    
    try:
        result = receive_chunk(upload_id, chunk_index, chunk_data)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/finalize-upload", methods=["POST"])
def finalize_upload():
    data = request.get_json(force=True)
    upload_id = data.get("upload_id")
    
    if not upload_id:
        return jsonify({"error": "Missing upload_id"}), 400

    upload_id = secure_filename(upload_id)
    
    try:
        result = finalize_upload(upload_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/job-status/<job_id>")
def job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/process-video", methods=["POST"])
def process_video_async():
    data = request.get_json(force=True)
    job_id = data.get("job_id") or data.get("upload_id")
    
    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400

    job_id = secure_filename(job_id)
    
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    video_path = None
    if job.get("metadata"):
        video_path = job["metadata"].get("final_path")
    
    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": "Video file not found"}), 404
    
    def process_worker():
        try:
            from models.streaming_processor import process_video_pipeline
            process_video_pipeline(job_id, video_path)
        except Exception as e:
            import traceback
            logger.error(f"Processing failed: {traceback.format_exc()}")
    
    thread = threading.Thread(target=process_worker)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status_url": f"/job-status/{job_id}"
    })


if __name__ == "__main__":
    app.run(port=5000)
