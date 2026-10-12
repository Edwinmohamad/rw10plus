# RW10+ Full Patch v9 — Apple Edition

## Isi utama
- Website publik + halaman RT + CMS v8 tetap tersedia.
- Website publik diberi refinement Apple-inspired untuk light/dark mode.
- Portal CMS diberi refinement UI agar lebih konsisten.
- Aplikasi internal/PWA dirombak visual total menggunakan Apple-inspired UI tanpa mengubah kontrak API dan workflow fitur existing.
- Android WebView shell diperbaiki untuk kompatibilitas API 26/27.
- Workflow GitHub Actions APK diperbaiki dan nama artifact dinaikkan ke v0.4.0.
- Mockup acuan tersedia di `docs/mockup-apple-reference.png`.

## Pengujian yang sudah dijalankan
- `tests/ui_contract_test.py`: PASS
- `tests/rt_isolation_test.py`: PASS
- `tests/smoke_test.py`: PASS
- Python compile: PASS
- JavaScript syntax checks: PASS
- Android XML structural checks: PASS
- Asset/link structural checks: PASS

## Batas validasi
Lingkungan build ini tidak memiliki Android SDK/Gradle dan tidak dapat mengunduh dependency dari internet, sehingga `lintDebug assembleDebug` tidak dapat dijalankan lokal. Error lint yang diberikan sebelumnya sudah diperbaiki dengan resource `values-v27` dan guard API level di `MainActivity.java`. Workflow GitHub Actions tetap menjadi validasi build APK final.

## Deployment
Backup `data/`, `cms-data/`, `.env`, dan konfigurasi produksi sebelum update.

```bash
docker compose up -d --build
```

Website publik: port 8080  
Portal internal: port 8188  
CMS: `/admin.html`

## CMS
Gunakan password produksi yang kuat pada environment CMS. Aktifkan secure cookie ketika sudah memakai HTTPS.
