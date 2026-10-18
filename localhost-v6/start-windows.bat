@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>&1
if errorlevel 1 (
 echo [RW10+] Node.js versi 22 atau lebih baru belum terinstall.
 echo Install dari https://nodejs.org lalu jalankan kembali file ini.
 pause
 exit /b 1
)
echo ====================================================
echo  RW10+ v6.0 - CONTROL CENTER ^& RUANG WARGA
echo ====================================================
echo  Browser : http://127.0.0.1:8097
 echo  Login   : http://127.0.0.1:8097/#/admin
 echo  Saat pertama kali, lihat data\AKUN-ADMIN-PERTAMA.txt
 echo  Tutup jendela ini untuk menghentikan server.
echo ====================================================
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8097'"
node server.js
if errorlevel 1 (
 echo.
 echo Server gagal berjalan. Periksa port 8097 atau versi Node.js.
 pause
)
