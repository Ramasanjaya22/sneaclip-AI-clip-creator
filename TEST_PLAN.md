# Test Plan — SneaClip v0.3.0

**Date**: April 24, 2026  
**Scope**: Functional, performance, and regression testing for SneaClip (fork & improvement of autoclipper tools)

---

## 1. Test Environment

| Item | Detail |
|------|--------|
| OS | Windows 10/11, Linux (Ubuntu 22.04+), macOS 13+ |
| Python | 3.9, 3.10, 3.11, 3.12 |
| GPU | Optional: CUDA 11.8+ / DirectML |
| Browser | Chrome 120+, Firefox 115+, Edge 120+ |
| Model Files | `VideoAutoClipper.pt`, `mfcc_scaler.joblib` |

---

## 2. Test Categories

### 2.1 Installation & Setup

| Test | Steps | Expected |
|------|-------|----------|
| Virtual env creation | `python -m venv venv312` | Env created without error |
| Dependencies install | `pip install -r requirements.txt` | All packages installed |
| Model exist check | Check `models/` folder | `VideoAutoClipper.pt` & `mfcc_scaler.joblib` present |
| Fallback mode | Set `"auto_load_model": false` | App runs without model |
| Run.bat execution | Execute `run.bat` | Server starts on port 5000 |

---

### 2.2 Configuration (`config.json`)

| Test | Input | Expected |
|------|------|----------|
| Default config creation | Delete `config.json`, run app | Default config created |
| GPU toggle on | `"use_gpu": true` | GPU device selected (if available) |
| GPU toggle off | `"use_gpu": false` | CPU device selected |
| Segment length | `600` → `300` | Video segmented in 5-min chunks |
| Threshold change | `0.7` → `0.5` | More clips detected |
| Clip length bounds | `min:5, max:30` | Clips within range |
| Config reload | Edit file while running | Changes detected & applied |

---

### 2.3 Upload & Processing

| Test | Input | Expected |
|------|------|----------|
| Valid video upload | MP4, MOV, AVI, MKV | Processed successfully |
| File size limit | 2GB file | Accepted (10GB support coming) |
| Invalid format | `.txt`, `.pdf` | Rejected with error message |
| Drag & drop | Browser DnD | File captured correctly |
| Segment generation | 10-min video, seg=600 | ~10 segment WAV files created |
| AI model inference | Valid model + segment | Prediction scores returned |
| Clip detection | Scores + threshold | Clips with timestamps extracted |
| No clips found | Very high threshold (0.99) | Info message displayed |

---

### 2.4 API Endpoints

| Endpoint | Method | Test | Expected |
|----------|--------|------|----------|
| `/` | GET | Access main page | HTTP 200, HTML rendered |
| `/` | POST (upload) | Valid video file | HTTP 200, clips generated |
| `/upload-music` | POST | Valid MP3 file | HTTP 200, music URL returned |
| `/upload-watermark` | POST | Valid PNG image | HTTP 200, watermark URL returned |
| `/list-music` | GET | Existing music files | HTTP 200, JSON with music list |
| `/export-edit` | POST | Valid clip + options | HTTP 200, `job_id` + `download_url` |
| `/export-status/<job_id>` | GET | Valid job_id | HTTP 200, status JSON |
| `/preview-clip` | POST | Valid video + t=10.5 | HTTP 200, preview URL |
| `/get-config` | POST | Form data | HTTP 200, success message |
| `/save-config` | POST | Config file exists | HTTP 200, saved message |

---

### 2.5 Video Export & Editor

| Test | Input | Expected |
|------|------|----------|
| Basic export | Clip timestamps only | MP4 exported, playable |
| 9:16 conversion | `aspect_ratio: "9:16"` | Vertical video, 1080x1920 |
| Blur background | `blur_background: true` | Blurred sides, clear center |
| Watermark text | `type: "text"`, `text: "@Test"` | Text visible on video |
| Watermark image | `type: "image"`, image_path | Image overlay visible |
| Audio mixing | `music_path`, `music_volume: 0.3` | Mixed audio in output |
| Fade in/out | `fade_in: 0.5`, `fade_out: 0.5` | Smooth transitions |
| Combined options | All above together | All effects applied correctly |
| Export job polling | Call `/export-status/<job_id>` | Progress 0→100, then "done" |

---

### 2.6 Performance & Reliability

| Test | Condition | Expected |
|------|-----------|----------|
| Large file (2GB) | Upload MP4 2GB | Processed within reasonable time |
| Gzip compression | Check response headers | `Content-Encoding: gzip` present |
| Cache headers | `/static/` assets | `max-age=31536000` for immutable |
| Cache headers | HTML pages | `no-cache, must-revalidate` |
| Rate limiting | POST `/metrics` 70x in 60s | HTTP 429 after limit |
| Background export | 3 concurrent exports | All complete successfully |
| Memory cleanup | After export done | Job removed from `_export_jobs` |

---

### 2.7 Browser Compatibility

| Browser | Upload | Preview | Export | Editor UI |
|---------|--------|---------|--------|-----------|
| Chrome 120+ | ✅ | ✅ | ✅ | ✅ |
| Firefox 115+ | ✅ | ✅ | ✅ | ✅ |
| Edge 120+ | ✅ | ✅ | ✅ | ✅ |
| Safari 16+ | ✅ | ✅ | ✅ | ⚠️ Minor CSS |

---

### 2.8 Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Video file not found | HTTP 404, JSON error message |
| Invalid music path | Clip exported without music |
| Corrupt video file | HTTP 400, error logged |
| FFmpeg failure | Job status "error", error in response |
| Model file missing + `auto_load: true` | Fallback, error in UI |
| Port 5000 in use | `OSError` in console, suggest port change |

---

## 3. Automated Test Checklist

```bash
# Run these checks before releasing:

□ requirements.txt installs without error
□ app.py starts without import errors
□ config.json is created with defaults if missing
□ Upload video → get clips → export works end-to-end
□ 9:16 aspect ratio converts correctly
□ Watermark (text + image) renders on output
□ Audio mixing produces mixed output
□ Fade in/out effects audibly present
□ Preview endpoint returns valid PNG
□ Export job status progresses 0→100→done
□ Gzip compression active on text responses
□ Cache headers set correctly on static assets
□ Rate limiter blocks after 60 req/min
□ All screenshots in README saved as actual .png files
```

---

## 4. Regression Tests (After Fork/Improvement)

| Feature | Original | Improved | Status |
|---------|----------|-----------|--------|
| Flask backend | ✅ | ✅ + performance opts | ✅ |
| PyTorch model | ✅ | ✅ + DirectML | ✅ |
| FFmpeg export | ✅ | ✅ + optimized | 🔄 Pending |
| 9:16 conversion | ✅ | ✅ + blur bg | ✅ |
| Watermark system | ✅ | ✅ + image support | ✅ |
| Audio mixing | ❌ | ✅ Added | ✅ |
| Fade effects | ❌ | ✅ Added | ✅ |
| 10GB upload | ❌ | ❌ Roadmap | 🔄 Pending |
| Whitelabel ready | ❌ | ✅ Added | ✅ |

---

## 5. Known Limitations (Test Around These)

| Limitation | Workaround |
|-------------|-------------|
| Max upload: 2GB (10GB planned) | Compress video before upload |
| Model required for clip detection | Use `"auto_load_model": false` for basic export |
| GPU required for fast inference | CPU works, slower |
| Windows path separators | Code uses `os.path`, cross-platform OK |

---

## 6. Test Commands (Quick Smoke Test)

```bash
# 1. Start the app
cd "C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator"
.\run.bat

# 2. Test upload (PowerShell)
Invoke-RestMethod -Uri "http://localhost:5000/" -Method GET

# 3. Test with curl (Linux/macOS)
curl -X GET http://localhost:5000/

# 4. Check logs
Get-Content "app.log" -Tail 50
```

---

**Last Updated**: April 24, 2026  
**Tester**: ramasanjaya3302@gmail.com  
**Version Under Test**: v0.3.0
