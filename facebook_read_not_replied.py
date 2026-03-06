# -*- coding: utf-8 -*-
"""
Facebook Inbox - รายงานเฉพาะ "อ่านแล้วแต่ยังไม่ตอบ"
แยกออกจาก facebook_unread_messages.py เพื่อให้รันโหมดนี้โดยตรง
เชื่อมต่อ Chrome แบบเดียวกับ facebook_unread_messages (ต้องเปิดหน้า Inbox ไว้ก่อน)
"""
import argparse
import os
import sys

# โหลด .env ก่อน import เพื่อให้ os.environ พร้อมก่อนที่ module อื่นจะถูกโหลด (เหมือน facebook_unread_messages)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for _base in (SCRIPT_DIR, os.getcwd()):
    _env_path = os.path.join(_base, ".env")
    if os.path.isfile(_env_path):
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip().replace("\r", "")
                    if not _line or _line.startswith("#"):
                        continue
                    if "=" in _line:
                        _k, _, _v = _line.partition("=")
                        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
                        if " # " in _v:
                            _v = _v.split(" # ", 1)[0].strip()
                        if _k:
                            os.environ[_k] = _v
            break
        except Exception:
            continue

from facebook_unread_messages import (
    WITHIN_DAYS_DEFAULT,
    scrape_facebook_inbox,
)


def main():
    # อ่านพอร์ตและส่งค่าให้ scrape_facebook_inbox แบบเดียวกับ facebook_unread_messages ทุกประการ
    chrome_port = (
        (os.environ.get("FB_CHROME_DEBUG_PORT") or os.environ.get("CHROME_DEBUG_PORT") or "").strip() or None
    )
    openclaw_target = (os.environ.get("LINE_OA_OPENCLAW_TARGET") or "").strip() or None

    parser = argparse.ArgumentParser(
        description="Facebook Inbox - รายงาน อ่านแล้วแต่ยังไม่ตอบ (เชื่อมต่อ Chrome ที่เปิดหน้า Inbox ไว้ก่อน)"
    )
    parser.add_argument(
        "--connect-chrome",
        type=str,
        default=chrome_port,
        metavar="PORT",
        help="เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (ใช้ FB_CHROME_DEBUG_PORT ใน .env)",
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
        help="ส่งผลไป openclaw (หรือใช้ LINE_OA_OPENCLAW_TARGET ใน .env)",
    )
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    args = parser.parse_args()

    # ส่งพอร์ตตรงจาก args เหมือน facebook_unread_messages (chrome_debug_port=args.connect_chrome)
    scrape_facebook_inbox(
        url=None,
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
