# Pembaruan instalasi web/app pada port 8080

Instalasi yang diperiksa memakai `rw10plus-web-1` (Nginx) dan `rw10plus-app-1`
(Uvicorn). Nginx membaca `frontend/` dan `nginx/default.conf`; database serta
unggahan berada pada named volume Docker. Compose baru di root memakai nama
service berbeda, sehingga menjalankan `compose up` langsung membuat website
kedua yang berebut port 8080.

`install.sh` sekarang mendeteksi container tersebut dan menjalankan
`scripts/deploy_existing_frontend.py` sebelum langkah build, database, atau
Compose. Pembaruan ini:

- Memastikan kedua container berjalan dan bind mount sesuai instalasi yang diperiksa.
- Membuat backup frontend dan konfigurasi di `/var/backups/rw10-ui-*`.
- Menyiapkan bundle publik di `frontend/_rw10_ui/<release>/`.
- Mengubah hanya route Nginx **exact `/`** menuju homepage baru.
- Mempertahankan route `/api/`, `/assets/`, `/login` dan backend `app:8000`.
- Menyesuaikan aset agar tidak bertabrakan dengan aset aplikasi lama dan memenuhi CSP tanpa inline script/handler.
- Memvalidasi Nginx, melakukan reload, lalu mengecek homepage, aset baru, login,
  dan status route/aset aplikasi yang diukur sebelum perubahan.
- Mengembalikan konfigurasi awal jika validasi/reload/HTTP check gagal.

Tidak ada container yang dihentikan/dihapus, port baru yang diterbitkan,
atau volume database/uploads yang dimigrasikan. Jangan memakai
`docker compose up --remove-orphans` pada checkout ini untuk instalasi lama.

GitHub Actions yang sudah ada memanggil `install.sh`; merge perbaikan ini
memicu jalur deployment di atas. Untuk menjalankan manual setelah checkout
diperbarui dan tidak ada job deployment lain yang berjalan:

```bash
cd /home/actions/actions-runner/_work/rw10plus/rw10plus
sudo bash install.sh
```

Website: `http://192.168.100.50:8080/`. Ruang Warga tetap `/login`.

Rollback manual: salin isi `default.conf` dari folder backup yang dicetak
installer ke file `nginx/default.conf` **tanpa mengganti inode** (gunakan `cat
backup/default.conf > nginx/default.conf`), jalankan `docker exec
rw10plus-web-1 nginx -t`, lalu `docker exec rw10plus-web-1 nginx -s reload`.

## Batasan dan validasi

Ini pembaruan homepage publik pada backend Uvicorn yang sudah berjalan.
Control Center Node.js v6 dan CMS Python standalone belum dimigrasikan ke
backend tersebut. Bundle mempertahankan endpoint konten publik yang sudah
ada; jika endpoint itu tidak tersedia, konten contoh tetap berlabel dan
installer menampilkan catatan. Perubahan ini tidak mengklaim integrasi data
CMS baru atau kesetaraan seluruh fitur v6.

Regresi lokal: enam tes untuk penjagaan konfigurasi, routing API/aset,
penamaan aset, kompatibilitas CSP, dan rollback. Sepuluh file JS hasil
penyiapan bundle lolos `node --check`, referensi aset HTML tersedia, dan
`sh -n install.sh` lolos. Uji Nginx/container/browser nyata belum dijalankan
di lingkungan pengembangan; installer wajib menjalankan validasi pada host.
