RW10+ v6.0 — KAMPUNG MODERN EDITORIAL + CONTROL CENTER
=====================================================

1) JALANKAN DI WINDOWS
   - Install Node.js 22 LTS atau yang lebih baru dari https://nodejs.org
   - Klik dua kali start-windows.bat
   - Buka http://127.0.0.1:8097
   - Login Control Center: http://127.0.0.1:8097/#/admin
   - Akun awal otomatis dibuat SATU KALI.
   - Username/password awal: buka data/AKUN-ADMIN-PERTAMA.txt
   - Ganti password dari menu "Ubah Kata Sandi" segera setelah login.
   - Hapus file kredensial awal setelah disimpan dengan aman.

2) CONTROL CENTER
   - Buka #/admin -> login admin.
   - Pilih Informasi, Agenda, Program, UMKM, atau Galeri.
   - Tambah -> unggah foto -> pilih Draf/Terbit -> Simpan.
   - Edit dan Hapus tersedia pada masing-masing entri.
   - Konten "Terbit" langsung terlihat pengunjung di website.
   - Konten "Draf" hanya terlihat di Control Center.
   - Admin dapat membuat akun Editor atau Warga di tab Akun Pengguna.
   - Editor boleh mengelola konten dan menindaklanjuti laporan; Warga tidak.

3) RUANG WARGA
   - Login lewat tombol "Ruang Warga" / #/warga.
   - Warga bisa mengirim aspirasi/pengaduan/permohonan informasi WiFi.
   - Pengurus dapat memantau dan mengubah status permohonan.
   - Belum terhubung dengan provisioning WiFi CasaOS atau CCTV asli.
   - Jangan gunakan permohonan untuk memasukkan NIK/No KK.

4) DATABASE & FOTO
   - Database: data/rw10plus.sqlite (SQLite).
   - Foto: data/uploads/ (JPG, PNG, WEBP maksimum 20 MB/file).
   - Backup: hentikan server dahulu, salin folder data/ secara utuh.
   - Seluruh data dipakai bersama semua browser yang terhubung ke server.
   - Konten versi demo/localStorage yang lama TIDAK otomatis diimpor.

5) DOCKER / CASAOS
   - Jalankan: docker compose up -d --build
   - Akses: http://IP-SERVER:8097
   - Data di Docker volume rw10_data.
   - Kredensial pertama: docker compose exec rw10plus cat /app/data/AKUN-ADMIN-PERTAMA.txt
   - Backup melalui docker volume atau salin direktori /app/data saat server berhenti.
   - JANGAN publikasi port 8097 langsung ke internet tanpa HTTPS, firewall, dan pengujian keamanan.
   - Jika di reverse proxy HTTPS: set COOKIE_SECURE=true dan jalankan kembali container.

6) BATASAN VERSI
   - Backend, login, data konten, unggah foto, CRUD, alur permohonan: aktif.
   - Validasi dan kontrol akses dasar ada, tetapi BUKAN klaim audit keamanan produksi.
   - Database warga/KK sensitif, verifikasi domisili, integrasi kamera, akses WiFi asli,
     email/WhatsApp notifikasi, dan reset kata sandi mandiri BELUM diaktifkan.
   - Data contoh yang masih ada ditandai sebagai "contoh".
   - UI tetap mengikuti referensi Kampung Modern Editorial dan memakai logo asli mitra.

Kredit wajib: Didukung oleh INKAMNET x POKJA10 / Dikembangkan oleh Edwin Mohamad.
