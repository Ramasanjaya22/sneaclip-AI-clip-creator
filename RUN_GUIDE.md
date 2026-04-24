# AI Clip Creator - Panduan Menjalankan Proyek

## Deskripsi Singkat
AI Clip Creator adalah aplikasi web berbasis Flask untuk membuat klip video/audio otomatis menggunakan AI (PyTorch, MoviePy, librosa).

---

## Cara Menjalankan Aplikasi

### Metode 1: Menggunakan run.bat (Recommended)
```batch
cd "C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator"
.\run.bat
```

### Metode 2: Manual via Virtual Environment
```powershell
cd "C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator"
.\venv312\Scripts\python.exe main.py
```

### Metode 3: PowerShell Script
```powershell
Start-Process -FilePath "venv312\Scripts\python.exe" -ArgumentList "main.py" -WorkingDirectory "C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator"
```

---

## Akses Aplikasi
Setelah server berjalan, buka browser dan kunjungi:
```
http://localhost:5000
```

---

## Konfigurasi (config.json)
```json
{
  "use_gpu": true,
  "auto_load_model": true,
  "segment_length": 600,
  "minimum_clip_length": 5,
  "maximum_clip_length": 9,
  "pad_clip_start": 1.0,
  "pad_clip_end": 1.0,
  "number_of_clips": 2,
  "threshold": 0.7,
  "leniency": 2
}
```

---

## Dependencies Utama
- Flask 3.1.2 - Web framework
- PyTorch >=2.0.0 - AI/ML backend
- MoviePy 2.2.1 - Video processing
- librosa 0.11.0 - Audio analysis
- NumPy, SciPy, scikit-learn - Numerical computing

---

## Menhentikan Aplikasi
Tekan `CTRL+C` di jendela terminal yang menjalankan aplikasi.

Atau via PowerShell:
```powershell
Stop-Process -Name python -Force
```

---

## Log File
Log aplikasi tersimpan di:
```
C:\Users\ramas\Downloads\v0.3.0-windows\AI-clip-creator\app.log
```

Cek log terbaru:
```powershell
Get-Content "app.log" -Tail 20
```

---

## Fitur Endpoints
- `GET /` - Halaman utama
- `POST /upload` - Upload video
- `POST /preview-clip` - Preview klip
- `POST /export-edit` - Export hasil edit
- `GET /list-music` - Daftar musik
- `POST /metrics` - Web performance metrics

---

## Troubleshooting

### Virtual environment tidak ditemukan
Jalankan `installer.bat` untuk membuat virtual environment dan menginstall dependencies.

### Port 5000 sudah digunakan
Edit `main.py` dan ubah port di akhir file:
```python
app.run(host='127.0.0.1', port=5000, debug=False)
```

### CUDA/GPU error
Set `"use_gpu": false` di `config.json` untuk menggunakan CPU saja.
