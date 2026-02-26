#!/bin/bash
# LINE OA: อ่านแล้วแต่ยังไม่ตอบของวันนี้ — รันครั้งเดียว (สำหรับ cron ทุกวัน 17:35)

WORKSPACE="${HOME}/.openclaw/workspace/LineWebScraping"
cd "$WORKSPACE" || { echo "ไม่เจอโฟลเดอร์: $WORKSPACE"; exit 1; }

# 1. เช็คพอร์ต 9222 ถ้าไม่เปิดก็รัน Chrome แล้วรอ 5 วินาที
nc -z localhost 9222 > /dev/null 2>&1 || { /bin/bash start_chrome_for_script.sh & sleep 5; }

# 2. รัน Python: อ่านแล้วแต่ยังไม่ตอบของวันนี้ (รันครั้งเดียว ส่งผลไป openclaw ตาม .env)
/opt/homebrew/bin/python3 line_oa_read_not_replied_once.py --url "${LINE_OA_URL:-https://chat.line.biz/Ua891055e09d7e52c08c29828d0f662f7}" --connect-chrome 9222 --send-openclaw-target "${LINE_OA_OPENCLAW_TARGET:-webchat}"
