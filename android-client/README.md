# RW10+ Android Internal

Android WebView client v0.3.0 untuk server lokal `http://192.168.100.50:8188/`.

## Penting

- Seluruh SOS dan TOA masih simulasi.
- APK hanya berfungsi saat HP dapat menjangkau jaringan `192.168.100.0/24`.
- Simpan `rw10plus-release.jks` dan `keystore.properties`; file yang hilang tidak dapat dipakai untuk menandatangani pembaruan dengan identitas yang sama.
- Jangan unggah kedua file signing tersebut ke repository publik.

## Build

```bash
cd android-client
./build-apk.sh
```

Output: `output/RW10PLUS-INTERNAL-v0.3.0.apk`.
