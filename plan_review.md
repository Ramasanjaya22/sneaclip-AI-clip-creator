# Temuan Utama
1. **Hero Visual Overflow/Overlap:**
   - `hero-floating-card--clip` menutupi teks penting pada `hero-screen-sidebar` di sisi kanan layar.
   - `hero-floating-card--stack` menutupi image preview pada layar kecil dan terlihat berantakan pada desktop (keluar batas di sebelah kiri).
   - Mockup image pada `.hero-screen-preview img` dan `.hero-floating-card--stack img` tidak dimuat dengan sempurna atau tertutup.
2. **Typography & Button Hierarchy:**
   - Button "See the flow" terlihat sedikit pudar dan kurang kontras dengan background (`opacity: 0.9` dan `btn-secondary`).
   - Font padding/margins pada landing chips dan buttons bisa diperbaiki.
3. **Spacing & Alignment:**
   - Ada spacing issue pada bagian `landing-upload` area drop zone, dimana element terlihat padat.
   - `hero-stage` aspect ratio dan padding bisa diperbaiki agar gambar tidak terlalu mepet dengan batas.
4. **Color usage:**
   - Background gradient hero terlalu dominan, bisa diringankan agar konten (text & gambar) lebih stand out.

# Perbaikan yang Disarankan
1. **Perbaikan Layout `hero-stage` (Hero Visual):**
   - Menyesuaikan posisi `.hero-floating-card--clip` (misal, pindahkan sedikit ke kanan bawah, jangan menutupi teks penting).
   - Menyesuaikan posisi `.hero-floating-card--stack` (pindahkan lebih ke kiri atas, agar tidak memotong isi utama layar).
   - Mengubah `object-fit` pada image preview jika diperlukan agar tidak tertutup konten melayang.

2. **Perbaikan Styling Buttons dan UI Elements:**
   - Hapus inline styles yang tidak perlu dari `btn-hero-start` dan `btn-hero-preview`.
   - Gunakan utility classes dan CSS tokens yang sudah ada (seperti `var(--space-*)` dan `var(--fluid-*)`) untuk typography.

3. **Perbaikan CSS pada `static/style.css` (Visual Polish):**
   - Rapikan padding/margin `landing-actions` dan `landing-chips`.
   - Rapikan responsive behaviour untuk layar tablet/mobile, agar floating cards menghilang (`display: none`) atau mengecil proporsional jika layar sempit agar tidak menghalangi gambar utama.

# Kenapa bernilai?
- **Clarity & Usability:** Menyembunyikan atau memperbaiki posisi elemen yang tumpang tindih akan meningkatkan keterbacaan (readability).
- **Modern & Rapi:** Penggunaan design tokens untuk padding dan typography memastikan konsistensi visual.
- **Trust:** Tampilan hero image yang clean memberikan kesan profesional dan modern kepada pengguna pertama yang mengunjungi aplikasi.

Mohon tinjau.
