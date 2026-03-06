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
from fb_open_tab import switch_to_first_tab
from fb_get_threads import (
    get_facebook_threads,
    scroll_inbox_to_top,
    scroll_down_until_date_then_back_to_top,
    debug_page_structure,
    DEFAULT_WAIT,
    WITHIN_DAYS_DEFAULT,
)
from fb_report import build_report
from fb_openclaw import send_report_to_openclaw


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


def scrape_facebook_inbox(url=None, report_format="summary-once", chrome_debug_port=None,
                          send_openclaw_target=None, unread_only=True, within_days=WITHIN_DAYS_DEFAULT,
                          within_today_only=False, scroll_to_load_week=True, debug=False):
    """
    เชื่อมต่อ Chrome → สลับแท็บแรก → ดึงรายการแชท → สร้างรายงาน → พิมพ์และส่ง openclaw
    ไม่เปิด/โหลด URL — ต้องเปิดหน้า FB Inbox ไว้ก่อนแล้ว
    """
    driver = None
    driver_owned = None

    try:
        driver, driver_owned = connect_chrome(chrome_debug_port)
        if not driver:
            raise SystemExit(1)
        if debug:
            n_tabs = len(driver.window_handles) if getattr(driver, "window_handles", None) else 0
            print(f"[DEBUG] เชื่อม Chrome สำเร็จ — จำนวนแท็บ: {n_tabs}", file=sys.stderr)

        first_tab_url = switch_to_first_tab(driver, debug=debug)
        print(f"รีเฟรชหน้า: {first_tab_url or driver.current_url or '(ไม่มี URL)'}", file=sys.stderr)
        driver.refresh()
        time.sleep(2)
        if debug:
            print("[DEBUG] รีเฟรชแล้ว รอ 2 วินาที", file=sys.stderr)
            print(f"[DEBUG] หน้าปัจจุบันหลังรีเฟรช: {driver.current_url or '(ไม่มี URL)'}", file=sys.stderr)
            debug_page_structure(driver, wait_seconds=DEFAULT_WAIT)

        read_not_replied = report_format == "read-not-replied-today"

        def _get_threads_one(unread_opt, read_not_replied_opt):
            return get_facebook_threads(
                driver,
                unread_only=unread_opt,
                read_not_replied_only=read_not_replied_opt,
                within_week=True,
                within_days=within_days,
                within_today_only=within_today_only,
                scroll_to_load_week=scroll_to_load_week,
                wait_seconds=DEFAULT_WAIT,
                debug=debug,
            )

        if read_not_replied and scroll_to_load_week:
            scroll_down_until_date_then_back_to_top(driver, debug=debug)
            threads1 = _get_threads_one(unread_only, True)
            scroll_inbox_to_top(driver, wait_seconds=DEFAULT_WAIT)
            time.sleep(0.8)
            threads2 = _get_threads_one(unread_only, True)
            seen_keys = set()
            all_threads = []
            for t in threads1 + threads2:
                key = (t.get("sender") or "", t.get("time") or "", (t.get("message") or "")[:80])
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_threads.append(t)
        else:
            all_threads = _get_threads_one(unread_only, read_not_replied)

        report_text = build_report(
            all_threads,
            report_format=report_format,
            unread_only=unread_only,
            within_today_only=within_today_only,
        )
        print(report_text)
        if send_openclaw_target:
            send_report_to_openclaw(report_text, send_openclaw_target)
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
    openclaw_target = (os.environ.get("LINE_OA_OPENCLAW_TARGET") or "").strip() or None

    parser = argparse.ArgumentParser(
        description="Facebook Inbox - ตรวจหาข้อความที่ยังไม่อ่าน (เชื่อมต่อ Chrome ที่เปิดหน้า Inbox ไว้แล้ว)"
    )
    parser.add_argument("--connect-chrome", type=str, default=chrome_port, metavar="PORT",
                        help="พอร์ต Chrome ที่เปิดไว้แล้ว (ใช้ FB_CHROME_DEBUG_PORT ใน .env)")
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
    parser.add_argument("--send-openclaw-target", type=str, default=openclaw_target, metavar="TARGET",
                        help="ส่งผลไป openclaw -t TARGET (หรือใช้ LINE_OA_OPENCLAW_TARGET ใน .env)")
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    args = parser.parse_args()

    scrape_facebook_inbox(
        url=None,
        report_format="summary-once",
        chrome_debug_port=args.connect_chrome,
        send_openclaw_target=args.send_openclaw_target,
        unread_only=args.unread_only,
        within_days=args.within_days,
        within_today_only=args.today_only,
        scroll_to_load_week=not args.no_scroll,
        debug=args.debug,
    )
