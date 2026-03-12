# -*- coding: utf-8 -*-
"""
LINE OA - ตรวจข้อความที่อ่านแล้วแต่ยังไม่ตอบของวันนี้ (รันครั้งเดียวแล้วจบ ไม่วนลูป)
สำหรับให้ OpenClaw / cron / Task Scheduler เรียกหลังเวลาเลิกงาน

- รันครั้งเดียว: ตรวจรายการ → ส่งผลไป Cliq (ถ้ากำหนด CLIQ_WEBHOOK_URL) → จบ (ไม่มี while loop)
- ตั้งเวลา: ใช้ cron หรือ Windows Task Scheduler ให้รันคำสั่งนี้ที่เวลาที่ต้องการ (เช่น 18:00)

ใช้ .env: LINE_OA_URL, LINE_OA_CHROME_DEBUG_PORT, CLIQ_WEBHOOK_URL (ถ้าต้องการส่งผลไป Cliq)
หรือส่งผ่านอาร์กิวเมนต์: --url, --connect-chrome, --cliq / --cliq-webhook-url
"""
import argparse
import os
import sys

# โฟลเดอร์เดียวกับสคริปต์ เพื่อโหลด .env และ import module ในโฟลเดอร์นี้
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# โหลด .env ก่อน (ซ้ำกับใน line_oa_unread_messages ก็ไม่เป็นไร)
def _load_dotenv():
    env_path = os.path.join(SCRIPT_DIR, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key:
                        os.environ.setdefault(key, value)
    except Exception:
        pass


_load_dotenv()

# เรียกใช้โหมด read-not-replied-today จากสคริปต์หลัก (รันครั้งเดียวแล้วจบ)
from line_oa_unread_messages import scrape_line_oa_unread_messages_continuous

if __name__ == "__main__":
    default_url = os.environ.get("LINE_OA_URL", "").strip()
    chrome_port = (
        (os.environ.get("LINE_OA_CHROME_DEBUG_PORT") or os.environ.get("CHROME_DEBUG_PORT") or "").strip() or None
    )
    default_cliq_url = os.environ.get("CLIQ_WEBHOOK_URL", "").strip() or None

    parser = argparse.ArgumentParser(
        description="LINE OA - ตรวจอ่านแล้วแต่ยังไม่ตอบของวันนี้ (รันครั้งเดียว สำหรับ cron)"
    )
    parser.add_argument("--url", default=default_url, help="URL หน้าแชท LINE OA (หรือใช้ LINE_OA_URL ใน .env)")
    parser.add_argument("--connect-chrome", type=str, default=chrome_port, metavar="PORT",
                        help="เชื่อมต่อ Chrome ที่เปิดอยู่แล้ว (หรือใช้ LINE_OA_CHROME_DEBUG_PORT ใน .env)")
    parser.add_argument("--cliq", action="store_true", help="ส่งผลรายงานไป Cliq (ใช้ CLIQ_WEBHOOK_URL ใน .env)")
    parser.add_argument("--cliq-webhook-url", type=str, default=default_cliq_url, metavar="URL",
                        help="Webhook URL ของ Cliq (หรือใช้ CLIQ_WEBHOOK_URL ใน .env)")
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    parser.add_argument("--for-test", action="store_true", dest="for_test",
                        help="โหมดทดสอบ: เช็คเฉพาะแชทที่แสดง Yesterday")
    args = parser.parse_args()

    if not args.url:
        print("กรุณาตั้ง LINE_OA_URL ใน .env หรือส่ง --url", file=sys.stderr)
        sys.exit(1)

    cliq_url = (args.cliq_webhook_url or "").strip() or (default_cliq_url if args.cliq else None)
    scrape_line_oa_unread_messages_continuous(
        args.url,
        check_interval_seconds=30,
        debug=args.debug,
        max_hours=None,
        chrome_debug_port=args.connect_chrome,
        report_format="read-not-replied-today",
        cliq_webhook_url=cliq_url,
        for_test=args.for_test,
    )
