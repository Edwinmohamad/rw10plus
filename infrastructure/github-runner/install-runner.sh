#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Edwinmohamad/rw10plus"
RUNNER_VERSION="${RUNNER_VERSION:-2.336.0}"
RUNNER_NAME="${RUNNER_NAME:-rw10plus-ct102}"
RUNNER_LABELS="${RUNNER_LABELS:-rw10plus-deploy,ct102,proxmox}"
RUNNER_DIR="${RUNNER_DIR:-/opt/actions-runner-rw10plus}"
RUNNER_USER="${RUNNER_USER:-actions}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: jalankan sebagai root."
  exit 1
fi

if [ -z "${RUNNER_TOKEN:-}" ]; then
  echo "Masukkan token self-hosted runner dari GitHub:"
  echo "Repo -> Settings -> Actions -> Runners -> New self-hosted runner -> Linux x64"
  read -r -p "RUNNER_TOKEN: " RUNNER_TOKEN
fi

if [ -z "${RUNNER_TOKEN:-}" ]; then
  echo "ERROR: RUNNER_TOKEN kosong."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git jq tar gzip sudo python3 docker.io docker-compose-plugin

systemctl enable --now docker

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$RUNNER_USER"
fi
usermod -aG docker "$RUNNER_USER"

mkdir -p "$RUNNER_DIR"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

if [ ! -f "$RUNNER_DIR/config.sh" ]; then
  sudo -u "$RUNNER_USER" bash -lc "
    cd '$RUNNER_DIR'
    curl -fL -o actions-runner-linux-x64.tar.gz \
      'https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz'
    tar xzf actions-runner-linux-x64.tar.gz
  "
fi

if [ -f "$RUNNER_DIR/.runner" ]; then
  echo "Runner sudah terdaftar. Saya hanya pastikan servicenya aktif."
else
  sudo -u "$RUNNER_USER" bash -lc "
    cd '$RUNNER_DIR'
    ./config.sh \
      --url '$REPO_URL' \
      --token '$RUNNER_TOKEN' \
      --name '$RUNNER_NAME' \
      --labels '$RUNNER_LABELS' \
      --work '_work' \
      --unattended \
      --replace
  "
fi

cd "$RUNNER_DIR"
./svc.sh install "$RUNNER_USER" || true
./svc.sh start

echo
echo "Selesai. Cek status runner:"
./svc.sh status || true
echo
echo "Buka GitHub -> Settings -> Actions -> Runners, pastikan runner '$RUNNER_NAME' status Online."
