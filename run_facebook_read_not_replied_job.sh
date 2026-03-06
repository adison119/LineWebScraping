#!/bin/bash
# รัน Facebook Inbox: ตรวจหาข้อความที่อ่านแล้วแต่ยังไม่ตอบ (read-not-replied)
# ใช้ FB_INBOX_URL และ FB_CHROME_DEBUG_PORT จาก .env ถ้ามี

cd "$(dirname "$0")" || exit 1
if [ -f .env ]; then
  _tmpenv=$(mktemp); sed 's/\r$//' .env > "$_tmpenv"; set -a; . "$_tmpenv"; set +a; rm -f "$_tmpenv"
fi

python3 facebook_read_not_replied.py "$@"
