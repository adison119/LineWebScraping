#!/bin/bash
# รัน Facebook Inbox: สรุปรายการแชท (summary-once) — ค่าเริ่มต้น
# ใช้ FB_INBOX_URL และ FB_CHROME_DEBUG_PORT จาก .env ถ้ามี

cd "$(dirname "$0")" || exit 1
if [ -f .env ]; then set -a; . ./.env; set +a; fi

python3 facebook_unread_messages.py --report-format summary-once "$@"
