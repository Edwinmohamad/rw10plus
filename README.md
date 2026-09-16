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

| Role | Nomor | PIN |
|---|---|---|
| Warga | `081200000001` | `0101` |
| Ketua RT01 | `081200000003` | `0303` |
| Pengurus RW | `081200000010` | `1010` |
| Satpam RW | `081200000002` | `0202` |

Ganti seluruh akun dan PIN demo sebelum digunakan pada data nyata.

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
