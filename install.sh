#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$APP_DIR"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: jalankan installer sebagai root"
  exit 1
fi

for required in compose.yaml Dockerfile server.py static tests; do
  if [ ! -e "$required" ]; then
    echo "ERROR: file/folder '$required' tidak ditemukan di $APP_DIR"
    echo "Jalankan installer dari checkout repo RW10+ yang lengkap."
    exit 1
  fi
done

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

docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" config --quiet
docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" build --no-cache

OLD_RUNNING=""
for old in rw10plus-v02 rw10plus-v01; do
  if [ "$(docker inspect --format='{{.State.Running}}' "$old" 2>/dev/null || true)" = "true" ]; then
    OLD_RUNNING="$old"
    docker stop "$old" >/dev/null
    break
  fi
done

if ! docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" up -d; then
  [ -n "$OLD_RUNNING" ] && docker start "$OLD_RUNNING" >/dev/null
  echo "ERROR: gagal menjalankan versi baru; versi lama diaktifkan kembali"
  exit 1
fi

attempt=0
while [ "$attempt" -lt 90 ]; do
  HEALTH_STATUS="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' rw10plus-v03 2>/dev/null || true)"
  if [ "$HEALTH_STATUS" = "healthy" ] || python3 - <<'PY' >/dev/null 2>&1
import json
import urllib.request
with urllib.request.urlopen("http://127.0.0.1:8188/api/health", timeout=2) as response:
    body = json.loads(response.read())
    raise SystemExit(0 if response.status == 200 and body.get("version") == "0.3.0" else 1)
PY
  then
    if ! python3 tests/deployment_check.py; then
      echo "ERROR: verifikasi tampilan/aset gagal"
      docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" logs --tail=100
      exit 1
    fi
    echo "RW10+ v0.3.0 berhasil dipasang"
    echo "Buka: http://192.168.100.50:8188"
    docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" ps
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "ERROR: aplikasi belum sehat setelah 90 detik"
docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" ps
docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" logs --tail=100
docker compose --project-directory "$APP_DIR" -f "$APP_DIR/compose.yaml" down
[ -n "$OLD_RUNNING" ] && docker start "$OLD_RUNNING" >/dev/null
echo "Versi lama diaktifkan kembali."
exit 1
