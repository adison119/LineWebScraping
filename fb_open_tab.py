# -*- coding: utf-8 -*-
"""
จัดการแท็บ — open_new_tab / close_current_tab
"""
import sys
import time


def _create_new_tab(driver, debug=False):
    """
    สร้างแท็บใหม่ — ลอง 3 วิธีตามลำดับ:
    1) Selenium 4 switch_to.new_window('tab')
    2) CDP Target.createTarget
    3) JavaScript window.open
    คืน handle ของแท็บใหม่
    """
    before_handles = set(driver.window_handles)

    # วิธี 1: Selenium 4+
    try:
        driver.switch_to.new_window("tab")
        new_handles = set(driver.window_handles) - before_handles
        if new_handles:
            h = new_handles.pop()
            if debug:
                print("[DEBUG] สร้างแท็บใหม่ด้วย switch_to.new_window('tab')", file=sys.stderr)
            return h
    except Exception as e:
        if debug:
            print(f"[DEBUG] new_window('tab') ไม่สำเร็จ: {e}", file=sys.stderr)

    # วิธี 2: CDP
    try:
        result = driver.execute_cdp_cmd("Target.createTarget", {"url": "about:blank"})
        time.sleep(0.5)
        new_handles = set(driver.window_handles) - before_handles
        if new_handles:
            h = new_handles.pop()
            driver.switch_to.window(h)
            if debug:
                print("[DEBUG] สร้างแท็บใหม่ด้วย CDP Target.createTarget", file=sys.stderr)
            return h
    except Exception as e:
        if debug:
            print(f"[DEBUG] CDP createTarget ไม่สำเร็จ: {e}", file=sys.stderr)

    # วิธี 3: JavaScript
    try:
        driver.execute_script("window.open('about:blank','_blank');")
        time.sleep(0.5)
        new_handles = set(driver.window_handles) - before_handles
        if new_handles:
            h = new_handles.pop()
            driver.switch_to.window(h)
            if debug:
                print("[DEBUG] สร้างแท็บใหม่ด้วย window.open", file=sys.stderr)
            return h
    except Exception as e:
        if debug:
            print(f"[DEBUG] window.open ไม่สำเร็จ: {e}", file=sys.stderr)

    return None


def open_new_tab(driver, url, debug=False):
    """
    สร้างแท็บใหม่ → โหลด URL ที่กำหนด → สลับไปแท็บนั้น
    คืน handle ของแท็บใหม่
    """
    if not driver:
        return None

    new_handle = _create_new_tab(driver, debug=debug)
    if not new_handle:
        print("[ERROR] ไม่สามารถสร้างแท็บใหม่ได้ (ลองแล้วทั้ง 3 วิธี)", file=sys.stderr)
        raise SystemExit(1)

    if debug:
        print(f"[DEBUG] กำลังโหลด: {url[:120]}", file=sys.stderr)

    driver.get(url)
    time.sleep(3)

    if debug:
        print(f"[DEBUG] โหลดเสร็จ — URL ปัจจุบัน: {driver.current_url or '(ไม่มี URL)'}", file=sys.stderr)

    return new_handle


def close_current_tab(driver, debug=False):
    """
    ปิดแท็บปัจจุบัน แล้วสลับกลับไปแท็บที่เหลืออยู่
    """
    if not driver:
        return
    try:
        url = driver.current_url or "(ไม่มี URL)"
        driver.close()
        if debug:
            print(f"[DEBUG] ปิดแท็บ: {url[:120]}", file=sys.stderr)
        remaining = driver.window_handles
        if remaining:
            driver.switch_to.window(remaining[0])
    except Exception as e:
        if debug:
            print(f"[DEBUG] close_current_tab error: {e}", file=sys.stderr)
