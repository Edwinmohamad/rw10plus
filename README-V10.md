# RW10+ v10 — Full UI Rebuild

Versi ini merombak UI nyata, bukan mockup dan bukan sekadar stylesheet tambahan.

## URL setelah deploy
- Internal / PWA / target APK WebView: `http://SERVER:8188/`
- Website publik: `http://SERVER:8080/`
- CMS publik: `http://SERVER:8080/admin.html`

## Perubahan utama
### Internal :8188 — Neighborhood OS
- Desktop memakai navigation rail kiri; mobile tetap bottom navigation.
- Beranda dirombak menjadi dashboard: welcome panel, status keamanan, KPI, layanan cepat, feed lingkungan, SOS, dan panel petugas.
- Light/Dark dan Mode Lansia tetap didukung.
- Tidak mengubah kontrak API, RBAC, isolasi RT, SOS, surat, iuran, guest pass, patrol, voting, dan endpoint backend.

### Public :8080 — Apple Civic Motion
- Header, hero, layanan, statistik agregat, RT switcher, berita, WiFi Pelajar, UMKM, galeri, footer, dan dark mode dirombak.
- Tetap memakai CMS publik untuk konten dinamis.
- Data pribadi tidak dipindahkan ke website publik.

## CMS bootstrap
Deployment tidak membutuhkan `.env` untuk start awal.
Password bootstrap sementara: `RW10Admin2026!`
Ganti setelah sistem stabil.

## Pengujian yang dijalankan
- Python compile
- UI contract
- RT isolation
- Backend smoke test
- CMS login/startup tanpa `.env`
- JavaScript syntax checks
- HTML parser checks
- Android XML parse
- Android API 27 attribute tetap berada di `values-v27`

Gradle APK final tidak dijalankan lokal karena environment build ini tidak memiliki Android SDK/Gradle. Workflow GitHub Actions tetap menjadi validasi final APK.
