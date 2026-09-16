# Matriks Implementasi RW10+ v0.3.0

| Modul PRD | Status v0.3 | Catatan |
|---|---|---|
| Empat role + RBAC | Aktif | Scope warga, RT, RW, Satpam diuji otomatis |
| SOS hold 3 detik | Aktif | Haptic bila perangkat mendukung |
| Cancel window 10 detik | Aktif | Deadline divalidasi server |
| Public / Silent SOS | Aktif lokal | Distribusi via polling; FCM belum tersambung |
| Respons petugas | Aktif | Acknowledge, menuju, resolve, audit log |
| TOA fisik | Simulasi | Interlock dan perangkat lapangan belum tersedia |
| Snap & Fix | Aktif dasar | Form, scope, state machine; object storage foto belum terhubung |
| Iuran / Kas | Aktif dasar | Tagihan, ring visual, referensi bukti bayar |
| Surat RT → RW | Aktif | Nomor dan token verifikasi; PDF/TTE tahap integrasi |
| Guest Pass | Aktif dengan token | Generator/validasi satu kali; kamera QR tahap integrasi |
| Patroli digital | Aktif | Checkpoint tervalidasi; geofence/NFC tahap integrasi |
| CCTV | Simulasi | Tidak menyimpan credential RTSP di client |
| Pasar Warga | Aktif | Katalog dan direct WhatsApp |
| E-voting | Aktif pilot | Constraint satu rumah satu suara |
| Mode Lansia | Aktif | Touch target ≥64px dan beranda disederhanakan |
| Light / Dark OLED | Aktif | Preferensi disimpan per akun |
| Supabase/Postgres | Blueprint siap | DDL + RLS di folder infrastructure |
| n8n / WA / FCM | Adapter siap | Membutuhkan URL dan credential milik RW10 |

> Status “aktif” berarti berjalan pada server lokal pilot. Bukan klaim siap digunakan untuk keadaan darurat nyata sebelum uji lapangan dan integrasi perangkat selesai.
