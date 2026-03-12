#!/bin/bash
# LINE OA: อ่านแล้วแต่ยังไม่ตอบของวันนี้ — รันครั้งเดียว (สำหรับ cron ทุกวัน 17:35)
# ส่งผลไป Cliq: ตั้ง CLIQ_WEBHOOK_URL ใน .env (ใช้ Channel Webhook URL จาก Cliq)

export PATH="/opt/homebrew/bin:${PATH}"

WORKSPACE="${HOME}/.openclaw/workspace/LineWebScraping"
cd "$WORKSPACE" || { echo "ไม่เจอโฟลเดอร์: $WORKSPACE"; exit 1; }

# โหลด .env (ต้องอยู่หลัง cd เพื่อใช้ path ที่ถูก)
if [ -f .env ]; then
  _tmpenv=$(mktemp); sed 's/\r$//' .env > "$_tmpenv"; set -a; . "$_tmpenv"; set +a; rm -f "$_tmpenv"
fi

# 1. เช็คพอร์ต LINE ถ้าไม่เปิดก็รัน Chrome แล้วรอ 5 วินาที
LINE_PORT="${LINE_OA_CHROME_DEBUG_PORT:-${CHROME_DEBUG_PORT:-9222}}"
LINE_PORT="${LINE_PORT%%,*}"
nc -z localhost "${LINE_PORT}" > /dev/null 2>&1 || { /bin/bash start_chrome_for_script.sh & sleep 5; }

# 2. รัน Python: อ่านแล้วแต่ยังไม่ตอบของวันนี้ (รันครั้งเดียว) + ส่งผลไป Cliq ถ้ามี CLIQ_WEBHOOK_URL ใน .env
/opt/homebrew/bin/python3 line_oa_read_not_replied_once.py \
  --url "${LINE_OA_URL:-https://chat.line.biz/Ua891055e09d7e52c08c29828d0f662f7}" \
  --connect-chrome "${LINE_OA_CHROME_DEBUG_PORT:-${CHROME_DEBUG_PORT:-9222}}" \
  --cliq
