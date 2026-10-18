@echo off
setlocal
cd /d "%~dp0"
echo Pastikan server RW10+ sedang dihentikan agar database tersalin konsisten.
echo.
set /p CONFIRM="Server sudah berhenti? Ketik YA lalu Enter: "
if /I not "%CONFIRM%"=="YA" exit /b 1
if not exist data\rw10plus.sqlite (
 echo Database belum tersedia. Jalankan server minimal satu kali.
 pause
 exit /b 1
)
if not exist backups mkdir backups
powershell -NoProfile -Command "$d=Get-Date -Format 'yyyyMMdd-HHmmss'; Compress-Archive -Path 'data' -DestinationPath ('backups\\RW10plus-BACKUP-'+$d+'.zip') -CompressionLevel Optimal; Write-Host 'Backup tersimpan di folder backups'"
pause
