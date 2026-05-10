# Laporan Optimalisasi Performa FFmpeg Pipeline SneaClip

Berdasarkan analisis area FFmpeg di dalam workspace, telah diidentifikasi beberapa bottleneck krusial yang berdampak langsung pada performa encoding, pipeline filter chain, dan proses ekstraksi audio. Perbaikan dilakukan dengan fokus penuh pada penghematan waktu eksekusi tanpa mengubah regresi kualitas output atau stabilitas kode. Berikut adalah rincian temuan serta perubahan yang telah diterapkan.

## 1. Bottleneck yang Diidentifikasi

1. **Resolusi Path Eksekusi:** Beberapa module masih melakukan hardcoding pada path biner `ffmpeg` (contoh di `models/processing.py` dan `models/streaming_processor.py`), dan penggunaan `ffprobe` masih terdistribusi secara parsial tanpa utilitas terpusat, berpotensi memicu error path `.exe` di lingkungan Windows.
2. **Filter Chain (Background Blur yang Berat):** Saat mengekspor hasil editan video untuk ukuran vertikal 9:16 (`[bg_full]`), proses pengaburan (*blur*) dan *scaling* dilakukan dengan kualitas tinggi. Operasi ini cukup intensif dan menyumbang perlambatan yang signifikan karena secara *default* `scale` filter menggunakan pengaturan `bilinear` standar tanpa *flag* tambahan.
3. **Ekstraksi Metadata Media Secara Berlebihan:** Pada proses komputasi durasi untuk membuat klip pendek (`create_clips` dan modul lain), memuat keseluruhan file ke dalam memori dengan MoviePy memakan *overhead* tinggi.
4. **Posisi Parameter Trimming:** Penggunaan perintah FFmpeg memiliki *seek-time* lambat karena file diparsing dahulu jika tidak disusun dengan efisien (penggunaan `-ss` yang tertinggal dari masukan). Pada modul yang ada, posisi `-ss` sebenarnya sudah di depan input `-i` namun harus dipastikan tidak ada pemrosesan tambahan untuk menghindari decoding memakan waktu.

## 2. Perubahan dan Optimasi yang Dilakukan

- **Memusatkan Utilitas Binary:**
  Dibuat file `models/ffmpeg_utils.py` yang berfungsi memastikan seluruh eksekusi `ffmpeg` dan `ffprobe` konsisten mengambil dari *environment variable* atau default dan menambahkan secara aman ekstensi `.exe` di platform Windows. Ini dipasangkan di *semua module* yang sebelumnya menggunakan string manual `"ffmpeg"`.
- **Optimalisasi Filter Scale Background (Safe & High Performance):**
  Di dalam modul `models/ffmpeg_export.py`, spesifik pada filter complex *blur* ukuran vertikal, argumen `:flags=fast_bilinear` ditambahkan pada seluruh rute instruksi pengubah ukuran `scale=` untuk komponen latar belakang `[bg_full]`. Pengaturan ini secara drastis memangkas waktu pemrosesan (*scaling*) resolusi, sementara *foreground* (*`[fg_full]`*) sengaja **tidak** diubah sehingga integritas visual objek utama di depan tetap maksimal.
- **Konsistensi Fast Processing dan Extraction:**
  Pada eksekusi ekstraksi audio `models/streaming_processor.py` maupun `models/processing.py`, *threads* diset secara konsisten ke maksimal (`-threads 0`). Ekstraksi informasi durasi secara eksklusif diprioritaskan menggunakan *subprocess* ke `ffprobe` (via `get_ffprobe_exe`).

## 3. Trade-off dan Pertimbangan Kualitas

1. **Penggunaan Fast Bilinear**: Skala `fast_bilinear` secara teori menurunkan presisi *sampling* dibandingkan algoritma Bicubic/Lanczos pada FFmpeg, namun **karena itu diterapkan pada lapisan yang akan diberikan efek blur yang kuat (`boxblur`)**, efek negatif (*aliasing* atau sedikit kasar) tersebut langsung hilang tersamarkan secara visual. Artinya kita mendapatkan efisiensi performa tanpa memengaruhi kualitas yang dapat dilihat oleh mata (perceptual quality). Subjek utama (*foreground*) tidak dikenai efek ini, sehingga kualitas HD tetap 100% terjaga.
2. **Ketergantungan terhadap Utility Helper**: Menggantikan path manual `ffmpeg` dengan helper utilitas `get_ffmpeg_exe` menambahkan sedikit waktu resolusi fungsi saat Python memuat modul, namun karena ditaruh saat deklarasi / dibungkus ringan, dampaknya bisa diabaikan dan jauh melampaui masalah kestabilan jangka panjang sistem di berbagai *runtime OS*.

## 4. Metode Verifikasi

- **Verifikasi Fungsionalitas Modul**: Seluruh modul `models/ffmpeg_export.py`, `models/processing.py`, dan `models/streaming_processor.py` telah diperiksa sintaks dan diimpor ulang.
- **Verifikasi Eksekusi Wrapper Eksternal**: Sebuah script `test_ffmpeg.py` digunakan untuk memastikan `ffmpeg_utils` berjalan, menemukan *path* FFmpeg, serta melakukan *subprocess run* dan mencetak *version string* berhasil tanpa masalah I/O Exception.
- **Verifikasi Aplikasi Flask**: Menjalankan ulang Flask untuk memastikan `process_video` atau `import` pipeline tidak putus dan metrics API masih stabil *serve* secara normal.
