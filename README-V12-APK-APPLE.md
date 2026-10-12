# Cicadas Digital v12 — APK Apple UI Rebuild

Baseline: v11 Desa Digital. Fokus rilis ini adalah tampilan APK/WebView pada `:8188`.

## UI APK
- Mobile UI dibangun ulang mengikuti referensi pengguna: header ringkas, hero foto lingkungan, shortcut layanan 4x2, feed berita dengan thumbnail, CCTV preview cards, profil warga, dan bottom navigation 5 menu.
- Bottom navigation: Beranda, Layanan, CCTV, Berita, Profil.
- Light/Dark toggle tersedia langsung di header. Profil tetap menyediakan pilihan Light / Dark / System.
- Android system status/navigation bar mengikuti tema melalui bridge terbatas `AndroidTheme.setTheme()`.
- Tampilan desktop `:8188` tetap memakai dashboard existing; layer redesign difokuskan ke viewport APK/mobile.

## WiFi Gratis Pelajar
- Shortcut di Beranda dan menu di Layanan.
- Halaman registrasi menyimpan: nama pelajar, sekolah, kelas, nomor kartu pelajar/NIS opsional, nomor HP, alamat, dan RT akun.
- NIK/KK tidak diminta.
- Endpoint: `POST /api/wifi-student/register`.
- Data hanya dikembalikan ke pemilik akun melalui bootstrap sebagai `wifi_registration`.
- Status awal: `menunggu_verifikasi`. Workflow verifikasi/aktivasi oleh admin belum ditambahkan pada rilis ini.

## Android
- `versionCode 7`
- `versionName 0.6.0-cicadas`
- Artifact GitHub Actions: `CICADAS-DIGITAL-v0.6.0.apk`
- API 26 tetap didukung; `windowLightNavigationBar` hanya berada di `values-v27`.

## Cache
Service Worker dinaikkan ke `cicadas-digital-v12` dan aset baru ikut diprecache. Setelah deploy lama, refresh/reopen APK bila WebView masih menyimpan tampilan sebelumnya.

## Validasi yang dijalankan
- Python compile
- JavaScript syntax
- UI contract
- RT isolation
- backend smoke test
- WiFi Pelajar API smoke test
- HTML local asset references
- YAML parse (Compose + workflows)
- Android XML parse dan API 26/27 style split

Gradle build penuh tidak dijalankan lokal karena Android SDK/Gradle tidak tersedia di environment pengerjaan. GitHub Actions tetap menjadi validasi final `lintDebug assembleDebug`.
