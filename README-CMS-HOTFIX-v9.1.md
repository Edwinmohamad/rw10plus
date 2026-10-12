# RW10+ CMS Hotfix v9.1

## Masalah yang diperbaiki
GitHub Actions sebelumnya gagal pada `docker compose config --quiet` karena `CMS_ADMIN_PASSWORD` diwajibkan oleh Compose walaupun `.env` belum dibuat.

## Perubahan
- `CMS_ADMIN_PASSWORD` sekarang memiliki default staging: `RW10Admin2026!`.
- `CMS_COOKIE_SECURE` default tetap `false` untuk HTTP/LAN.
- Perubahan pada folder `cms/**` sekarang memicu workflow deploy CT102.
- `.env.example` dan `CMS-LOGIN.txt` ditambahkan.

## Login CMS sementara
- URL: `http://IP-SERVER:8080/admin.html`
- Username: tidak digunakan pada CMS v8/v9
- Password: `RW10Admin2026!`

## Production
Setelah semuanya stabil, buat `.env` di root repository:

```env
CMS_ADMIN_PASSWORD=PASSWORD_BARU_YANG_KUAT
CMS_COOKIE_SECURE=true
```

Gunakan `CMS_COOKIE_SECURE=true` hanya setelah portal menggunakan HTTPS.

## Validasi yang dilakukan
- YAML parse: PASS
- Compose interpolation static check: PASS
- CMS server Python compile: PASS
- CMS login dengan default staging: PASS
- CMS session check: PASS

Docker tidak tersedia pada environment pembuatan patch, sehingga `docker compose config` aktual belum dijalankan di sini. Namun ekspresi Compose yang menyebabkan kegagalan sudah dihapus.
