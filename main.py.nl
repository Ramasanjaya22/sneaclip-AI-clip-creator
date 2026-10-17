     1	import sys
     2	import os
     3	import traceback
     4	import logging
     5	import gzip
     6	import io
     7	import hashlib
     8	import time
     9	import threading
    10
    11	sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    12
    13	from models.processing import process_video, make_prediction, find_clips, create_clips
    14	from flask import Flask, render_template, request, jsonify, send_file, make_response
    15	from models.model import VideoAutoClipper, load_model, get_directml_device
    16	from werkzeug.utils import secure_filename
    17	from datetime import datetime
    18	import numpy as np
    19	import joblib
    20	import json
    21	import re
    22
    23	from models.job_store import get_job, get_all_jobs, transition_job, update_job
    24	from models.chunked_upload import init_upload, receive_chunk, finalize_upload, get_upload_status
    25
    26	try:
    27	    import torch
    28	    TORCH_AVAILABLE = True
    29	except ImportError:
    30	    torch = None
    31	    TORCH_AVAILABLE = False
    32
    33	log_file_path = os.path.abspath("./app.log")
    34	logging.basicConfig(
    35	    filename=log_file_path,
    36	    level=logging.DEBUG,
    37	    format="%(asctime)s [%(levelname)s] %(message)s",
    38	    datefmt="%Y-%m-%d %H:%M:%S"
    39	)
    40	logger = logging.getLogger(__name__)
    41
    42
    43	# ── Performance: Metrics endpoint rate limiter ──────────────────────────
    44	class MetricsRateLimiter:
    45	    """Simple in-memory rate limiter for the /metrics endpoint.
    46
    47	    Allows up to *max_requests* requests per *window_seconds* per IP.
    48	    Thread-safe via a lock. Entries older than the window are pruned
    49	    on every check to prevent unbounded memory growth.
    50	    """
    51
    52	    def __init__(self, max_requests=60, window_seconds=60):
    53	        self.max_requests = max_requests
    54	        self.window = window_seconds
    55	        self._store = {}
    56	        self._lock = threading.Lock()
    57
    58	    def is_allowed(self, key):
    59	        now = time.time()
    60	        cutoff = now - self.window
    61	        with self._lock:
    62	            timestamps = self._store.get(key, [])
    63	            timestamps = [t for t in timestamps if t > cutoff]
    64	            self._store[key] = timestamps
    65	            if len(timestamps) >= self.max_requests:
    66	                return False
    67	            timestamps.append(now)
    68	            return True
    69
    70
    71	_metrics_limiter = MetricsRateLimiter(max_requests=60, window_seconds=60)
    72
    73
    74	class Config:
    75	    _cached_config = None
    76	    _config_mtime = 0
    77
    78	    def __init__(self, config_file_path):
    79	        self._config_file_path = config_file_path
    80	        self._load_config()
    81
    82	    def _load_config(self):
    83	        config_default = {
    84	            "use_gpu": False,
    85	            "auto_load_model": False,
    86	            "segment_length": 300,
    87	            "minimum_clip_length": 5,
    88	            "maximum_clip_length": 9,
    89	            "pad_clip_start": 1.0,
    90	            "pad_clip_end": 1.0,
    91	            "number_of_clips": 2,
    92	            "threshold": 0.7,
    93	            "leniency": 2,
    94	            "max_file_size_mb": 10240,
    95	            "max_segment_length": 300,
    96	            "max_ram_usage_mb": 4096,
    97	            "use_streaming_audio": True,
    98	            "upload_chunk_size_mb": 50,
    99	            "temp_file_ttl_hours": 24,
   100	            "enable_background_jobs": True,
   101	            "frame_sample_fps": 0.5,
   102	            "sliding_window_overlap": 2
   103	        }
   104
   105	        if not os.path.exists(self._config_file_path):
   106	            with open(self._config_file_path, "w") as f:
   107	                json.dump(config_default, f, indent="\t")
   108
   109	        with open(self._config_file_path, "r") as f:
   110	            config = json.load(f)
   111
   112	        self.use_gpu = config.get("use_gpu", False)
   113	        self.auto_load_model = config.get("auto_load_model", False)
   114	        self.segment_length = config.get("segment_length", 600)
   115
   116	        self.minimum_clip_length = config.get("minimum_clip_length", 5)
   117	        self.maximum_clip_length = config.get("maximum_clip_length", 30)
   118	        self.pad_clip_start = config.get("pad_clip_start", 1.0)
   119	        self.pad_clip_end = config.get("pad_clip_end", 1.0)
   120	        self.number_of_clips = config.get("number_of_clips", 2)
   121
   122	        self.threshold = config.get("threshold", 0.7)
   123	        self.leniency = config.get("leniency", 2)
   124
   125	        self.max_file_size_mb = config.get("max_file_size_mb", 10240)
   126	        self.max_segment_length = config.get("max_segment_length", 300)
   127	        self.max_ram_usage_mb = config.get("max_ram_usage_mb", 4096)
   128	        self.use_streaming_audio = config.get("use_streaming_audio", True)
   129	        self.upload_chunk_size_mb = config.get("upload_chunk_size_mb", 50)
   130	        self.temp_file_ttl_hours = config.get("temp_file_ttl_hours", 24)
   131	        self.enable_background_jobs = config.get("enable_background_jobs", True)
   132	        self.frame_sample_fps = config.get("frame_sample_fps", 0.5)
   133	        self.sliding_window_overlap = config.get("sliding_window_overlap", 2)
   134
   135	        Config._cached_config = config
   136	        try:
   137	            Config._config_mtime = os.path.getmtime(self._config_file_path)
   138	        except OSError:
   139	            Config._config_mtime = 0
   140
   141	    def reload_if_changed(self):
   142	        try:
   143	            current_mtime = os.path.getmtime(self._config_file_path)
   144	            if current_mtime != Config._config_mtime:
   145	                self._load_config()
   146	                logger.info("Config reloaded from disk (file changed)")
   147	        except OSError:
   148	            pass
   149
   150	    def get_device(self):
   151	        if self.use_gpu:
   152	            dml = get_directml_device()
   153	            if dml:
   154	                try:
   155	                    test = torch.zeros(1).to(dml)
   156	                    del test
   157	                    return dml
   158	                except Exception:
   159	                    logger.warning("DirectML device found but not working, falling back to CPU.")
   160	            if TORCH_AVAILABLE and torch.cuda.is_available():
   161	                return "cuda"
   162	            return "cpu"
   163	        return "cpu"
   164
   165
   166	class SimpleCache:
   167	    def __init__(self, default_ttl=120):
   168	        self._cache = {}
   169	        self._default_ttl = default_ttl
   170
   171	    def get(self, key):
   172	        entry = self._cache.get(key)
   173	        if entry is None:
   174	            return None
   175	        if time.time() > entry["expires"]:
   176	            del self._cache[key]
   177	            return None
   178	        return entry["value"]
   179
   180	    def set(self, key, value, ttl=None):
   181	        self._cache[key] = {
   182	            "value": value,
   183	            "expires": time.time() + (ttl if ttl is not None else self._default_ttl),
   184	        }
   185
   186	    def invalidate(self, key):
   187	        self._cache.pop(key, None)
   188
   189	    def clear(self):
   190	        self._cache.clear()
   191
   192
   193	api_cache = SimpleCache(default_ttl=120)
   194
   195
   196	def get_folder_name():
   197	    return datetime.now().strftime("%Y-%m-%d")
   198
   199
   200	def numerical_sort(value):
   201	    numbers = re.findall(r"\d+", value)
   202	    return int(numbers[0]) if numbers else 0
   203
   204
   205	def get_files(clip_folder):
   206	    folder_list = os.listdir(clip_folder)
   207	    all_files = {}
   208
   209	    for folder in folder_list:
   210	        folder_path = os.path.join(clip_folder, folder)
   211	        files = sorted(os.listdir(folder_path), key=numerical_sort)
   212	        all_files[folder] = files
   213
   214	    return all_files
   215
   216
   217	app = Flask(__name__)
   218	app.jinja_env.trim_blocks = True
   219	app.jinja_env.lstrip_blocks = True
   220	app.jinja_env.auto_reload = False
   221
   222	import os as __os # just in case
   223	# Security configurations
   224	is_prod = __os.environ.get('FLASK_ENV') == 'production' or __os.environ.get('NODE_ENV') == 'production'
   225	app.config.update(
   226	    SESSION_COOKIE_SECURE=is_prod,
   227	    SESSION_COOKIE_HTTPONLY=True,
   228	    SESSION_COOKIE_SAMESITE='Lax',
   229	    MAX_CONTENT_LENGTH=10240 * 1024 * 1024 # 10GB max length to match config
   230	)
   231
   232	# ── Performance: Gzip compression middleware ──────────────────────────
   233	# Compresses text/html, application/json, text/css, application/javascript
   234	# responses > 500 bytes. Reduces network transfer ~60-80% for text assets.
   235	class GzipMiddleware:
   236	    """WSGI middleware that gzip-compresses text-based responses."""
   237
   238	    # MIME types worth compressing (already-compressed formats like images excluded)
   239	    COMPRESSIBLE = {
   240	        "text/html", "text/css", "text/javascript", "text/plain",
   241	        "application/json", "application/javascript", "application/xml",
   242	        "text/xml", "application/manifest+json",
   243	    }
   244
   245	    def __init__(self, app, minimum_size=500):
   246	        self.app = app
   247	        self.minimum_size = minimum_size
   248
   249	    def __call__(self, environ, start_response):
   250	        # Check if client accepts gzip
   251	        accept_encoding = environ.get("HTTP_ACCEPT_ENCODING", "")
   252	        if "gzip" not in accept_encoding:
   253	            return self.app(environ, start_response)
   254
   255	        # Capture response headers to decide whether to compress
   256	        captured = []
   257	        def custom_start_response(status, headers, exc_info=None):
   258	            captured.extend([status, headers, exc_info])
   259	            return lambda s: None  # dummy write
   260
   261	        body_iter = self.app(environ, custom_start_response)
   262	        status, headers, exc_info = captured
   263
   264	        # Determine content-type and content-length from headers
   265	        content_type = ""
   266	        content_length = 0
   267	        for name, value in headers:
   268	            if name.lower() == "content-type":
   269	                content_type = value.split(";")[0].strip().lower()
   270	            elif name.lower() == "content-length":
   271	                try:
   272	                    content_length = int(value)
   273	                except ValueError:
   274	                    pass
   275
   276	        # Only compress compressible MIME types above minimum size
   277	        should_compress = (
   278	            content_type in self.COMPRESSIBLE
   279	            and content_length >= self.minimum_size
   280	        )
   281
   282	        if not should_compress:
   283	            # Pass through uncompressed
   284	            start_response(status, headers, exc_info)
   285	            return body_iter
   286
   287	        # Gzip-compress the response body
   288	        compressed = io.BytesIO()
   289	        with gzip.GzipFile(fileobj=compressed, mode="wb") as gz:
   290	            for chunk in body_iter:
   291	                gz.write(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
   292	        compressed_body = compressed.getvalue()
   293
   294	        new_headers = [
   295	            (name, value) for name, value in headers
   296	            if name.lower() not in ("content-length",)
   297	        ]
   298	        new_headers.append(("Content-Length", str(len(compressed_body))))
   299	        new_headers.append(("Content-Encoding", "gzip"))
   300	        new_headers.append(("Vary", "Accept-Encoding"))
   301
   302	        start_response(status, new_headers, exc_info)
   303	        return [compressed_body]
   304
   305
   306	# Wrap the Flask app with gzip compression
   307	app.wsgi_app = GzipMiddleware(app.wsgi_app)
   308
   309
   310	# ── Performance: Cache-Control headers ───────────────────────────────
   311	# Static assets (CSS, JS, images) get long-lived cache (1 year) since
   312	# they rarely change. HTML pages get no-cache so users always get fresh
   313	# content. This reduces repeat visits to near-zero latency.
   314	@app.after_request
   315	def set_cache_headers(response):
   316	    # Determine if this is a static asset request
   317	    path = request.path
   318
   319	    # Static assets with content hashes or infrequently changed files
   320	    if path.startswith("/static/"):
   321	        # Check if this is a static file with a content-based path
   322	        # (e.g., /static/clips/..., /static/exports/... are dynamic)
   323	        static_subdirs_dynamic = ("/static/clips/", "/static/uploads/",
   324	                                  "/static/exports/", "/static/previews/")
   325	        if any(path.startswith(d) for d in static_subdirs_dynamic):
   326	            # Dynamic user-generated content — short cache, must revalidate
   327	            response.cache_control.max_age = 60
   328	            response.cache_control.must_revalidate = True
   329	        else:
   330	            # Immutable assets (CSS, JS, lib) — cache for 1 year
   331	            response.cache_control.max_age = 31536000
   332	            response.cache_control.public = True
   333	            response.headers["X-Content-Type-Options"] = "nosniff"
   334	    else:
   335	        # HTML pages and API responses — no cache, always revalidate
   336	        response.cache_control.no_cache = True
   337	        response.cache_control.must_revalidate = True
   338
   339	    # Global security headers
   340	    response.headers["X-Content-Type-Options"] = "nosniff"
   341	    response.headers["X-Frame-Options"] = "SAMEORIGIN"
   342	    response.headers["X-XSS-Protection"] = "1; mode=block"
   343	    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
   344
   345	    return response
   346
   347
   348	video_folder = os.path.abspath("./static/uploads")
   349	clip_folder = os.path.abspath("./static/clips")
   350	static_folder = os.path.abspath("./static")
   351	output_folder = os.path.abspath(os.path.join(clip_folder, get_folder_name()))
   352
   353	os.makedirs(video_folder, exist_ok=True)
   354	os.makedirs(clip_folder, exist_ok=True)
   355	music_folder = os.path.abspath("./static/uploads/music")
   356	watermark_folder = os.path.abspath("./static/watermarks")
   357	os.makedirs(music_folder, exist_ok=True)
   358	os.makedirs(watermark_folder, exist_ok=True)
   359
   360	model_path = os.path.abspath("./models/VideoAutoClipper.pt")
   361	scaler_path = os.path.abspath("./models/mfcc_scaler.joblib")
   362
   363	config_file_path = os.path.abspath("./config.json")
   364	config = Config(config_file_path)
   365
   366	if config.auto_load_model:
   367	    model, model_device = load_model(VideoAutoClipper(), model_path, device=config.get_device())
   368	else:
   369	    model = False
   370	    model_device = "cpu"
   371
   372	@app.route("/", methods=["GET", "POST"])
   373	def main():
   374	    global model, model_device
   375
   376	    if request.method == "POST":
   377	        if "video" in request.files:
   378	            try:
   379	                video = request.files["video"]
   380	                if video:
   381	                    print("Processing video...")
   382
   383	                    filename = secure_filename(video.filename)
   384	                    video_path = os.path.join(video_folder, filename)
   385	                    video.save(video_path)
   386
   387	                    if not model:
   388	                        model, model_device = load_model(VideoAutoClipper(), model_path, device=config.get_device())
   389
   390	                    video_paths = process_video(video_path, config.segment_length, video_folder)
   391	                    all_scores = []
   392
   393	                    print("Making predictions...")
   394
   395	                    for path in video_paths:
   396	                        scores, sr = make_prediction(model, joblib.load(scaler_path), path, threshold=config.threshold, device=model_device)
   397	                        all_scores.extend(scores)
   398
   399	                    print("Finding best clips...")
   400
   401	                    clip_timestamps = find_clips(
   402	                        np.array(all_scores), sr,
   403	                        config.minimum_clip_length,
   404	                        config.maximum_clip_length,
   405	                        config.number_of_clips,
   406	                        config.threshold,
   407	                        video_path=video_path,
   408	                    )
   409
   410	                    info_msg = None
   411	                    if not clip_timestamps:
   412	                        info_msg = "No clips found. Try lowering the Threshold or adjusting the Minimum/Maximum Clip Length in settings."
   413
   414	                    clip_starts_ends = [(s, e) for s, e, _ in clip_timestamps]
   415	                    clip_paths = create_clips(video_path, clip_starts_ends, output_folder, config.pad_clip_start, config.pad_clip_end)
   416	                    clip_urls = [os.path.relpath(clip_path, static_folder).replace("\\", "/") for clip_path in clip_paths]
   417	                    poster_urls = _generate_clip_posters(video_path, clip_timestamps) if clip_timestamps else []
   418
   419	                    logger.info(f"Done! Generated {len(clip_urls)} clip(s).")
   420
   421	                    editor_clips = [
   422	                        {
   423	                            "start": round(s, 2),
   424	                            "end": round(e, 2),
   425	                            "score": round(sc, 2),
   426	                            "poster_url": poster_urls[idx] if idx < len(poster_urls) else ""
   427	                        }
   428	                        for idx, (s, e, sc) in enumerate(clip_timestamps)
   429	                    ]
   430	                    video_rel = os.path.relpath(video_path, static_folder).replace("\\", "/")
   431	                    editor_data = {
   432	                        "video_url": "/static/" + video_rel,
   433	                        "clips": editor_clips,
   434	                    }
   435
   436	                    return render_template(
   437	                        "index.html",
   438	                        config=config,
   439	                        clips=clip_urls,
   440	                        info=info_msg,
   441	                        editor_data=editor_data,
   442	                        folders=get_files(clip_folder),
   443	                    )
   444
   445	            except Exception as e:
   446	                error_msg = traceback.format_exc()
   447	                logger.error(f"Error processing video: {error_msg}")
   448	                return render_template(
   449	                    "index.html",
   450	                    config=config,
   451	                    error=str(e),
   452	                    folders=get_files(clip_folder)
   453	                )
   454
   455	            finally:
   456	                for path in os.listdir(video_folder):
   457	                    full_path = os.path.join(video_folder, path)
   458	                    if os.path.isfile(full_path) and "segment_" in path:
   459	                        os.remove(full_path)
   460
   461	    return render_template("index.html", config=config, folders=get_files(clip_folder))
   462
   463
   464	@app.route("/get-config", methods=["POST"])
   465	def get_config():
   466	    try:
   467	        global model, model_device
   468	        config.reload_if_changed()
   469	        previous_device = config.use_gpu
   470
   471	        config.use_gpu = request.form.get("use-gpu") == "on"
   472	        config.auto_load_model = request.form.get("auto-load-model") == "on"
   473	        config.segment_length = int(request.form.get("segment-length"))
   474
   475	        config.minimum_clip_length = int(request.form.get("minimum-clip-length"))
   476	        config.maximum_clip_length = int(request.form.get("maximum-clip-length"))
   477	        config.pad_clip_start = float(request.form.get("pad-clip-start"))
   478	        config.pad_clip_end = float(request.form.get("pad-clip-end"))
   479	        config.number_of_clips = int(request.form.get("number-of-clips"))
   480
   481	        config.threshold = float(request.form.get("threshold"))
   482	        config.leniency = int(request.form.get("leniency"))
   483	        if previous_device != config.use_gpu and model:
   484	            model, model_device = load_model(VideoAutoClipper(), model_path, device=config.get_device())
   485
   486	    except ValueError as e:
   487	        print(e)
   488
   489	    finally:
   490	        return jsonify({"status": "success", "message": "Settings succesfully updated"})
   491
   492
   493	@app.route("/save-config", methods=["POST"])
   494	def save_config():
   495	    with open(config_file_path, "w") as f:
   496	        json.dump(config.__dict__, f, indent="\t")
   497	    Config._config_mtime = 0
   498	    return jsonify({"status": "success", "message": "Settings succesfully updated"})
   499
   500
   501	def _resolve_static_path(url_path):
   502	    if not url_path:
   503	        return ""
   504	    rel = url_path.replace("/static/", "").lstrip("/")
   505	    resolved_path = os.path.abspath(os.path.join(static_folder, rel))
   506	    static_abs = os.path.abspath(static_folder)
   507	    if os.path.commonpath([static_abs, resolved_path]) != static_abs:
   508	        raise ValueError("Invalid path traversal detected")
   509	    return resolved_path
   510
   511
   512	def _normalize_editor_options_paths(editor_options):
   513	    if not editor_options:
   514	        return editor_options
   515
   516	    normalized = dict(editor_options)
   517
   518	    if normalized.get("audio", {}).get("music_path"):
   519	        normalized["audio"] = dict(normalized["audio"])
   520	        music_url = normalized["audio"].get("music_path", "")
   521	        if music_url:
   522	            normalized["audio"]["music_path"] = _resolve_static_path(music_url)
   523
   524	    if normalized.get("watermark", {}).get("image_path"):
   525	        normalized["watermark"] = dict(normalized["watermark"])
   526	        image_url = normalized["watermark"].get("image_path", "")
   527	        if image_url:
   528	            normalized["watermark"]["image_path"] = _resolve_static_path(image_url)
   529
   530	    return normalized
   531
   532
   533	def _generate_clip_posters(video_path, clip_timestamps):
   534	    from models.clip_editor import generate_preview_frame
   535
   536	    preview_subdir = os.path.join(static_folder, "previews", get_folder_name())
   537	    os.makedirs(preview_subdir, exist_ok=True)
   538
   539	    video_stem = os.path.splitext(os.path.basename(video_path))[0]
   540	    safe_stem = secure_filename(video_stem) or "video"
   541	    run_token = datetime.now().strftime("%H%M%S")
   542	    poster_urls = []
   543
   544	    for idx, clip in enumerate(clip_timestamps):
   545	        start, end = clip[0], clip[1]
   546	        midpoint = start + max(0.1, (end - start) / 2)
   547	        image = generate_preview_frame(video_path, {}, t=midpoint)
   548	        poster_name = f"{safe_stem}_{run_token}_{idx}.png"
   549	        poster_path = os.path.join(preview_subdir, poster_name)
   550	        image.save(poster_path)
   551	        rel_path = os.path.relpath(poster_path, static_folder).replace("\\", "/")
   552	        poster_urls.append("/static/" + rel_path)
   553
   554	    return poster_urls
   555
   556
   557	@app.route("/export-edit", methods=["POST"])
   558	def export_edit():
   559	    try:
   560	        data = request.get_json(force=True)
   561	        video_url = data.get("video_url", "")
   562	        clips = data.get("clips", [])
   563	        editor_options = data.get("editor_options", None)
   564
   565	        if not video_url or not clips:
   566	            return jsonify({"success": False, "error": "Missing video or clips"}), 400
   567
   568	        video_path = _resolve_static_path(video_url)
   569	        if not os.path.exists(video_path):
   570	            return jsonify({"success": False, "error": "Video file not found"}), 404
   571
   572	        from models.ffmpeg_export import start_export_job, cleanup_job
   573
   574	        export_name = "edited_" + datetime.now().strftime("%H%M%S") + ".mp4"
   575	        export_dir = os.path.join(static_folder, "exports")
   576	        os.makedirs(export_dir, exist_ok=True)
   577	        export_path = os.path.join(export_dir, export_name)
   578
   579	        editor_options = _normalize_editor_options_paths(editor_options)
   580
   581	        job_id = start_export_job(video_path, clips, editor_options, export_path)
   582	        download_url = "/static/exports/" + export_name
   583	        return jsonify({"success": True, "job_id": job_id, "download_url": download_url})
   584
   585	    except Exception as e:
   586	        logger.error(traceback.format_exc())
   587	        return jsonify({"success": False, "error": str(e)}), 500
   588
   589
   590	@app.route("/export-status/<job_id>", methods=["GET"])
   591	def export_status(job_id):
   592	    from models.ffmpeg_export import get_job_status, cleanup_job
   593	    status = get_job_status(job_id)
   594	    if status.get("status") in ("done", "error"):
   595	        cleanup_job(job_id)
   596	    return jsonify(status)
   597
   598
   599	@app.route("/upload-music", methods=["POST"])
   600	def upload_music():
   601	    try:
   602	        if "music" not in request.files:
   603	            return jsonify({"success": False, "error": "No music file provided"}), 400
   604	        file = request.files["music"]
   605	        if not file or file.filename == "":
   606	            return jsonify({"success": False, "error": "Empty file"}), 400
   607	        filename = secure_filename(file.filename)
   608	        save_path = os.path.join(music_folder, filename)
   609	        file.save(save_path)
   610	        api_cache.invalidate("list_music")
   611	        return jsonify({"success": True, "music_url": "/static/uploads/music/" + filename})
   612	    except Exception as e:
   613	        logger.error(traceback.format_exc())
   614	        return jsonify({"success": False, "error": str(e)}), 500
   615
   616
   617	@app.route("/list-music", methods=["GET"])
   618	def list_music():
   619	    try:
   620	        cached = api_cache.get("list_music")
   621	        if cached is not None:
   622	            response = make_response(cached["data"])
   623	            response.headers["X-Cache"] = "HIT"
   624	        else:
   625	            files = []
   626	            for f in os.listdir(music_folder):
   627	                if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
   628	                    files.append({"name": f, "url": "/static/uploads/music/" + f})
   629	            data = {"success": True, "music": files}
   630	            response = make_response(jsonify(data))
   631	            response.headers["X-Cache"] = "MISS"
   632	            api_cache.set("list_music", {"data": data}, ttl=120)
   633
   634	        response.headers["Cache-Control"] = "max-age=120, public"
   635	        response.headers["Vary"] = "Accept-Encoding"
   636	        etag = hashlib.md5(
   637	            (response.get_data(as_text=True)).encode("utf-8")
   638	        ).hexdigest()
   639	        response.headers["ETag"] = f'"{etag}"'
   640	        if request.headers.get("If-None-Match") == f'"{etag}"':
   641	            return make_response("", 304)
   642	        return response
   643	    except Exception as e:
   644	        logger.error(traceback.format_exc())
   645	        return jsonify({"success": False, "error": str(e)}), 500
   646
   647
   648	@app.route("/upload-watermark", methods=["POST"])
   649	def upload_watermark():
   650	    try:
   651	        if "watermark" not in request.files:
   652	            return jsonify({"success": False, "error": "No watermark file provided"}), 400
   653	        file = request.files["watermark"]
   654	        if not file or file.filename == "":
   655	            return jsonify({"success": False, "error": "Empty file"}), 400
   656	        filename = secure_filename(file.filename)
   657	        save_path = os.path.join(watermark_folder, filename)
   658	        file.save(save_path)
   659	        return jsonify({"success": True, "watermark_url": "/static/watermarks/" + filename})
   660	    except Exception as e:
   661	        logger.error(traceback.format_exc())
   662	        return jsonify({"success": False, "error": str(e)}), 500
   663
   664
   665	@app.route("/preview-clip", methods=["POST"])
   666	def preview_clip():
   667	    try:
   668	        data = request.get_json(force=True)
   669	        video_url = data.get("video_url", "")
   670	        editor_options = data.get("editor_options", {})
   671	        t = data.get("t")
   672
   673	        if not video_url:
   674	            return jsonify({"success": False, "error": "Missing video"}), 400
   675
   676	        video_path = _resolve_static_path(video_url)
   677	        if not os.path.exists(video_path):
   678	            return jsonify({"success": False, "error": "Video file not found"}), 404
   679
   680	        editor_options = _normalize_editor_options_paths(editor_options)
   681
   682	        from models.clip_editor import generate_preview_frame
   683	        if t is not None:
   684	            t = float(t)
   685	        img = generate_preview_frame(video_path, editor_options, t=t)
   686
   687	        preview_dir = os.path.join(static_folder, "previews")
   688	        os.makedirs(preview_dir, exist_ok=True)
   689	        preview_name = "preview_" + datetime.now().strftime("%H%M%S") + ".png"
   690	        preview_path = os.path.join(preview_dir, preview_name)
   691	        img.save(preview_path)
   692
   693	        return jsonify({"success": True, "preview_url": "/static/previews/" + preview_name})
   694	    except Exception as e:
   695	        logger.error(traceback.format_exc())
   696	        return jsonify({"success": False, "error": str(e)}), 500
   697
   698
   699	from flask import send_from_directory
   700
   701	@app.route("/static/exports/<path:filename>")
   702	def serve_export(filename):
   703	    export_dir = os.path.join(static_folder, "exports")
   704	    # Using send_from_directory safely handles path traversal
   705	    return send_from_directory(
   706	        export_dir,
   707	        filename,
   708	        as_attachment=True,
   709	        mimetype="video/mp4",
   710	    )
   711
   712
   713	@app.route("/static/previews/<path:filename>")
   714	def serve_preview(filename):
   715	    preview_dir = os.path.join(static_folder, "previews")
   716	    return send_from_directory(preview_dir, filename, mimetype="image/png")
   717
   718
   719	@app.route("/metrics", methods=["POST"])
   720	def collect_metrics():
   721	    client_ip = request.remote_addr or "unknown"
   722	    if not _metrics_limiter.is_allowed(client_ip):
   723	        return "", 429
   724	    try:
   725	        data = request.get_json(silent=True)
   726	        if not data or "metrics" not in data:
   727	            return "", 400
   728	        url = data.get("url", "")
   729	        ua = data.get("ua", "")
   730	        ts = data.get("ts", 0)
   731	        for m in data["metrics"]:
   732	            name = m.get("name", "unknown")
   733	            value = m.get("value", 0)
   734	            rating = m.get("rating", "")
   735	            source = m.get("source", "")
   736	            detail = m.get("detail", "")
   737	            logger.info(
   738	                "METRIC name=%s value=%s rating=%s source=%s url=%s ua=%s ts=%s detail=%s",
   739	                name, value, rating, source, url, ua, ts, detail,
   740	            )
   741	    except Exception:
   742	        logger.debug("Metrics payload could not be parsed")
   743	    return "", 204
   744
   745
   746
   747	@app.route("/upload-chunk", methods=["POST"])
   748	def upload_chunk():
   749	    upload_id = request.headers.get("X-Upload-Id")
   750	    chunk_index = request.headers.get("X-Chunk-Index")
   751
   752	    if not upload_id or chunk_index is None:
   753	        return jsonify({"error": "Missing X-Upload-Id or X-Chunk-Index"}), 400
   754
   755	    chunk_index = int(chunk_index)
   756
   757	    if "chunk" not in request.files:
   758	        return jsonify({"error": "No chunk provided"}), 400
   759
   760	    chunk_file = request.files["chunk"]
   761	    chunk_data = chunk_file.read()
   762
   763	    try:
   764	        result = receive_chunk(upload_id, chunk_index, chunk_data)
   765	        return jsonify(result)
   766	    except ValueError as e:
   767	        return jsonify({"error": str(e)}), 400
   768
   769
   770	@app.route("/finalize-upload", methods=["POST"])
   771	def finalize_upload():
   772	    data = request.get_json(force=True)
   773	    upload_id = data.get("upload_id")
   774
   775	    if not upload_id:
   776	        return jsonify({"error": "Missing upload_id"}), 400
   777
   778	    try:
   779	        result = finalize_upload(upload_id)
   780	        return jsonify(result)
   781	    except ValueError as e:
   782	        return jsonify({"error": str(e)}), 400
   783
   784
   785	@app.route("/job-status/<job_id>")
   786	def job_status(job_id):
   787	    job = get_job(job_id)
   788	    if not job:
   789	        return jsonify({"error": "Job not found"}), 404
   790	    return jsonify(job)
   791
   792
   793	@app.route("/process-video", methods=["POST"])
   794	def process_video_async():
   795	    data = request.get_json(force=True)
   796	    job_id = data.get("job_id") or data.get("upload_id")
   797
   798	    if not job_id:
   799	        return jsonify({"error": "Missing job_id"}), 400
   800
   801	    job = get_job(job_id)
   802	    if not job:
   803	        return jsonify({"error": "Job not found"}), 404
   804
   805	    video_path = None
   806	    if job.get("metadata"):
   807	        video_path = job["metadata"].get("final_path")
   808
   809	    if not video_path or not os.path.exists(video_path):
   810	        return jsonify({"error": "Video file not found"}), 404
   811
   812	    def process_worker():
   813	        try:
   814	            from models.streaming_processor import process_video_pipeline
   815	            process_video_pipeline(job_id, video_path)
   816	        except Exception as e:
   817	            import traceback
   818	            logger.error(f"Processing failed: {traceback.format_exc()}")
   819
   820	    thread = threading.Thread(target=process_worker)
   821	    thread.daemon = True
   822	    thread.start()
   823
   824	    return jsonify({
   825	        "job_id": job_id,
   826	        "status_url": f"/job-status/{job_id}"
   827	    })
   828
   829
   830	if __name__ == "__main__":
   831	    app.run(port=5000)
