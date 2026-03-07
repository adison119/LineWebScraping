# -*- coding: utf-8 -*-
"""
โหลดข้อมูลแชทด้วยการเลื่อน — 1 ฟังก์ชัน: scroll_load_threads()

ขั้นตอน:
  1) เลื่อนลงจนเจอฟอร์มวันที่ (วว/ดด/ปป) → กลับบนสุด → รอ 5 วิ (รอบที่ 1)
  2) เลื่อนลงอีกครั้งให้ไกลขึ้นจากค่าครั้งแรก (ครั้งแรก + เล็กน้อย) → กลับบนสุด → รอ 5 วิ (รอบที่ 2)
  3) ดึง threads รอบที่ 1
  4) เลื่อนขึ้นบนสุดอีกครั้ง
  5) ดึง threads รอบที่ 2
  6) รวมผลและ deduplicate
"""
import time

from fb_get_threads import (
    get_facebook_threads,
    scroll_inbox_to_top,
    scroll_down_until_date_then_back_to_top,
    DEFAULT_WAIT,
    WITHIN_DAYS_DEFAULT,
)


def scroll_load_threads(driver, *, unread_only=False, read_not_replied_only=False,
                        within_days=WITHIN_DAYS_DEFAULT, within_today_only=False,
                        scroll_to_load_week=True, debug=False):
    """
    เลื่อนลงจนเจอ dd/mm/yy → เลื่อนขึ้นบนสุด → ตรวจสอบ 2 ครั้ง → dedup → คืน threads
    ใช้ได้ทุกโหมด (unread / read-not-replied / all)
    """
    if scroll_to_load_week:
        # รอบที่ 1: เลื่อนจนเจอ dd/mm/yy เก็บจำนวนครั้งที่เลื่อน
        first_scroll_count = scroll_down_until_date_then_back_to_top(
            driver, max_scrolls=200, min_scrolls=0, debug=debug
        )
        # รอบที่ 2: เลื่อนให้ไกลขึ้นจากครั้งแรก (ครั้งแรก + 40 รอบ แล้วค่อยเช็คฟอร์ม)
        extra = 40
        scroll_down_until_date_then_back_to_top(
            driver,
            max_scrolls=first_scroll_count + extra + 100,
            min_scrolls=first_scroll_count + extra,
            debug=debug,
        )

    def _collect():
        return get_facebook_threads(
            driver,
            unread_only=unread_only,
            read_not_replied_only=read_not_replied_only,
            within_week=True,
            within_days=within_days,
            within_today_only=within_today_only,
            scroll_to_load_week=scroll_to_load_week,
            wait_seconds=DEFAULT_WAIT,
            debug=debug,
        )

    threads1 = _collect()

    if scroll_to_load_week:
        scroll_inbox_to_top(driver, wait_seconds=DEFAULT_WAIT)
        time.sleep(0.8)
        threads2 = _collect()
    else:
        threads2 = []

    seen_keys = set()
    merged = []
    for t in threads1 + threads2:
        key = (t.get("sender") or "", t.get("time") or "", (t.get("message") or "")[:80])
        if key not in seen_keys:
            seen_keys.add(key)
            merged.append(t)

    return merged
