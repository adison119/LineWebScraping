#!/bin/bash
# ปิด Chrome ที่ใช้ port 9222 (สำหรับ LINE OA)
# เรียกเมื่อไหร่ก็ได้ หรือให้ cron ตั้งเวลาเรียก เช่น 19:00
# Usage: ./close_chrome_port_9222.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 close_chrome_port_9222.py
