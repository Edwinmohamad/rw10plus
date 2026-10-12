# RW10+ Public Portal & RT Isolation — Patch October 2026

## Scope
- Website publik di `website/` didesain ulang untuk meniru arah **mockup Opsi 1 (editorial putih/navy)**.
- Hero menggunakan **foto Street View gerbang RT04 yang diberikan user** (`website/assets/gerbang-rt04-streetview.jpg`). Foto adalah tangkapan layar Street View Juli 2025, **bukan foto dokumentasi milik RW**; atribusi dicantumkan pada halaman.
- Semua aset contoh disimpan lokal di `website/assets`, tidak ada hotlink gambar.
- WiFi Gratis Pelajar memiliki informasi program dan alur manual; **belum ada backend pendaftaran maupun provisioning MikroTik**.
- Web publik adalah statis dan tidak menyediakan CMS atau konten database otomatis.
- Internal app menggunakan `server.py` dengan role existing.

## Kebijakan RT
- `warga`: data miliknya sendiri; daftar UMKM yang ditampilkan dari RT akun, kamera RT akun, SOS RT akun.
- `ketua_rt`: dapat melihat/memproses laporan, surat, dan iuran yang relevan pada RT akun saja.
- `satpam_rw`: data rutin mengikuti RT akun; respons SOS `scope=rw/petugas` diperbolehkan lintas RT **khusus keselamatan**, dan kegiatan patroli wilayah sesuai RT akun. Guest Pass RT lain ditolak.
- `pengurus_rw`: akses seluruh RT untuk koordinasi/persetujuan tingkat RW.
- Berita, struktur RW, dan voting saat ini tetap konten tingkat RW (bukan data privat RT).
- Saat ini belum ada self-registration; field RT berasal dari database pengguna dan tidak dapat diganti lewat frontend.

## Konfigurasi
- Public website: `http://SERVER:8080`
- Internal app: `http://SERVER:8188`
- **Sebelum portal dipublikasi secara internet**, edit `website/config.js` untuk memakai domain HTTPS aplikasi internal yang dapat dijangkau user. IP `192.168.100.50` hanya contoh lokal existing.
- `docker compose up -d --build` pada direktori proyek.
- Backup folder `data/` terlebih dahulu sebelum setiap deployment. Jangan upload `data/` asli ke GitHub.
- Hak akses RT ditentukan kolom `users.rt` existing; migrasi tidak menghapus data.

## Quality checks executed
- `python3 -m py_compile server.py`: pass
- `python3 tests/ui_contract_test.py`: pass
- `python3 tests/smoke_test.py`: pass (expectations adapted for RT-scoped cameras/guest scan)
- `python3 tests/rt_isolation_test.py`: pass
- Static HTML check: all 15 images present / every internal anchor resolves.
- HTTP header response served by Python local test server: not a full automated browser run.
- Playwright browser navigation blocked by environment's administrator (`ERR_BLOCKED_BY_ADMINISTRATOR`); **render fidelity, CLS and mobile interactions not fully verified**. Manual visual QA required at 360px, 390px, 768px, 1280px, 1440px.

## Pending for production
- Real verified content/photos and approved stats; more original RT photography.
- Real contacts and authorized hotline.
- WiFi student registration backend and policy/compliance review for minors.
- CMS with authenticated publishing and dynamic public data.
- Full browser test on deploy server; HTTPS domain, cookie hardening and security review.
- Real CCTV/TOA/FCM and other documented simulation integrations remain unchanged.
