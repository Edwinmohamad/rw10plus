# RW10+ Website v7 — Premium Light / Dark

Source lengkap berbasis RW10+ v6 dengan isolasi RT existing.

## Perubahan v7
- Mode terang/gelap pada website publik dan halaman RT01–RT04, mengikuti sistem secara default lalu menyimpan pilihan pengguna di localStorage.
- Tombol pencarian informasi halaman publik, juga dapat dibuka lewat Ctrl+K / Cmd+K.
- Penyesuaian desain premium: warna, spasi, tipografi, card/widget, mobile, warna dark mode.
- Aset foto lokal dan logo INKAMNET tetap disertakan.
- Backend, database, dan layanan CCTV/MikroTik tidak diubah.

## Pemasangan
1. Cadangkan direktori aplikasi, .env dan terutama data/ dari server aktif.
2. Uji paket dalam staging.
3. `docker compose up -d --build`
4. Akses website publik pada port 8080 dan aplikasi internal pada port 8188.

## Cakupan & batasan
- Mode gelap baru berlaku pada **website publik** dan halaman RT, bukan seluruh UI aplikasi internal. Aplikasi internal memiliki mode tema sendiri dari source sebelumnya.
- Pencarian ini hanya menavigasi bagian yang sudah ada di halaman, bukan pencarian database.
- Data penduduk, CMS, CCTV dan integrasi WiFi Pelajar baru belum dibuat dalam rilis ini.
- Nilai dan foto ilustrasi pada mockup bukan data warga terverifikasi.
- Tidak ada klaim pixel-perfect terhadap mockup; pengujian visual desktop dan mobile perlu dilakukan di browser deployment.

## Uji
- `python3 tests/ui_contract_test.py`
- `python3 tests/rt_isolation_test.py`
- `python3 tests/smoke_test.py`
- `node --check website/premium.js`
