#!/bin/bash
# Tugas 15 no.1 - User data untuk Launch Template / EC2 di belakang Application Load Balancer.
apt update -y
apt install -y apache2
systemctl start apache2
systemctl enable apache2
echo "<h1> Hello WORLD from $(hostname -f) </h1>" > /var/www/html/index.html
