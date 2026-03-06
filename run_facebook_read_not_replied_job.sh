#!/bin/bash
# รัน Facebook Inbox: ตรวจหาข้อความที่อ่านแล้วแต่ยังไม่ตอบ (read-not-replied)
# ใช้ FB_INBOX_URL และ FB_CHROME_DEBUG_PORT จาก .env ถ้ามี

cd "$(dirname "$0")" || exit 1
if [ -f .env ]; then set -a; . ./.env; set +a; fi

python3 facebook_read_not_replied.py "$@"
