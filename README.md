# RW10+ — Testing lokal v6.0

Versi testing terbaru beserta UI editorial berada di [`localhost-v6`](localhost-v6/README-MULAI-DISINI.txt).

```bash
cd localhost-v6
docker compose up -d --build
```

Buka `http://IP-SERVER:8097`, Control Center di `/#/admin`, dan Ruang Warga di `/#/warga`. Untuk Windows, jalankan `localhost-v6/start-windows.bat` (Node.js 22.13+ atau Node.js 24).

Backend ini memakai Node.js + SQLite, berbeda dari backend Python lama di root. Data dan akun lama belum dimigrasikan otomatis. Jangan menyalin database Python ke volume v6. Database dan kredensial hasil testing tidak disertakan dalam source. APK lama tetap menunjuk ke layanan lama; belum diubah oleh pembaruan UI ini.

Validasi: sintaks JavaScript, respons halaman/aset, API publik dan penolakan akses anonim ke API pengelolaan lolos. Uji visual browser dan Docker build belum dijalankan. Lihat `localhost-v6/VALIDASI-UI.txt`.

---

## Dokumentasi aplikasi Python sebelumnya

# RW10+ Internal v0.3.0

Aplikasi Smart Neighborhood lokal untuk RW10 (RT01–RT04) dengan empat role: Warga, Ketua RT, Pengurus RW, dan Satpam RW.

## Fitur aktif

- SOS public/silent: hold 3 detik, cancel window 10 detik, respons dan penyelesaian petugas.
- Snap & Fix dengan state machine status laporan.
- Iuran warga dan pengiriman referensi bukti bayar.
- Surat digital: Warga → Ketua RT → Pengurus RW → nomor surat/verifikasi.
- Guest Pass sementara dan validasi satu kali oleh Satpam/Pengurus.
- Check-in patroli digital, dashboard CCTV simulasi, kegiatan, organisasi, UMKM, dan e-voting 1 rumah 1 suara.
- RBAC empat role, audit log, idempotensi SOS, Light Mode, Dark OLED, dan Mode Lansia.

## Instalasi server lokal

```bash
tar -xzf RW10PLUS-v0.3.0.tar.gz
cd rw10plus-v0.3.0
bash install.sh
```

Buka `http://192.168.100.50:8188`. Installer menyalin database dari container v0.2/v0.1 bila tersedia dan membuat backup sebelum migrasi.

## Akun pilot

Kelola kredensial pilot secara privat dan ganti kredensial demo sebelum penggunaan nyata.

## Pengujian

```bash
python3 tests/ui_contract_test.py
python3 tests/smoke_test.py
```

## APK internal

APK adalah secure WebView shell yang menunjuk ke server lokal `192.168.100.50:8188`.

```bash
cd android-client
sudo ./build-apk.sh
```

Output: `android-client/output/RW10PLUS-INTERNAL-v0.3.0.apk`.

Jika source disimpan di GitHub, workflow **Build RW10+ Internal APK** otomatis melakukan lint dan menyediakan APK pada menu Actions → Artifacts. APK Play Store tetap harus ditandatangani dengan release keystore milik RW10.

## Batas produksi saat ini

- TOA, CCTV RTSP, QR camera scanner, barrier gate, FCM/DND, PDF bertanda tangan, GPS geofence, n8n, dan WhatsApp masih adapter/simulasi.
- Polling 4 detik dipakai untuk realtime lokal. Migrasi produksi tersedia di `infrastructure/supabase/schema.sql`.
- Aplikasi pilot ini tidak menggantikan nomor darurat 110/112/119.
