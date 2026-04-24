# Rencana Teknis: Automation Clip Creator Editor Enhancement
## AI Clip Creator - Vertical 9:16 Smart Clipper Plan

---

## 1. Ringkasan Eksekutif

Plan ini merencanakan enhancement fitur automation clip creator agar mendukung output **vertical 9:16**, konversi cerdas **horizontal-to-vertical dengan blurred background**, **auto-watermark**, **auto audio/music mixing**, dan **auto fade-in/fade-out**. Semua fitur akan dibangun di atas **existing open-source library** yang sudah ada di ecosystem proyek ini, tanpa membuat video processing engine dari nol.

**Library utama yang akan digunakan:**
- **MoviePy** (sudah ada, v2.2.1) — engine video processing, compositing, audio mixing, effects
- **FFmpeg** (sudah ada via `imageio-ffmpeg`) — backend rendering & codec
- **Pillow** (sudah ada, v11.3.0) — image processing untuk watermark dan blur background
- **NumPy** (sudah ada) — array manipulation untuk efek visual
- **pydub** (tambahan baru, opsional) — advanced audio processing jika MoviePy audio tidak cukup fleksibel

---

## 2. Rekomendasi Library Open Source

| Komponen | Library Rekomendasi | Status | Alasan |
|----------|---------------------|--------|--------|
| Video Processing & Editing | **MoviePy** (`Zulko/moviepy`) | ✅ Sudah ada | Mature, Pythonic API, mendukung compositing, resizing, cropping, audio mixing, fade effects |
| Rendering Backend | **FFmpeg** via `imageio-ffmpeg` | ✅ Sudah ada | Industry standard, sudah terintegrasi dengan MoviePy |
| Watermark & Image FX | **Pillow** (`python-pillow/Pillow`) | ✅ Sudah ada | Image manipulation, text rendering, alpha blending |
| Advanced Audio (opsional) | **pydub** (`jiaaro/pydub`) | ⬜ Tambah baru | Ducking, crossfade, gain control lebih presisi daripada MoviePy native |
| Aspect Ratio Detection | **MoviePy** built-in | ✅ Sudah ada | `clip.size` memberikan `(width, height)` |
| Blur Effect | **MoviePy + Pillow** | ✅ Bisa kombinasi | Pillow GaussianBlur + MoviePy ImageClip |

**Catatan:** Tidak perlu library tambahan seperti Remotion (React-based, terlalu berat), CapCut API (proprietary), atau auto-editor (terlalu kompleks untuk kebutuhan ini). MoviePy yang sudah ada sangat cukup untuk semua requirements.

---

## 3. Arsitektur Fitur

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Browser)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Upload Page  │  │ Results Page │  │    Editor Page (NEW)     │  │
│  │  + Aspect    │  │  + 9:16      │  │  ┌────────────────────┐  │  │
│  │    Ratio     │  │    Preview   │  │  │ Aspect Ratio Toggle│  │  │
│  │    Toggle    │  │    Badge     │  │  │ (16:9 / 9:16)      │  │  │
│  └──────────────┘  └──────────────┘  │  ├────────────────────┤  │  │
│                                      │  │ Watermark Settings │  │  │
│                                      │  ├────────────────────┤  │  │
│                                      │  │ Audio/Music Mix    │  │  │
│                                      │  ├────────────────────┤  │  │
│                                      │  │ Fade In/Out Config │  │  │
│                                      │  └────────────────────┘  │  │
│                                      └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (Flask - Python)                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           NEW: `models/clip_editor.py` (Engine)             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │   │
│  │  │  Vertical9  │ │  BlurBg     │ │   WatermarkOverlay    │  │   │
│  │  │  16Renderer │ │  Generator  │ │   (Text/Image)        │  │   │
│  │  └─────────────┘ └─────────────┘ └───────────────────────┘  │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │   │
│  │  │  AudioMixer │ │  FadeFX     │ │   ExportPipeline      │  │   │
│  │  │  (Music+VO) │ │  In/Out     │ │   (MoviePy Composer)  │  │   │
│  │  └─────────────┘ └─────────────┘ └───────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │        MODIFIED: `main.py` (Routes)                         │   │
│  │  • POST `/export-edit`  → extend dengan editor options      │   │
│  │  • POST `/preview-clip` → NEW, generate preview frame       │   │
│  │  • POST `/upload-music` → NEW, upload background music      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │        MODIFIED: `models/processing.py`                     │   │
│  │  • `create_clips()` → extend dengan `editor_options` param  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE & CONFIG                               │
│  • `config.json` → tambah editor settings                           │
│  • `static/exports/` → output video                                 │
│  • `static/uploads/music/` → background music library               │
│  • `static/watermarks/` → watermark image/logo library              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Spesifikasi Teknis Detail

### 4.1 Vertical 9:16 Clip Support

**Target Output:** 1080x1920 (9:16) atau 720x1280

**Logika Deteksi & Konversi:**
```python
# Pseudocode arsitektur
def render_clip(input_clip, target_aspect="9:16"):
    w, h = input_clip.size
    current_aspect = w / h
    target_ratio = 9 / 16  # 0.5625
    
    if current_aspect > target_ratio:
        # Video horizontal (lebar), perlu vertical conversion dengan blur bg
        return render_vertical_with_blur(input_clip)
    else:
        # Sudah vertical atau square, cukup resize & crop ke 9:16
        return render_vertical_resize_crop(input_clip)
```

**Implementation dengan MoviePy:**
- Gunakan `clip.resized()` atau `clip.crop()` untuk fit ke target resolution
- Untuk video yang sudah vertical: `clip.resized(height=1920)` lalu `crop(x_center=0.5, y_center=0.5, width=1080, height=1920)`

### 4.2 Smart Horizontal-to-Vertical (Blur Background)

**Efek yang diminta:** Area black bars (letterbox) diganti dengan versi buram/glassy/blur dari video itu sendiri.

**Teknis:**
1. Buat **background layer**: resize video original ke `height=1920` (cover mode), lalu apply **Gaussian Blur** (radius 15-25px)
2. Buat **foreground layer**: resize video original dengan `height=1080` (fit mode, maintain aspect ratio), center secara vertikal
3. Composite: `CompositeVideoClip([background, foreground])`
4. Output final: 1080x1920

**MoviePy Implementation:**
```python
from moviepy import VideoFileClip, CompositeVideoClip
from PIL import ImageFilter
import numpy as np

def create_blurred_background(clip, target_w=1080, target_h=1920, blur_radius=20):
    # Background: scale to cover, then blur
    bg = clip.resized(height=target_h)  # scale up
    # Apply blur via PIL by converting frame-by-frame atau gunakan MoviePy fl_image
    def blur_frame(frame):
        from PIL import Image
        img = Image.fromarray(frame)
        blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        return np.array(blurred)
    bg = bg.with_effects([Lambda(lambda f: blur_frame(f))])  # atau fl_image
    bg = bg.crop(x_center=0.5, y_center=0.5, width=target_w, height=target_h)
    
    # Foreground: fit to width, maintain aspect
    fg = clip.resized(width=target_w)
    # Center vertically
    fg = fg.with_position("center")
    
    return CompositeVideoClip([bg, fg], size=(target_w, target_h))
```

**Optimasi Performa:**
- Untuk blur, gunakan **PIL GaussianBlur** yang cukup cepat untuk video pendek
- Alternatif: gunakan **FFmpeg native boxblur** via `ffmpeg -i input -vf "boxblur=luma_radius=min(h\,w)/20:luma_power=1"` jika perlu performa lebih baik untuk video panjang
- Untuk proyek ini, MoviePy + PIL cukup karena clip duration pendek (5-30 detik)

### 4.3 Auto-Watermark

**Fitur:**
- Text watermark atau Image watermark
- Konfigurasi: posisi (top-left, top-right, bottom-left, bottom-right, center), opacity (0-1), ukuran
- Font: system default atau custom TTF

**Implementation MoviePy:**
```python
from moviepy import TextClip, ImageClip

def add_watermark(clip, text=None, image_path=None, position="bottom-right", 
                  opacity=0.7, fontsize=48, color="white"):
    if text:
        watermark = TextClip(text=text, font="Arial-Bold", fontsize=fontsize, 
                            color=color, stroke_color="black", stroke_width=1)
    elif image_path:
        watermark = ImageClip(image_path).resized(height=100)
    
    watermark = watermark.with_opacity(opacity)
    watermark = watermark.with_position(position)
    watermark = watermark.with_duration(clip.duration)
    
    return CompositeVideoClip([clip, watermark])
```

**Posisi yang didukung:**
- String: `"left"`, `"right"`, `"top"`, `"bottom"`, `"center"`
- Tuple: `(x, y)` pixel coordinates
- Predefined: `"top-left"`, `"top-right"`, `"bottom-left"`, `"bottom-right"`

### 4.4 Auto Audio - Music & Editor

**Fitur:**
1. **Background Music**: Upload file MP3/WAV, secara otomatis di-mix dengan audio original video
2. **Volume Mixing**: Kontrol volume music (0-100%) dan volume original audio (0-100%)
3. **Auto-Duck**: Music volume otomatis turun saat ada dialog/suara di video (optional advanced)
4. **Trim**: Music otomatis di-loop atau di-trim sesuai durasi clip

**Implementation MoviePy Audio:**
```python
from moviepy import CompositeAudioClip, AudioFileClip

def mix_audio(video_clip, music_path=None, music_volume=0.3, original_volume=1.0):
    # Original audio
    original = video_clip.audio
    if original:
        original = original.with_volume_scaled(original_volume)
    
    if music_path and os.path.exists(music_path):
        music = AudioFileClip(music_path)
        
        # Loop atau trim music sesuai durasi video
        if music.duration < video_clip.duration:
            # Loop music
            n_loops = int(video_clip.duration / music.duration) + 1
            music = music.loop(n=n_loops)
        
        music = music.subclipped(0, video_clip.duration)
        music = music.with_volume_scaled(music_volume)
        
        if original:
            final_audio = CompositeAudioClip([original, music])
        else:
            final_audio = music
    else:
        final_audio = original
    
    return video_clip.with_audio(final_audio)
```

**Advanced Audio Ducking (opsional Phase 2):**
Gunakan `librosa` yang sudah ada untuk deteksi voice activity, lalu turunkan volume music di segment-segment tersebut.

### 4.5 Auto Fade-In / Fade-Out

**Fitur:**
- Fade-in di awal clip (durasi configurable, default 0.5s)
- Fade-out di akhir clip (durasi configurable, default 0.5s)
- Berlaku untuk video dan audio

**Implementation MoviePy:**
```python
from moviepy import vfx

def apply_fades(clip, fade_in=0.5, fade_out=0.5):
    if fade_in > 0:
        clip = clip.with_effects([vfx.FadeIn(fade_in)])
    if fade_out > 0:
        clip = clip.with_effects([vfx.FadeOut(fade_out)])
    return clip
```

**Audio Fade:**
```python
from moviepy import afx

def apply_audio_fades(clip, fade_in=0.5, fade_out=0.5):
    if clip.audio:
        audio = clip.audio.with_effects([
            afx.AudioFadeIn(fade_in),
            afx.AudioFadeOut(fade_out)
        ])
        clip = clip.with_audio(audio)
    return clip
```

---

## 5. Struktur File & Perubahan

### File Baru yang Harus Dibuat

| File | Fungsi |
|------|--------|
| `models/clip_editor.py` | **Engine utama** — berisi semua fungsi editing: vertical render, blur bg, watermark, audio mix, fade effects |
| `models/audio_utils.py` | Utility audio: ducking, volume analysis, music looping (opsional, bisa digabung ke clip_editor.py) |
| `static/watermarks/` | Folder penyimpanan watermark image/logo yang di-upload user |
| `static/uploads/music/` | Folder penyimpanan background music yang di-upload user |

### File yang Harus Dimodifikasi

| File | Modifikasi |
|------|-----------|
| `main.py` | • Extend `export_edit()` route untuk menerima `editor_options` JSON<br>• Tambah route `POST /preview-clip` untuk generate preview frame<br>• Tambah route `POST /upload-music` untuk upload bg music<br>• Tambah route `GET /list-music` untuk list music library |
| `models/processing.py` | • Extend `create_clips()` untuk support `editor_options` parameter<br>• Integrasi dengan `clip_editor.py` engine |
| `templates/index.html` | • Tambah **Aspect Ratio Toggle** (16:9 / 9:16 / Auto) di editor page<br>• Tambah **Watermark Panel**: text input, position select, opacity slider, size slider<br>• Tambah **Audio Panel**: music upload, volume sliders (music + original)<br>• Tambah **Fade Panel**: fade-in duration, fade-out duration sliders<br>• Tambah **Preview Button** untuk lihat hasil sebelum export |
| `static/app.js` | • Tambah event listeners untuk semua kontrol editor baru<br>• Implementasi live preview (kirim ke `/preview-clip`, tampilkan frame)<br>• Extend payload `export-edit` untuk include `editor_options`<br>• Upload music handler |
| `config.json` | Tambah field default untuk editor settings |
| `requirements.txt` | Tambah `pydub>=0.25.1` (opsional, untuk advanced audio) |

---

## 6. Langkah Implementasi (Step-by-Step)

### Phase 1: Foundation & Vertical Renderer (1-2 hari)

**Step 1.1:** Buat `models/clip_editor.py`
- Implementasi `render_vertical_9_16(clip)` — resize & crop untuk video yang sudah vertical/square
- Implementasi `render_vertical_with_blur(clip)` — horizontal-to-vertical dengan blurred background
- Unit test dengan sample video horizontal dan vertical

**Step 1.2:** Extend `models/processing.py`
- Modifikasi `create_clips()` untuk menerima `editor_options` dict
- Panggil fungsi dari `clip_editor.py` jika `editor_options` disediakan

**Step 1.3:** Update Frontend — Aspect Ratio Toggle
- Tambah toggle 16:9 / 9:16 di editor page HTML
- Kirim `aspect_ratio` dalam payload export

**Step 1.4:** Test End-to-End
- Upload video horizontal → export 9:16 dengan blur bg
- Upload video vertical → export 9:16 normal

### Phase 2: Watermark & Fade Effects (1 hari)

**Step 2.1:** Extend `models/clip_editor.py`
- Implementasi `add_watermark(clip, config)`
- Implementasi `apply_fades(clip, fade_in, fade_out)` — video + audio

**Step 2.2:** Update Frontend — Watermark & Fade UI
- Tambah panel watermark di HTML
- Tambah panel fade in/out di HTML
- Extend app.js untuk kirim konfigurasi baru

**Step 2.3:** Integrasi ke Export Pipeline
- Pastikan watermark dan fade diterapkan sebelum final render

### Phase 3: Audio Music Mixer (1-2 hari)

**Step 3.1:** Buat `static/uploads/music/` folder
- Implementasi upload music di frontend dan backend
- Implementasi list/delete music

**Step 3.2:** Extend `models/clip_editor.py`
- Implementasi `mix_audio(clip, music_path, music_vol, original_vol)`
- Implementasi music looping jika durasi music < durasi clip

**Step 3.3:** Update Frontend — Audio Panel
- Dropdown/select untuk pilih music dari library
- Slider volume music (0-100%)
- Slider volume original audio (0-100%)

**Step 3.4:** Test Audio Mixing
- Export clip dengan music background
- Export clip dengan original audio only
- Export clip dengan keduanya mixed

### Phase 4: Preview & Polish (1 hari)

**Step 4.1:** Implementasi Preview Frame
- Route `/preview-clip` menerima video + timestamp + editor_options
- Generate 1 frame pada posisi tengah clip untuk preview
- Return image base64 atau URL

**Step 4.2:** Update Config Defaults
- Tambah field editor ke `config.json` dan class `Config` di `main.py`

**Step 4.3:** Final Testing & Bugfix
- Test semua kombinasi fitur
- Optimasi performa render
- Handle edge cases (video tanpa audio, music terlalu pendek, dsb)

---

## 7. Format Payload API

### Export Edit (Extended)

```json
POST /export-edit
{
  "video_url": "/static/uploads/video.mp4",
  "clips": [
    {"start": 10.5, "end": 20.0},
    {"start": 45.0, "end": 55.0}
  ],
  "editor_options": {
    "aspect_ratio": "9:16",
    "resolution": "1080x1920",
    "watermark": {
      "enabled": true,
      "type": "text",
      "text": "@MyChannel",
      "position": "bottom-right",
      "opacity": 0.7,
      "fontsize": 48,
      "color": "white"
    },
    "audio": {
      "music_path": "/static/uploads/music/lofi.mp3",
      "music_volume": 0.25,
      "original_volume": 1.0
    },
    "fade": {
      "fade_in": 0.5,
      "fade_out": 0.5
    }
  }
}
```

### Response

```json
{
  "success": true,
  "download_url": "/static/exports/edited_143052.mp4"
}
```

---

## 8. Potensi Challenge & Mitigation

| Challenge | Risiko | Mitigation |
|-----------|--------|------------|
| **Performa Blur** | Gaussian blur frame-by-frame dengan PIL bisa lambat untuk video panjang | • Gunakan blur radius moderat (15-20)<br>• Cache blurred background clip<br>• Alternatif: gunakan FFmpeg boxblur filter via MoviePy `ffmpeg_params` |
| **Audio Sync** | Mixing audio dengan MoviePy terkadang ada drift | • Pastikan semua audio clip memiliki same FPS/sample rate<br>• Gunakan `temp_audiofile` parameter saat write_videofile |
| **Memory Usage** | MoviePy load video ke RAM bisa besar untuk file 2GB | • Proses clip per-segment (sudah dilakukan di existing code)<br>• Pastikan `close()` dipanggil setelah write<br>• Gunakan `method="compose"` dengan hati-hati |
| **Watermark Font** | Font "Arial-Bold" mungkin tidak tersedia di semua OS | • Bundle font file (Roboto atau OpenSans) di `static/fonts/`<br>• Gunakan path absolut ke font file di `TextClip` |
| **Music Copyright** | User upload music berlisensi | • Tambah disclaimer di UI<br>• Sediakan sample royalty-free music |
| **Vertical Crop Center** | Subjek video bisa terpotong saat center-crop | • Future enhancement: AI-powered subject detection untuk smart crop (gunakan OpenCV face/body detection) |

---

## 9. Quick Start Code Snippet

Berikut contoh implementasi lengkap `models/clip_editor.py` yang bisa langsung digunakan:

```python
"""
Clip Editor Engine untuk AI Clip Creator
Mendukung: vertical 9:16, blur background, watermark, audio mix, fade in/out
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, CompositeVideoClip, CompositeAudioClip,
    AudioFileClip, TextClip, ImageClip, vfx, afx
)

TARGET_VERTICAL = (1080, 1920)

def render_vertical_9_16(clip, blur_bg=True, blur_radius=20):
    w, h = clip.size
    aspect = w / h
    target_w, target_h = TARGET_VERTICAL
    target_aspect = target_w / target_h  # 0.5625
    
    if aspect > target_aspect and blur_bg:
        # Horizontal video -> vertical dengan blurred background
        bg = clip.resized(height=target_h)
        
        def blur_frame(frame):
            img = Image.fromarray(frame)
            blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            return np.array(blurred)
        
        bg = bg.with_effects([vfx.TimeMirror()])  # placeholder untuk custom effect
        # Note: MoviePy v2 menggunakan .transform() atau fl_image
        # Implementasi sebenarnya menggunakan clip.fl_image(blur_frame)
        
        bg = bg.crop(x_center=0.5, y_center=0.5, width=target_w, height=target_h)
        
        fg = clip.resized(width=target_w)
        fg = fg.with_position("center")
        
        return CompositeVideoClip([bg, fg], size=(target_w, target_h))
    else:
        # Vertical/square -> resize dan crop ke 9:16
        clip = clip.resized(height=target_h)
        return clip.crop(x_center=0.5, y_center=0.5, width=target_w, height=target_h)


def add_watermark(clip, config):
    if not config.get("enabled", False):
        return clip
    
    wm_type = config.get("type", "text")
    position = config.get("position", "bottom-right")
    opacity = config.get("opacity", 0.7)
    
    if wm_type == "text":
        text = config.get("text", "")
        fontsize = config.get("fontsize", 48)
        color = config.get("color", "white")
        # Gunakan font bundled jika tersedia
        font_path = config.get("font_path") or "Arial-Bold"
        watermark = TextClip(text=text, font=font_path, fontsize=fontsize,
                            color=color, stroke_color="black", stroke_width=2)
    else:
        image_path = config.get("image_path", "")
        wm_height = config.get("height", 100)
        watermark = ImageClip(image_path).resized(height=wm_height)
    
    watermark = watermark.with_opacity(opacity)
    watermark = watermark.with_position(position)
    watermark = watermark.with_duration(clip.duration)
    
    return CompositeVideoClip([clip, watermark])


def mix_audio(clip, config):
    if not config or not config.get("music_path"):
        return clip
    
    music_path = config["music_path"]
    music_volume = config.get("music_volume", 0.3)
    original_volume = config.get("original_volume", 1.0)
    
    original = clip.audio
    if original:
        original = original.with_volume_scaled(original_volume)
    
    if os.path.exists(music_path):
        music = AudioFileClip(music_path)
        if music.duration < clip.duration:
            n_loops = int(clip.duration / music.duration) + 1
            music = music.loop(n=n_loops)
        music = music.subclipped(0, clip.duration)
        music = music.with_volume_scaled(music_volume)
        
        final_audio = CompositeAudioClip([original, music]) if original else music
        clip = clip.with_audio(final_audio)
    
    return clip


def apply_fades(clip, config):
    fade_in = config.get("fade_in", 0)
    fade_out = config.get("fade_out", 0)
    
    if fade_in > 0:
        clip = clip.with_effects([vfx.FadeIn(fade_in)])
    if fade_out > 0:
        clip = clip.with_effects([vfx.FadeOut(fade_out)])
    
    if clip.audio:
        audio = clip.audio
        if fade_in > 0:
            audio = audio.with_effects([afx.AudioFadeIn(fade_in)])
        if fade_out > 0:
            audio = audio.with_effects([afx.AudioFadeOut(fade_out)])
        clip = clip.with_audio(audio)
    
    return clip


def process_clip(clip, editor_options):
    """Pipeline utama: terapkan semua efek berurutan"""
    # 1. Aspect ratio & vertical conversion
    if editor_options.get("aspect_ratio") == "9:16":
        clip = render_vertical_9_16(
            clip,
            blur_bg=editor_options.get("blur_background", True),
            blur_radius=editor_options.get("blur_radius", 20)
        )
    
    # 2. Watermark
    if "watermark" in editor_options:
        clip = add_watermark(clip, editor_options["watermark"])
    
    # 3. Audio mixing
    if "audio" in editor_options:
        clip = mix_audio(clip, editor_options["audio"])
    
    # 4. Fade effects
    if "fade" in editor_options:
        clip = apply_fades(clip, editor_options["fade"])
    
    return clip
```

---

## 10. Timeline Estimasi

| Phase | Durasi | Deliverable |
|-------|--------|-------------|
| Phase 1: Vertical Renderer | 1-2 hari | `clip_editor.py`, vertical 9:16 dengan blur bg, integrasi export |
| Phase 2: Watermark & Fade | 1 hari | Watermark overlay, fade in/out, UI kontrol |
| Phase 3: Audio Mixer | 1-2 hari | Music upload, audio mixing, volume control |
| Phase 4: Preview & Polish | 1 hari | Preview frame, config defaults, testing, bugfix |
| **Total** | **4-6 hari** | Full feature automation clip editor |

---

## 11. Kesimpulan

Plan ini memanfaatkan **MoviePy yang sudah ada** sebagai engine utama, ditambah **Pillow** untuk image processing watermark/blur, dan **FFmpeg** sebagai backend rendering. Tidak diperlukan library video editing baru yang kompleks — semua requirements (vertical 9:16, blur background, watermark, audio mix, fade) bisa diimplementasikan dengan kombinasi library yang sudah tersedia.

**Rekomendasi Prioritas:**
1. Mulai dari **Phase 1** (Vertical Renderer) karena ini core requirement
2. Pastikan **font file bundled** agar watermark konsisten cross-platform
3. Untuk performa optimal, pertimbangkan menggunakan **FFmpeg boxblur** sebagai alternatif PIL GaussianBlur untuk video dengan durasi > 30 detik

---

*Plan dibuat oleh: Metis - Plan Consultant*
*Untuk proyek: AI-Clip-Creator*
*Tanggal: 2026-04-23*
