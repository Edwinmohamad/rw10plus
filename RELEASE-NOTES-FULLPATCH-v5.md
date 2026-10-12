# RW10+ Pabuaran — Full Patch v5 (12 Oktober 2026)

## Paket
Full project RW10+ terdiri dari website publik (8080), aplikasi internal (8188), konfigurasi Docker, dan test existing. Basis dari RW10+ foto/INKAMNET v2 (termasuk pembatasan RT) + website visual v4. Bukan hanya folder website.

## Yang termasuk
- Website publik modern dengan foto lokal, logo INKAMNET transparan dan kredit pengembang.
- Halaman RT01–RT04 termasuk RT04 GG H Kape.
- Animasi scroll/counter (angka hanya saat data tersedia), navbar mobile, gaya font konsisten.
- Backend internal lama dan pembatasan cakupan RT01–RT04, diuji lewat test yang disediakan.
- Aplikasi internal SOS, pengaduan, surat, iuran, Guest Pass, patroli dan fitur sebelumnya.

## Batasan penting
- CCTV di aplikasi internal masih simulasi. Tidak ada konfigurasi CCTV pelanggan PPPoE, go2rtc, RTSP atau ONVIF otomatis di paket ini.
- Tidak mengintegrasikan GenieACS.
- Belum ada CRUD penduduk/KK, CMS dinamis, import-export penduduk, atau integrasi WiFi Pelajar/MikroTik ke website RW10+. Modul tersebut tidak diklaim selesai.
- Foto generatif merupakan ilustrasi; data statistik/organisasi RT belum tersedia secara resmi.
- URL aplikasi internal pada `website/config.js` saat ini memakai `http://192.168.100.50:8188`: wajib ubah ke domain HTTPS yang bisa dijangkau apabila website dibuka dari internet.
- Kredensial dan PIN akun demo harus diganti sebelum produksi. Periksa HTTPS, RBAC dan kebijakan data pribadi.

## Instalasi aman
1. Backup source lama, Docker compose, konfigurasi lingkungan, dan **folder `data/`**; jangan tertimpa database aktif.
2. Extract paket ke direktori baru untuk staging. Tinjau diff terhadap instalasi existing, termasuk customisasi di `server.py`.
3. Salin konfigurasi produksi yang telah dicek; jangan gunakan akun demo di lingkungan publik.
4. Pastikan `website/config.js` disetel benar.
5. Dari root project: `docker compose up -d --build`.
6. Uji `/` di port 8080; `rt.html?rt=04`, login dan akses internal di port 8188; uji izin lintas RT sebelum deployment final.
7. Jika gagal, rollback ke backup kode dan data sesuai rencana.

## QA berhasil di lingkungan build
- `python3 -m py_compile server.py`
- `python3 tests/ui_contract_test.py`: PASS
- `python3 tests/rt_isolation_test.py`: PASS
- `python3 tests/smoke_test.py`: PASS
- `node --check` pada website/app.js, motion.js, rt.js: PASS
- Referensi aset dan anchor lokal index.html/rt.html: tidak ada file hilang.

Belum diuji dalam browser visual lintas perangkat, deployment aktual, atau MikroTik/CCTV fisik. Hasil tes ini bukan jaminan bebas bug keamanan.
