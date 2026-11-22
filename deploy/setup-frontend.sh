#!/bin/bash
# Tugas 14 no.3 - frontend statis LabLend di EC2 Ubuntu dengan Nginx.
# Pakai: bash deploy/setup-frontend.sh <url-repo-github> <url-backend>
#   contoh: bash deploy/setup-frontend.sh https://github.com/USER/lablend.git http://ec2-1-2-3-4.compute.amazonaws.com:5000
set -e
REPO="${1:?Pakai: bash setup-frontend.sh <url-repo-github> <url-backend>}"
API="${2:?Pakai: bash setup-frontend.sh <url-repo-github> <url-backend>}"
sudo apt update -y && sudo apt install -y nginx git
cd ~ && rm -rf lablend && git clone "$REPO" lablend
sudo mkdir -p /var/www/lablend && sudo cp -r lablend/frontend/. /var/www/lablend/
sudo sed -i "s|API_BASE: \".*\"|API_BASE: \"$API\"|" /var/www/lablend/config.js
sudo cp lablend/deploy/nginx-lablend.conf /etc/nginx/sites-available/lablend
sudo ln -sf /etc/nginx/sites-available/lablend /etc/nginx/sites-enabled/lablend
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl enable --now nginx && sudo systemctl reload nginx
systemctl status nginx --no-pager
