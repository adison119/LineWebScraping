# -*- coding: utf-8 -*-
"""
เชื่อมต่อ Chrome — 1 ฟังก์ชัน: connect_chrome(chrome_debug_port) -> (driver, driver_owned)
"""
import os
import socket
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import SessionNotCreatedException

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROME_USER_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "chrome_profile_facebook"))


def _first_port(chrome_debug_port):
    """คืนพอร์ตแรกจาก FB_CHROME_DEBUG_PORT (ถ้ามีหลายคั่น comma)"""
    port_str = (chrome_debug_port or "").strip()
    if not port_str:
        return None
    parts = [p.strip() for p in port_str.split(",") if p.strip()]
    return parts[0] if parts else None


def _is_port_in_use(port=9222):
    port = int(port)
    for family, addr in [
        (socket.AF_INET, ("127.0.0.1", port)),
        (socket.AF_INET6, ("::1", port)),
    ]:
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                if s.connect_ex(addr) == 0:
                    return True
        except (OSError, socket.error):
            continue
    return False


def _connect_to_existing_chrome(debug_port):
    """เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (remote-debugging-port)"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def connect_chrome(chrome_debug_port=None):
    """
    เชื่อมต่อ Chrome: ถ้ามีพอร์ต → เชื่อมกับ Chrome ที่เปิดอยู่; ไม่มี → เปิด Chrome ใหม่
    คืน (driver, driver_owned) โดย driver_owned เป็น instance ที่เราสร้าง (ต้อง quit เอง) หรือ None
    """
    port = _first_port(chrome_debug_port)
    driver_owned = None
    driver = None

    if port:
        try:
            port_num = int(port) if str(port).strip().isdigit() else 9222
        except (ValueError, TypeError):
            port_num = 9222
        if not _is_port_in_use(port_num):
            print(f"Port {port} is not in use. Run Chrome with that port first (e.g. FB_CHROME_DEBUG_PORT={port}).", file=sys.stderr)
            raise SystemExit(1)
        try:
            driver = _connect_to_existing_chrome(port)
        except Exception as e:
            print(f"Connection failed (port {port}): {e}", file=sys.stderr)
            raise SystemExit(1)
        print(f"เชื่อม Chrome สำเร็จ (พอร์ต {port})", file=sys.stderr)
        return driver, None

    if not os.path.isdir(CHROME_USER_DATA_DIR):
        os.makedirs(CHROME_USER_DATA_DIR, exist_ok=True)
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disk-cache-size=0")
    chrome_options.add_argument("--disable-extensions")
    service = Service(ChromeDriverManager().install())
    try:
        driver_owned = webdriver.Chrome(service=service, options=chrome_options)
    except SessionNotCreatedException:
        print("Chrome เปิดไม่สำเร็จ แนะนำให้ใช้ --connect-chrome กับ Chrome ที่เปิดแล้ว (FB_CHROME_DEBUG_PORT ใน .env)", file=sys.stderr)
        raise SystemExit(1)
    driver_owned.set_window_size(1280, 900)
    print("เปิด Chrome ใหม่สำเร็จ (ไม่ใช้พอร์ต debug)", file=sys.stderr)
    return driver_owned, driver_owned
