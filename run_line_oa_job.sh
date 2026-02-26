#!/bin/bash
# รายงานข้อความที่ยังไม่อ่าน (summary-once) — รันครั้งเดียวต่อครั้ง
# ใช้กับ cron: ทุก 1 ชม. 8:30–17:30 (30 8-17 * * *)
# ถ้ารันจาก cron แล้ว OpenClaw ไม่ส่งไป LINE: ดู CRON_OPENCLAW.md (ตั้ง HOME/PATH ใน crontab + ให้ Gateway รันอยู่)

export PATH="/opt/homebrew/bin:${PATH}"

WORKSPACE="${HOME}/.openclaw/workspace/LineWebScraping"
cd "$WORKSPACE" || { echo "ไม่เจอโฟลเดอร์: $WORKSPACE"; exit 1; }

# โหลด .env (ต้องอยู่หลัง cd เพื่อใช้ path ที่ถูก)
if [ -f .env ]; then set -a; . ./.env; set +a; fi

# 1. เช็คพอร์ต 9222 ถ้าไม่เปิดก็รัน Chrome แล้วรอ 5 วินาที
nc -z localhost 9222 > /dev/null 2>&1 || { /bin/bash start_chrome_for_script.sh & sleep 5; }

# 2. รัน Python: รายงานข้อความที่ยังไม่อ่าน (รันครั้งเดียว) + ส่งผลไป openclaw ถ้ามี LINE_OA_OPENCLAW_TARGET
/opt/homebrew/bin/python3 line_oa_unread_messages.py \
  --url "${LINE_OA_URL:-https://chat.line.biz/Ua891055e09d7e52c08c29828d0f662f7}" \
  --connect-chrome 9222 \
  --report-format summary-once \
  --send-openclaw-target "${LINE_OA_OPENCLAW_TARGET:-}"
