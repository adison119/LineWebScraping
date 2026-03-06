# -*- coding: utf-8 -*-
"""
สลับแท็บ — 1 ฟังก์ชัน: switch_to_first_tab(driver)
"""
import sys

# ไม่เปิด/โหลด URL — แค่สลับไปแท็บแรกของ driver ที่เชื่อมอยู่แล้ว


def switch_to_first_tab(driver, debug=False):
    """
    สลับไปแท็บแรก (window_handles[0])
    ถ้าไม่มีแท็บเลย จะ raise SystemExit(1) และพิมพ์ข้อความแจ้ง
    คืน URL ของแท็บแรกหลังสลับ (หรือ None ถ้าไม่มี driver)
    """
    if not driver:
        return None
    handles = getattr(driver, "window_handles", None)
    if not handles or len(handles) == 0:
        print("ไม่พบแท็บใดๆ ใน Chrome — กรุณาเปิดหน้า FB Inbox ไว้ในแท็บอย่างน้อย 1 แท็บ", file=sys.stderr)
        raise SystemExit(1)
    driver.switch_to.window(handles[0])
    url = (driver.current_url or "").strip()
    if debug:
        print(f"[DEBUG] เลือกแท็บแรก (จาก {len(handles)} แท็บ): {url or '(ไม่มี URL)'}", file=sys.stderr)
    return url
