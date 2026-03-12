# -*- coding: utf-8 -*-
"""
Facebook Inbox (Biz Web) - ดึงรายการแชท ยังไม่อ่าน / อ่านแล้วแต่ยังไม่ตอบ
Orchestrator: เรียกใช้ fb_connect_chrome, fb_open_tab, fb_get_threads, fb_report, fb_openclaw (1 ไฟล์ 1 ฟังก์ชัน)
"""
import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from fb_connect_chrome import connect_chrome
from fb_open_tab import open_new_tab, close_current_tab
from fb_get_threads import debug_page_structure, DEFAULT_WAIT, WITHIN_DAYS_DEFAULT
from fb_scroll_load import scroll_load_threads
from fb_report import build_report
from fb_openclaw import send_report_to_openclaw, send_report_to_cliq


def _load_dotenv():
    """โหลด .env แบบง่าย (ไม่ต้องติดตั้ง python-dotenv) — ดูจากโฟลเดอร์สคริปต์ก่อน แล้วลอง cwd"""
    for base in (SCRIPT_DIR, os.getcwd()):
        env_path = os.path.join(base, ".env")
        if not os.path.isfile(env_path):
            continue
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().replace("\r", "")
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if " # " in value:
                            value = value.split(" # ", 1)[0].strip()
                        if key:
                            os.environ[key] = value
            return
        except Exception:
            continue


def _scrape_one_url(driver, url, report_format, unread_only, within_days,
                    within_today_only, scroll_to_load_week, debug):
    """
    สร้างแท็บใหม่ → โหลด URL → เลื่อนโหลดข้อมูล → ตรวจสอบ 2 ครั้ง → ปิดแท็บ → คืน threads
    """
    open_new_tab(driver, url, debug=debug)

    if debug:
        print(f"[DEBUG] หน้าปัจจุบัน: {driver.current_url or '(ไม่มี URL)'}", file=sys.stderr)
        debug_page_structure(driver, wait_seconds=DEFAULT_WAIT)

    read_not_replied = report_format == "read-not-replied-today"

    threads = scroll_load_threads(
        driver,
        unread_only=unread_only,
        read_not_replied_only=read_not_replied,
        within_days=within_days,
        within_today_only=within_today_only,
        scroll_to_load_week=scroll_to_load_week,
        debug=debug,
    )

    close_current_tab(driver, debug=debug)
    return threads


def scrape_facebook_inbox(urls=None, report_format="summary-once", chrome_debug_port=None,
                          cliq_webhook_url=None, unread_only=True, within_days=WITHIN_DAYS_DEFAULT,
                          within_today_only=False, scroll_to_load_week=True, debug=False):
    """
    เชื่อมต่อ Chrome → สร้างแท็บใหม่สำหรับแต่ละ URL → สแกน → ปิดแท็บ → รายงานรวม
    urls: list ของ URL หรือ string คั่นด้วย comma
    """
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split(",") if u.strip()]
    if not urls:
        print("ไม่มี URL ให้ทำงาน — กรุณาตั้ง FB_INBOX_URL ใน .env", file=sys.stderr)
        raise SystemExit(1)

    driver = None
    driver_owned = None

    try:
        driver, driver_owned = connect_chrome(chrome_debug_port)
        if not driver:
            raise SystemExit(1)
        if debug:
            n_tabs = len(driver.window_handles) if getattr(driver, "window_handles", None) else 0
            print(f"[DEBUG] เชื่อม Chrome สำเร็จ — จำนวนแท็บ: {n_tabs}", file=sys.stderr)

        all_threads = []
        for i, url in enumerate(urls):
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"ลิงก์ที่ {i+1}/{len(urls)}: {url[:120]}", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

            threads = _scrape_one_url(
                driver, url, report_format, unread_only, within_days,
                within_today_only, scroll_to_load_week, debug,
            )
            for t in threads:
                t["_source"] = f"link_{i+1}"
            all_threads.extend(threads)

            if i < len(urls) - 1:
                time.sleep(2)

        report_text = build_report(
            all_threads,
            report_format=report_format,
            unread_only=unread_only,
            within_today_only=within_today_only,
        )
        print(report_text)
        if cliq_webhook_url:
            send_report_to_cliq(report_text, cliq_webhook_url)
    finally:
        if driver_owned:
            try:
                driver_owned.quit()
            except Exception:
                pass


if __name__ == "__main__":
    _load_dotenv()
    chrome_port = (
        (os.environ.get("FB_CHROME_DEBUG_PORT") or os.environ.get("CHROME_DEBUG_PORT") or "").strip() or None
    )
    cliq_webhook_url = (os.environ.get("CLIQ_WEBHOOK_URL") or "").strip() or None
    fb_inbox_urls = (os.environ.get("FB_INBOX_URL") or "").strip() or None

    parser = argparse.ArgumentParser(
        description="Facebook Inbox - ตรวจหาข้อความที่ยังไม่อ่าน (สร้างแท็บใหม่สำหรับแต่ละ URL จาก FB_INBOX_URL)"
    )
    parser.add_argument("--connect-chrome", type=str, default=chrome_port, metavar="PORT",
                        help="พอร์ต Chrome ที่เปิดไว้แล้ว (ใช้ FB_CHROME_DEBUG_PORT ใน .env)")
    parser.add_argument("--urls", type=str, default=fb_inbox_urls, metavar="URLS",
                        help="URL ของ FB Inbox คั่นด้วย comma (หรือใช้ FB_INBOX_URL ใน .env)")
    parser.add_argument("--unread-only", action="store_true", default=True, dest="unread_only",
                        help="รายงานเฉพาะแชทที่ยังไม่อ่าน (ค่าเริ่มต้น)")
    parser.add_argument("--all", action="store_false", dest="unread_only",
                        help="แสดงทุกแชท (ปิดโหมดยังไม่อ่าน)")
    parser.add_argument("--today-only", action="store_true",
                        help="กรองเฉพาะแชทของวันนี้เท่านั้น (ข้อความที่แสดง 'วันนี้' ในเวลา)")
    parser.add_argument("--within-days", type=int, default=WITHIN_DAYS_DEFAULT, metavar="N",
                        help="กรองเฉพาะแชทภายใน N วัน (ค่าเริ่มต้น 3 = วันนี้, เมื่อวาน, เมื่อวานก่อน)")
    parser.add_argument("--no-scroll", action="store_true",
                        help="ไม่เลื่อนรายการ (ใช้เฉพาะแถวที่โหลดบนหน้าปัจจุบัน)")
    parser.add_argument("--cliq", action="store_true", help="ส่งผลรายงานไป Cliq (ใช้ CLIQ_WEBHOOK_URL ใน .env)")
    parser.add_argument("--cliq-webhook-url", type=str, default=cliq_webhook_url, metavar="URL",
                        help="Webhook URL ของ Cliq (หรือใช้ CLIQ_WEBHOOK_URL ใน .env)")
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    args = parser.parse_args()

    scrape_facebook_inbox(
        urls=args.urls,
        report_format="summary-once",
        chrome_debug_port=args.connect_chrome,
        cliq_webhook_url=(args.cliq_webhook_url or "").strip() or (cliq_webhook_url if args.cliq else None),
        unread_only=args.unread_only,
        within_days=args.within_days,
        within_today_only=args.today_only,
        scroll_to_load_week=not args.no_scroll,
        debug=args.debug,
    )
