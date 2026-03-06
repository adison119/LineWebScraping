#!/bin/bash
# Start Chrome with remote debugging for LINE OA and Facebook Inbox (Mac/Linux).
# รันครั้งเดียว: อ่าน LINE_OA_PORTS / LINE_OA_CHROME_DEBUG_PORT และ FB_CHROME_DEBUG_PORT จาก .env แล้วเปิด Chrome ตามรายการพอร์ต
# Usage: ./start_chrome_for_script.sh
#        หรือส่งตัวเลข slot: ./start_chrome_for_script.sh 2 (เปิดแค่ slot ที่ 2)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# โหลด .env (พอร์ตและ profile สำหรับ LINE และ Facebook)
FB_CHROME_DEBUG_PROFILE=""
if [[ -f .env ]]; then
  set -a
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line//$'\r'/}"
    if [[ "$line" =~ ^[[:space:]]*LINE_OA_PORTS=(.*) ]]; then
      LINE_OA_PORTS="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ ^[[:space:]]*LINE_OA_CHROME_DEBUG_PORT=(.*) ]]; then
      LINE_OA_CHROME_DEBUG_PORT="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ ^[[:space:]]*FB_CHROME_DEBUG_PORT=(.*) ]]; then
      FB_CHROME_DEBUG_PORT="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ ^[[:space:]]*FB_CHROME_DEBUG_PROFILE=(.*) ]]; then
      FB_CHROME_DEBUG_PROFILE="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ ^[[:space:]]*CHROME_DEBUG_PORT=(.*) ]]; then
      CHROME_DEBUG_PORT="${BASH_REMATCH[1]}"
    fi
  done < .env
  set +a
fi

LINE_PORTS="${LINE_OA_PORTS:-${LINE_OA_CHROME_DEBUG_PORT:-${CHROME_DEBUG_PORT:-9222}}}"
LINE_PORTS="${LINE_PORTS// /}"
[[ -z "$LINE_PORTS" ]] && LINE_PORTS="9222"
FB_PORTS="${FB_CHROME_DEBUG_PORT:-}"
FB_PORTS="${FB_PORTS// /}"
# Facebook ใช้ profile หมายเลขเท่าไร (ค่าเริ่มต้น 3 = chrome_debug_profile_3)
FB_PROFILE_NUM="${FB_CHROME_DEBUG_PROFILE:-3}"
FB_PROFILE_NUM="${FB_PROFILE_NUM// /}"

# ถ้ารันด้วย argument ตัวเลข = เปิดแค่ slot นั้น (โหมดเดิม)
if [[ -n "$1" && "$1" =~ ^[0-9]+$ ]]; then
  SLOT="$1"
  PORT=$((9221 + SLOT))
  LINE_PORTS="$PORT"
  FB_PORTS=""
fi

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

OPENED=0

# --- เปิด Chrome สำหรับ LINE (profile ตาม slot: 9222=profile, 9223=profile_2 ฯลฯ) ---
IFS=',' read -ra LINE_ARRAY <<< "$LINE_PORTS"
for PORT in "${LINE_ARRAY[@]}"; do
  PORT="${PORT// /}"
  [[ -z "$PORT" ]] && continue
  SLOT=$((PORT - 9221))
  [[ $SLOT -lt 1 ]] && SLOT=1
  if [[ $SLOT -eq 1 ]]; then
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
  echo "Chrome started [LINE]: port $PORT, profile $DEBUG_PROFILE_NAME"
  OPENED=$((OPENED + 1))
  sleep 1
done

# --- เปิด Chrome สำหรับ Facebook (profile ร่วม = แค่พอร์ตแรก; ใช้ profile ตาม FB_CHROME_DEBUG_PROFILE เช่น 3) ---
if [[ -n "$FB_PORTS" ]]; then
  IFS=',' read -ra FB_ARRAY <<< "$FB_PORTS"
  PORT="${FB_ARRAY[0]// /}"
  if [[ -n "$PORT" ]]; then
    if [[ "$FB_PROFILE_NUM" == "1" ]]; then
      DEBUG_PROFILE_NAME="chrome_debug_profile"
    else
      DEBUG_PROFILE_NAME="chrome_debug_profile_${FB_PROFILE_NUM}"
    fi
    DEBUG_PROFILE="${SCRIPT_DIR}/${DEBUG_PROFILE_NAME}"
    if command -v lsof >/dev/null 2>&1; then
      if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "[Warning] Port $PORT is already in use (profile: $DEBUG_PROFILE_NAME). Skip."
      else
        mkdir -p "$DEBUG_PROFILE"
        "$CHROME" --remote-debugging-port="$PORT" --user-data-dir="$DEBUG_PROFILE" &
        echo "Chrome started [FB]: port $PORT, profile $DEBUG_PROFILE_NAME"
        OPENED=$((OPENED + 1))
        sleep 1
      fi
    else
      mkdir -p "$DEBUG_PROFILE"
      "$CHROME" --remote-debugging-port="$PORT" --user-data-dir="$DEBUG_PROFILE" &
      echo "Chrome started [FB]: port $PORT, profile $DEBUG_PROFILE_NAME"
      OPENED=$((OPENED + 1))
      sleep 1
    fi
  fi
fi

if [[ $OPENED -eq 0 ]]; then
  echo "No Chrome started (all ports may be in use)."
  exit 1
fi

echo ""
echo "Started $OPENED Chrome profile(s)."
echo "  - ล็อกอิน LINE OA ในหน้าต่างที่ตรงกับพอร์ต LINE (จาก LINE_OA_CHROME_DEBUG_PORT)"
echo "  - ล็อกอิน Facebook Inbox ในหน้าต่างที่ตรงกับพอร์ต FB (จาก FB_CHROME_DEBUG_PORT)"
echo "Then run: python line_oa_unread_messages.py หรือ python facebook_unread_messages.py"
