# -*- coding: utf-8 -*-
"""
Facebook Inbox - รายงานเฉพาะ "อ่านแล้วแต่ยังไม่ตอบ"
แยกออกจาก facebook_unread_messages.py เพื่อให้รันโหมดนี้โดยตรง
ใช้ FB_INBOX_URL, CHROME_DEBUG_PORT, FB_OPENCLAW_TARGET จาก .env
"""
import argparse
import os
import sys

# โหลด .env ก่อน import เพื่อให้ default จาก env ใช้ได้
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(SCRIPT_DIR, ".env")
if os.path.isfile(_env_path):
    try:
        with open(_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip().strip('"').strip("'")
                    if key:
                        os.environ.setdefault(key, value)
    except Exception:
        pass

from facebook_unread_messages import (
    WITHIN_DAYS_DEFAULT,
    scrape_facebook_inbox,
)


def main():
    default_url = (os.environ.get("FB_INBOX_URL") or "").strip()
    chrome_port = (os.environ.get("CHROME_DEBUG_PORT") or "").strip() or None
    openclaw_target = (
        os.environ.get("FB_OPENCLAW_TARGET") or os.environ.get("LINE_OA_OPENCLAW_TARGET") or ""
    ).strip() or None

    parser = argparse.ArgumentParser(
        description="Facebook Inbox - รายงาน อ่านแล้วแต่ยังไม่ตอบ (ไม่รวม 'คุณ:' และข้อความระบบ)"
    )
    parser.add_argument(
        "--url",
        default=default_url,
        help="URL หน้า Facebook Inbox (หรือใช้ FB_INBOX_URL ใน .env)",
    )
    parser.add_argument(
        "--connect-chrome",
        type=str,
        default=chrome_port,
        metavar="PORT",
        help="เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (เช่น 9222)",
    )
    parser.add_argument(
        "--today-only",
        action="store_true",
        help="กรองเฉพาะแชทของวันนี้เท่านั้น",
    )
    parser.add_argument(
        "--within-days",
        type=int,
        default=WITHIN_DAYS_DEFAULT,
        metavar="N",
        help="กรองเฉพาะแชทภายใน N วัน (ค่าเริ่มต้น 3)",
    )
    parser.add_argument(
        "--no-scroll",
        action="store_true",
        help="ไม่เลื่อนรายการ",
    )
    parser.add_argument(
        "--send-openclaw-target",
        type=str,
        default=openclaw_target,
        metavar="TARGET",
        help="ส่งผลไป openclaw (หรือใช้ FB_OPENCLAW_TARGET ใน .env)",
    )
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    args = parser.parse_args()

    if not args.url:
        print("กรุณาตั้ง FB_INBOX_URL ใน .env หรือส่ง --url", file=sys.stderr)
        sys.exit(1)

    scrape_facebook_inbox(
        args.url,
        report_format="read-not-replied-today",
        chrome_debug_port=args.connect_chrome,
        send_openclaw_target=args.send_openclaw_target,
        unread_only=False,
        within_days=args.within_days,
        within_today_only=args.today_only,
        scroll_to_load_week=not args.no_scroll,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
