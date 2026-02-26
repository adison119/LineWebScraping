#!/bin/bash
WORKSPACE="${HOME}/.openclaw/workspace/Line_Unread"
cd "$WORKSPACE" || { echo "ไม่เจอโฟลเดอร์: $WORKSPACE"; exit 1; }

# 1. เช็คพอร์ต 9222 ถ้าไม่เปิดก็รัน Chrome แล้วรอ 5 วินาที
nc -z localhost 9222 > /dev/null 2>&1 || { /bin/bash start_chrome_for_script.sh & sleep 5; }

# 2. รัน Python (ดึงข้อมูล + ส่งผลไป openclaw เอง ไม่ต้องเรียก openclaw ใน shell)
/opt/homebrew/bin/python3 line_oa_unread_messages.py --url "https://chat.line.biz/Ua891055e09d7e52c08c29828d0f662f7" --connect-chrome 9222 --report-format summary-once --send-openclaw-target webchat
