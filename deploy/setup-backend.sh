#!/bin/bash
# Tugas 14 no.4 - backend LabLend di EC2 Ubuntu (Gunicorn + systemd).
# Pakai: bash deploy/setup-backend.sh https://github.com/USER/lablend.git
set -e
REPO="${1:?Pakai: bash setup-backend.sh <url-repo-github>}"
sudo apt update -y && sudo apt install -y python3-venv python3-pip git
cd ~ && rm -rf lablend && git clone "$REPO" lablend && cd lablend
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 24)/;s/^FLASK_DEBUG=.*/FLASK_DEBUG=0/" .env
sed "s|__USER__|$USER|g;s|__DIR__|$HOME/lablend|g" deploy/lablend-backend.service | sudo tee /etc/systemd/system/lablend-backend.service >/dev/null
sudo systemctl daemon-reload && sudo systemctl enable --now lablend-backend
systemctl status lablend-backend --no-pager
echo "Tes: curl http://localhost:5000/api/health  (buka port 5000 pada Security Group)"
