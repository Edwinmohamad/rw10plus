# Kontrak Webhook RW10+ → n8n

Semua request produksi wajib memakai HTTPS, `X-RW10-Signature: sha256=<HMAC_BODY>`, timestamp, idempotency key, dan retry eksponensial. Jangan kirim PIN, token login, atau URL CCTV.

## Pengingat tagihan

`POST /webhook/rw10/billing-reminder`

```json
{
  "event": "dues.reminder.requested",
  "event_id": "uuid",
  "occurred_at": "2026-09-16T07:00:00+07:00",
  "resident": {"name": "Ahmad", "phone": "62812xxxx", "rt": 1},
  "invoice": {"id": "uuid", "period": "2026-09", "amount_due": 150000, "due_date": "2026-09-30"}
}
```

Flow: Webhook → verifikasi HMAC/timestamp → cek idempotency → format pesan → WA Gateway → simpan delivery status. Maksimal tiga retry; kegagalan masuk dead-letter queue untuk admin.

## Kwitansi terverifikasi

`POST /webhook/rw10/receipt-issued`

```json
{
  "event": "dues.receipt.issued",
  "event_id": "uuid",
  "resident": {"name": "Ahmad", "phone": "62812xxxx"},
  "receipt": {"number": "KW-RW10-202609-0001", "amount": 150000, "paid_at": "2026-09-16T10:15:00+07:00", "pdf_url": "https://signed.example/short-lived-url"}
}
```

## Emergency dispatch

Payload hanya menuju adapter FCM/WA petugas, bukan grup publik. Silent SOS tidak boleh memicu audio di perangkat pelapor.

```json
{
  "event": "emergency.activated",
  "event_id": "uuid",
  "mode": "silent",
  "category": "keamanan",
  "reporter": {"name": "Ahmad", "house": "Rumah 12", "rt": 1},
  "location": {"lat": -6.0, "lng": 106.0},
  "cancel_deadline": "2026-09-16T10:15:10+07:00"
}
```

> n8n tidak boleh menjadi sumber kebenaran status SOS. Database aplikasi tetap authoritative; workflow hanya mengirim side effect setelah cancel window berakhir.
