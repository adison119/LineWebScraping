#!/bin/bash
# Start Chrome with remote debugging for LINE OA script (Mac/Linux).
# รันครั้งเดียว: อ่าน LINE_OA_PORTS หรือ CHROME_DEBUG_PORT จาก .env แล้วเปิด Chrome ตามจำนวน port
# ถ้าไม่พบ .env หรือไม่กำหนด port = เปิดแค่ port 9222 (โปรไฟล์เดียว)
# Usage: ./start_chrome_for_script.sh
#        หรือส่งตัวเลข slot อย่างเดียว: ./start_chrome_for_script.sh 2 (เปิดแค่บัญชีที่ 2)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# โหลด .env
if [[ -f .env ]]; then
  set -a
  # กันไม่ให้ # ในค่าตัวแปรถูกมองเป็น comment
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[[:space:]]*LINE_OA_PORTS=(.*) ]]; then
      LINE_OA_PORTS="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ ^[[:space:]]*CHROME_DEBUG_PORT=(.*) ]]; then
      CHROME_DEBUG_PORT="${BASH_REMATCH[1]}"
    fi
  done < .env
  set +a
fi

# รายการ port: ใช้ LINE_OA_PORTS ถ้ามี ไม่ก็ CHROME_DEBUG_PORT (รองรับค่าเดียวหรือหลายค่าคั่น comma)
PORTS_RAW="${LINE_OA_PORTS:-${CHROME_DEBUG_PORT:-9222}}"
PORTS_RAW="${PORTS_RAW// /}"  # ลบช่องว่าง
if [[ -z "$PORTS_RAW" ]]; then
  PORTS_RAW="9222"
fi

# ถ้ารันด้วย argument ตัวเลข = เปิดแค่ slot นั้น (โหมดเดิม)
if [[ -n "$1" && "$1" =~ ^[0-9]+$ ]]; then
  SLOT="$1"
  PORT=$((9221 + SLOT))
  PORTS_RAW="$PORT"
fi

# แปลงเป็น array (คั่น comma)
IFS=',' read -ra PORTS_ARRAY <<< "$PORTS_RAW"
OPENED=0

# หา Chrome
CHROME=""
if [[ "$OSTYPE" == darwin* ]]; then
  if [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  fi
else
  for c in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then
      CHROME="$(command -v "$c")"
      break
    fi
  done
fi

if [[ -z "$CHROME" ]]; then
  echo "Chrome not found. Install Chrome or set CHROME path in this script."
  exit 1
fi

for PORT in "${PORTS_ARRAY[@]}"; do
  PORT="${PORT// /}"
  [[ -z "$PORT" ]] && continue
  SLOT=$((PORT - 9221))
  if [[ "$SLOT" -lt 1 ]]; then
    SLOT=1
  fi
  if [[ "$SLOT" -eq 1 ]]; then
    DEBUG_PROFILE_NAME="chrome_debug_profile"
  else
    DEBUG_PROFILE_NAME="chrome_debug_profile_${SLOT}"
  fi
  DEBUG_PROFILE="${SCRIPT_DIR}/${DEBUG_PROFILE_NAME}"

  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "[Warning] Port $PORT is already in use (profile: $DEBUG_PROFILE_NAME). Skip."
      continue
    fi
  fi

  mkdir -p "$DEBUG_PROFILE"
  "$CHROME" --remote-debugging-port="$PORT" --user-data-dir="$DEBUG_PROFILE" &
  echo "Chrome started: port $PORT, profile $DEBUG_PROFILE_NAME"
  OPENED=$((OPENED + 1))
  sleep 1
done

if [[ $OPENED -eq 0 ]]; then
  echo "No Chrome started (all ports may be in use)."
  exit 1
fi

echo ""
echo "Started $OPENED Chrome profile(s). Log in to LINE OA in each window."
echo "Then run: python line_oa_unread_messages.py --report-format summary-once"
echo "(ใช้ LINE_OA_URL และ LINE_OA_PORTS ใน .env ให้สอดคล้องกัน)"
