#!/bin/bash
# Tugas 11 no.3 - skrip bash sederhana di Linux (EC2): menampilkan info server.
echo "Host     : $(hostname -f)"
echo "Waktu    : $(date)"
echo "OS       : $(lsb_release -ds 2>/dev/null || uname -sr)"
echo "CPU      : $(nproc) vCPU"
echo "RAM      : $(free -h | awk '/Mem:/ {print $2}')"
echo "Disk     : $(df -h / | awk 'NR==2 {print $3 " terpakai dari " $2}')"
echo "IP privat: $(hostname -I | awk '{print $1}')"
