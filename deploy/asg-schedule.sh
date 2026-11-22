#!/bin/bash
# Tugas 15 no.2 - Penjadwalan Auto Scaling Group (AWS CLI).
# Pakai: bash deploy/asg-schedule.sh <nama-asg> <waktu-UTC>   contoh: bash deploy/asg-schedule.sh lablend-asg 2026-12-01T03:00:00Z
ASG="${1:?Pakai: bash asg-schedule.sh <nama-asg> <waktu-UTC ISO>}"; WHEN="${2:?waktu UTC ISO, mis. 2026-12-01T03:00:00Z}"
# Sebelum jadwal: desired 1, min 1, max 2
aws autoscaling update-auto-scaling-group --auto-scaling-group-name "$ASG" --min-size 1 --max-size 2 --desired-capacity 1
# Saat jadwal tiba: desired 3, min 1, max 4
aws autoscaling put-scheduled-update-group-action --auto-scaling-group-name "$ASG" \
  --scheduled-action-name lablend-naik --start-time "$WHEN" --min-size 1 --max-size 4 --desired-capacity 3
aws autoscaling describe-scheduled-actions --auto-scaling-group-name "$ASG"
