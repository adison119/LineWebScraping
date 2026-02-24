#!/bin/bash
# Start Chrome with remote debugging for LINE OA script (Mac/Linux).
# Usage: ./start_chrome_for_script.sh

PORT=9222
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEBUG_PROFILE="${SCRIPT_DIR}/chrome_debug_profile"

# Check if port is already in use
if command -v lsof >/dev/null 2>&1; then
  if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "[Warning] Port $PORT is already in use."
    echo "  - If you already started Chrome for the script, do not run this again."
    echo "  - To start a new Chrome, quit the one using this port first, or change PORT in this script."
    exit 1
  fi
fi

echo "Starting Chrome for LINE OA script..."
echo "Log in to LINE OA in this Chrome, then run: python line_oa_unread_messages.py"
echo ""

# Find Chrome (Mac typical path; Linux may use google-chrome or chromium)
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

mkdir -p "$DEBUG_PROFILE"
"$CHROME" --remote-debugging-port="$PORT" --user-data-dir="$DEBUG_PROFILE" &
echo "Chrome started on port $PORT (profile: chrome_debug_profile) - must match CHROME_DEBUG_PORT in .env"
echo "Log in to LINE OA, then run the Python script."
