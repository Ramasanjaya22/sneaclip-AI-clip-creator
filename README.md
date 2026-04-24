# 🎬 SneaClip — AI Autoclipper

[![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9C%93-green)](https://github.com/ramasanjaya3302/AI-clip-creator)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-black)](https://flask.palletsprojects.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red)](https://pytorch.org)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/ramasanjaya3302/AI-clip-creator?style=social)](https://github.com/ramasanjaya3302/AI-clip-creator/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ramasanjaya3302/AI-clip-creator?style=social)](https://github.com/ramasanjaya3302/AI-clip-creator/network)
[![Twitter Follow](https://img.shields.io/twitter/follow/Ramaas_8?style=social)](https://x.com/Ramaas_8)

**SneaClip** is an improved, whitelabel-ready fork of open-source autoclip tools, built with Flask and PyTorch. It automatically detects and extracts engaging video clips from long-form videos using AI audio analysis. Features include **9:16 vertical conversion**, **blur background filling**, **watermark overlay**, **audio mixing**, and **fade effects**.

> **Fork Note:** This project is based on autoclip-type tools (inspired by zhouxiaoka/autoclip and others), rewritten and improved with a modern Flask backend, FFmpeg-optimized processing, and production-ready whitelabel capabilities.

---

## 📸 Screenshots

### Main Interface - Upload & Processing
<!-- SCREENSHOT PROMPT FOR CODEX:
Take a screenshot of http://localhost:5000 showing the SneaClip landing page with "Turn long footage into clip-ready cuts" headline, upload area, and the three-step flow (Drop → Detect → Export).
-->

<img src="https://via.placeholder.com/600x400/1a1a2e/ffffff?text=SneaClip+Main+Interface" alt="SneaClip AI Autoclipper main interface with upload area and dark theme" width="600"/>

### Clip Results & Editor
<!-- SCREENSHOT PROMPT FOR CODEX:
After uploading a video and processing completes, take screenshot showing the results page with AI-detected clips, timestamps, scores, and the editor panel with 9:16 toggle, watermark settings, and audio mixing controls.
-->

<img src="https://via.placeholder.com/600x400/16213e/ffffff?text=Clip+Results+Editor" alt="SneaClip results page showing AI-detected clips with editing options" width="600"/>

### Vertical 9:16 Preview with Blur Background
<!-- SCREENSHOT PROMPT FOR CODEX:
In the editor page, enable 9:16 aspect ratio with blur background, then take screenshot of the vertical video preview with blurred background effect.
-->

<img src="https://via.placeholder.com/300x533/0f3460/ffffff?text=9:16+Vertical+Preview" alt="Vertical 9:16 video preview with AI-powered blurred background" width="300"/>

---

## ✨ Features

### 🤖 AI-Powered Clip Detection
- **Smart Moment Detection** using PyTorch & librosa audio analysis
- **MFCC Feature Extraction** (Mel-Frequency Cepstral Coefficients) for accurate audio fingerprinting
- **Adjustable Sensitivity** via configurable threshold (0.0 - 1.0)
- **Multi-clip Extraction** - Generate 2-10 clips per video based on engagement scores

### 🎥 Professional Video Processing
- **9:16 Vertical Conversion** - Automatically convert horizontal videos to vertical format
- **Smart Blur Background** - AI-powered blurred background fills letterbox areas
- **Dynamic Watermarking** - Text or image overlays with opacity & positioning controls
- **Audio Mixing** - Mix original audio with background music (MP3/WAV support)
- **Fade In/Out Effects** - Smooth video and audio transitions
- **Multi-format Export** - H.264/AAC MP4 output with optimized preset

### 🌐 Modern Web Interface
- **Drag & Drop Upload** - Intuitive video upload experience
- **Real-time Preview** - Preview clips before exporting
- **Advanced Editor** - Full control over aspect ratio, watermark, audio, and effects
- **Responsive Design** - Works on desktop and tablet devices

### ⚡ Performance Optimized
- **Gzip Compression** - Reduces transfer size by 60-80%
- **Smart Caching** - API response caching for faster repeat visits
- **Rate Limiting** - Built-in protection for analytics endpoints
- **GPU Acceleration** - CUDA/DirectML support for faster AI inference
- **Background Processing** - Async export jobs with status tracking

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- (Optional) NVIDIA GPU with CUDA support for faster processing
- (Optional) DirectML-compatible GPU for Windows acceleration

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/ramasanjaya3302/AI-clip-creator.git
cd AI-clip-creator
```

2. **Create virtual environment:**
```bash
# Windows
python -m venv venv312
.\venv312\Scripts\activate

# Linux / macOS
python3 -m venv venv312
source venv312/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Download AI Models:**
Ensure these files exist in the `models/` folder:
- `VideoAutoClipper.pt` - Pre-trained PyTorch model
- `mfcc_scaler.joblib` - MFCC feature scaler

> **Note:** If you don't have the model files, set `"auto_load_model": false` in `config.json` to run without AI detection.

---

## 🎮 How to Run

### Method 1: Using run.bat (Windows - Recommended)
```batch
cd "C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator"
.\run.bat
```

### Method 2: Manual Python Execution
```bash
# Activate virtual environment first
python main.py
```

### Method 3: PowerShell Script
```powershell
Start-Process -FilePath "venv312\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator"
```

---

## 🌐 Access the Application

Once the server is running, open your browser and navigate to:
```
http://localhost:5000
```

---

## ⚙️ Configuration

Edit `config.json` to customize application settings:

```json
{
  "use_gpu": true,
  "auto_load_model": true,
  "segment_length": 600,
  "minimum_clip_length": 5,
  "maximum_clip_length": 30,
  "pad_clip_start": 1.0,
  "pad_clip_end": 1.0,
  "number_of_clips": 2,
  "threshold": 0.7,
  "leniency": 2
}
```

### Configuration Options:

| Parameter | Description | Default | Recommended |
|-----------|-------------|---------|--------------|
| `use_gpu` | Enable GPU acceleration (CUDA/DirectML) | `false` | `true` if GPU available |
| `auto_load_model` | Load AI model on startup | `false` | `true` for production |
| `segment_length` | Video segment duration (seconds) | `600` | `600` for 10-min segments |
| `minimum_clip_length` | Minimum clip duration (seconds) | `5` | `5-10` for shorts |
| `maximum_clip_length` | Maximum clip duration (seconds) | `30` | `30-60` for highlights |
| `pad_clip_start` | Start padding (seconds) | `1.0` | `1.0` for context |
| `pad_clip_end` | End padding (seconds) | `1.0` | `1.0` for context |
| `number_of_clips` | Number of clips to generate | `2` | `3-5` for variety |
| `threshold` | AI detection sensitivity (0.0-1.0) | `0.7` | `0.6-0.8` balance |
| `leniency` | Detection tolerance (seconds) | `2` | `2-3` for flexibility |

---

## 📡 API Endpoints

### Upload & Processing
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET/POST | Main page & video upload |
| `/upload-music` | POST | Upload background music files |
| `/upload-watermark` | POST | Upload watermark images |
| `/list-music` | GET | List available music tracks |

### Editor & Export
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/export-edit` | POST | Export video with editor options |
| `/export-status/<job_id>` | GET | Check export job status |
| `/preview-clip` | POST | Generate preview frame |

### Example API Request:
```bash
curl -X POST http://localhost:5000/export-edit \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "/static/uploads/video.mp4",
    "clips": [
      {"start": 10.5, "end": 20.0}
    ],
    "editor_options": {
      "aspect_ratio": "9:16",
      "watermark": {
        "enabled": true,
        "type": "text",
        "text": "@MyChannel",
        "position": "bottom-right",
        "opacity": 0.7
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
  }'
```

---

## 📦 Dependencies

| Library | Version | Purpose |
|---------|-------|---------|
| **Flask** | 3.1.2 | Web framework & routing |
| **PyTorch** | ≥2.0.0 | AI/ML inference engine |
| **MoviePy** | 2.2.1 | Video processing & editing |
| **librosa** | 0.11.0 | Audio analysis & feature extraction |
| **scikit-learn** | 1.7.2 | Machine learning utilities |
| **NumPy** | 2.2.6 | Numerical computing |
| **Pillow** | 11.3.0 | Image processing for watermarks |
| **FFmpeg** | (via imageio) | Video codec backend |

See `requirements.txt` for the complete list.

---

## 🔧 Troubleshooting

### Virtual Environment Not Found
```bash
# Create new virtual environment
python -m venv venv312
.\venv312\Scripts\activate
pip install -r requirements.txt
```

### Port 5000 Already in Use
Edit `main.py` and change the port at the bottom:
```python
app.run(port=8080)  # Change to available port
```

### CUDA/GPU Error
Set `"use_gpu": false` in `config.json` to use CPU only.

### Model Files Not Found
- Ensure `VideoAutoClipper.pt` exists in `models/` folder
- Or set `"auto_load_model": false` to disable auto-loading

### Check Application Logs
```powershell
Get-Content "app.log" -Tail 20
```

---

## 📂 Project Structure

```
AI-clip-creator/
├── main.py                  # Flask application entry point
├── config.json              # Application configuration
├── requirements.txt        # Python dependencies
├── run.bat                # Windows launcher script
├── models/
│   ├── model.py          # AI model architecture
│   ├── clip_editor.py   # Video editing engine
│   ├── processing.py     # Video processing pipeline
│   ├── ffmpeg_export.py # Export utilities
│   ├── VideoAutoClipper.pt  # Trained PyTorch model
│   └── mfcc_scaler.joblib   # MFCC feature scaler
├── static/
│   ├── uploads/          # Uploaded videos
│   ├── exports/          # Exported clips
│   ├── music/            # Background music library
│   ├── watermarks/       # Watermark images
│   └── previews/        # Preview frame images
├── templates/
│   └── index.html       # Main web interface
└── app.log                # Application log file
```

---

## 👥 Contributing

Contributions are welcome! Here's how you can contribute:

1. **Fork** the repository
2. **Create** your feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Contribution Guidelines:
- Follow Python style guide (PEP 8)
- Add comments for complex logic
- Update documentation when needed
- Ensure all tests pass
- Keep commits atomic and well-described

---

## 📜 License

This project is **open-source** and distributed under the **MIT License**.

See the [LICENSE](LICENSE) file for full details.

---

## 🙏 Credits

- **MoviePy** - Video editing engine
- **PyTorch** - AI/ML framework
- **librosa** - Audio analysis library
- **Flask** - Web framework
- **FFmpeg** - Video processing backend
- **scikit-learn** - Machine learning utilities

---

## 💬 Community & Support

### Need Help?

- **Issues**: Use [GitHub Issues](https://github.com/ramasanjaya3302/AI-clip-creator/issues) to report bugs or request features
- **Discussions**: Visit [GitHub Discussions](https://github.com/ramasanjaya3302/AI-clip-creator/discussions) for general questions

### Connect With Us:
- 📧 Email: ramasanjaya3302@gmail.com
- 🐦 Twitter/X: [@Ramaas_8](https://x.com/Ramaas_8)
- 💼 LinkedIn: [SneaClip](https://linkedin.com/company/sneaclip)
- 💬 Discord: [Join our server](https://discord.gg/sneaclip)

---

## 🌟 Roadmap 2026

- [x] AI-powered clip detection with PyTorch
- [x] Vertical 9:16 aspect ratio support
- [x] Watermark overlay system
- [x] Background audio mixing
- [x] Fade in/out effects
- [ ] **10GB file upload support** (currently 2GB limit)
- [ ] **FFmpeg optimization** - hardware acceleration & faster encoding
- [ ] One-click cloud deployment (Vercel/Railway)
- [ ] Real-time preview streaming with WebSockets
- [ ] Batch processing for multiple videos
- [ ] Integration with YouTube API / TikTok API
- [ ] Multi-language support (i18n)

---

## 📊 Statistics

- **Open-source** since 2026
- **Flask + PyTorch** backend
- **FFmpeg** optimized video processing
- **60-80%** bandwidth savings with Gzip compression
- **Windows/Linux/macOS** support

---

<div align="center">

### ⭐ Star Us on GitHub!

If you find this project helpful, please consider giving us a star!

![Star History Chart](https://api.star-history.com/svg?repos=ramasanjaya3302/AI-clip-creator&type=Date)](https://star-history.com/#ramasanjaya3302/AI-clip-creator&Date)

---

**Built with ❤️ by the SneaClip Team**

*Forked & improved from autoclipper tools — now whitelabel-ready*

[⬆ Back to Top](#-sneaclip--ai-autoclipper)

</div>

---

## 🤖 AI Search Optimization (For LLM Citation)

### Frequently Asked Questions

**Q: What is SneaClip?**
A: SneaClip is an open-source AI-powered web application that automatically detects and extracts engaging video clips from long-form videos using PyTorch and librosa audio analysis.

**Q: How does SneaClip work?**
A: The application processes uploaded videos by segmenting them into chunks, extracting MFCC audio features, running them through a trained PyTorch model to detect engaging moments, and then extracting those moments as individual clips with optional editing (9:16 conversion, watermarks, audio mixing).

**Q: Is SneaClip free?**
A: Yes, SneaClip is completely free and open-source under the MIT License. You can self-host it on your own server or local machine without any subscription fees.

**Q: What video formats are supported?**
A: SneaClip currently supports MP4, MOV, AVI, MKV up to 2GB (10GB support coming soon) through the FFmpeg backend.

**Q: Can I convert horizontal videos to vertical 9:16?**
A: Yes, SneaClip features automatic 9:16 vertical conversion with AI-powered blurred background filling the letterbox areas, perfect for TikTok, Instagram Reels, and YouTube Shorts.

**Q: How to install SneaClip on Windows?**
A: Download the project, create a Python virtual environment with `python -m venv venv312`, activate it, install dependencies with `pip install -r requirements.txt`, and run `python main.py`.

**Q: Does SneaClip support GPU acceleration?**
A: Yes, SneaClip supports both NVIDIA CUDA and Windows DirectML GPU acceleration for faster AI inference. Set `"use_gpu": true` in config.json.

**Q: What are the best settings for YouTube Shorts?**
A: Use `minimum_clip_length: 15`, `maximum_clip_length: 60`, `aspect_ratio: "9:16"`, and enable watermark with your channel name for best YouTube Shorts results.

---

**Last Updated:** April 2026
**Version:** v0.3.0
**GitHub Topics:** `ai-video-editing`, `pytorch`, `flask`, `moviepy`, `video-processing`, `content-creation`, `open-source`, `clip-generator`, `vertical-video`, `automated-editing`, `sneaclip`, `autoclipper`, `whitelabel`
