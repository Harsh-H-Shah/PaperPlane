#!/bin/bash
# One-time setup for a fresh Google Cloud e2-micro VM (Ubuntu 24.04 LTS, x86).
# Safe to re-run. Usage, on the VM:
#
#   curl -fsSL https://raw.githubusercontent.com/Harsh-H-Shah/PaperPlane/main/deploy/gcp-setup.sh | bash
#
set -euo pipefail

APP_DIR="$HOME/paperplane"
REPO="https://github.com/Harsh-H-Shah/PaperPlane.git"

echo "==> 2 GB swap (the VM has 1 GB RAM; headless Chrome needs headroom)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> Docker (starts on boot)"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker

echo "==> Code"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"
mkdir -p data logs
# The container runs as a non-root user; let it write runtime data.
chmod 777 data logs

if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! Created .env from the template. Fill in GEMINI_API_KEY and ADMIN_TOKEN before starting."
fi

echo "==> Daily jobs (server time is UTC)"
CRON_BACKUP="0 7 * * * $APP_DIR/deploy/backup-db.sh >> $APP_DIR/logs/backup.log 2>&1"
CRON_SCRAPE="0 13 * * * cd $APP_DIR && docker compose -f docker-compose.prod.yml exec -T backend python main.py scrape --limit 50 >> $APP_DIR/logs/cron-scrape.log 2>&1"
( crontab -l 2>/dev/null | grep -v "$APP_DIR/deploy/backup-db.sh" | grep -v "main.py scrape"; echo "$CRON_BACKUP"; echo "$CRON_SCRAPE" ) | crontab -

cat <<EOF

Setup done. Next:
  1. Log out and back in (so your user can run docker without sudo).
  2. Copy your data into $APP_DIR/data/ (applications.db, profile.json, resume.pdf).
  3. Edit $APP_DIR/.env (GEMINI_API_KEY, ADMIN_TOKEN).
  4. cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d
EOF
