#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: jalankan installer sebagai root"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker belum terpasang"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose plugin belum tersedia"
  exit 1
fi

mkdir -p data data/backups
if [ ! -f data/rw10.db ]; then
  for old in rw10plus-v02 rw10plus-v01; do
    if docker inspect "$old" >/dev/null 2>&1; then
      docker cp "$old":/app/data/rw10.db data/rw10.db 2>/dev/null || true
      [ -f data/rw10.db ] && break
    fi
  done
fi
if [ -f data/rw10.db ]; then
  cp data/rw10.db "data/backups/rw10-pre-v030-$(date +%Y%m%d-%H%M%S).db"
fi
chown -R 10001:10001 data

docker compose config --quiet
docker compose build --no-cache

OLD_RUNNING=""
for old in rw10plus-v02 rw10plus-v01; do
  if [ "$(docker inspect --format='{{.State.Running}}' "$old" 2>/dev/null || true)" = "true" ]; then
    OLD_RUNNING="$old"
    docker stop "$old" >/dev/null
    break
  fi
done

if ! docker compose up -d; then
  [ -n "$OLD_RUNNING" ] && docker start "$OLD_RUNNING" >/dev/null
  echo "ERROR: gagal menjalankan versi baru; versi lama diaktifkan kembali"
  exit 1
fi

attempt=0
while [ "$attempt" -lt 30 ]; do
  if docker inspect --format='{{.State.Health.Status}}' rw10plus-v03 2>/dev/null | grep -q healthy; then
    if ! python3 tests/deployment_check.py; then
      echo "ERROR: verifikasi tampilan/aset gagal"
      docker compose logs --tail=100
      exit 1
    fi
    echo "RW10+ v0.3.0 berhasil dipasang"
    echo "Buka: http://192.168.100.50:8188"
    docker compose ps
    exit 0
fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "ERROR: aplikasi belum sehat setelah 30 detik"
docker compose ps
docker compose logs --tail=100
docker compose down
[ -n "$OLD_RUNNING" ] && docker start "$OLD_RUNNING" >/dev/null
echo "Versi lama diaktifkan kembali."
exit 1
