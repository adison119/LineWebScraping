# -*- coding: utf-8 -*-
"""
LINE OA - รายงานแชทที่คุยกันเกิน N บทสนทนา (รันครั้งเดียวแล้วจบ)
อ้างอิงจาก line_oa_read_not_replied_once.py

- รายการแชทฝั่งซ้าย: เช็คเฉพาะวันนี้และเมื่อวาน (ไม่เลื่อนไปแชทเก่ากว่าเมื่อวาน)
- ตรวจแต่ละแชท นับจำนวนบทสนทนา (ลูกค้าทักมา เราตอบกลับ = 1 บทสนทนา)
- รายงานเฉพาะแชทที่จำนวนบทสนทนาเกิน threshold (ค่าเริ่มต้น 5)

ใช้ .env: LINE_OA_URL, LINE_OA_CHROME_DEBUG_PORT
หรือส่งผ่านอาร์กิวเมนต์: --url, --connect-chrome, --ports, --threshold
"""
import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


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

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

from line_oa_unread_messages import (
    CONVERSATION_SELECTORS,
    _back_to_list,
    _connect_to_existing_chrome,
    _get_our_chat_header_names,
    _is_port_in_use,
    _open_conversation,
    _parse_ports,
    _parse_urls,
    _random_delay,
    _reload_current_page_and_wait,
    _room_label_from_url,
    count_exchanges_in_open_chat,
    get_all_conversation_rows,
    safe_find_text,
)

DEFAULT_THRESHOLD = 5


def run_long_chats_report(
    url,
    chrome_debug_port=None,
    chrome_debug_ports=None,
    threshold=DEFAULT_THRESHOLD,
    debug=False,
):
    """
    รันครั้งเดียว: โหลดหน้า → ดึงรายการแชททั้งหมด → เปิดแต่ละแชท นับบทสนทนา (ลูกค้า↔เราตอบกัน)
    → รายงานเฉพาะแชทที่จำนวนบทสนทนา > threshold → พิมพ์รายงาน
    """
    if debug:
        print("[DEBUG] โหมด debug เปิด — จะพิมพ์ขั้นตอนและผลนับทุกแชท", file=sys.stderr)
    urls = _parse_urls(url)
    if not urls:
        print("ไม่พบ URL กรุณาระบุ --url หรือ LINE_OA_URL", file=sys.stderr)
        raise SystemExit(1)
    port_src = (chrome_debug_ports or chrome_debug_port or "").strip()
    default_port = (str(chrome_debug_port or "9222").strip().split(",")[0].strip() or "9222")
    ports = _parse_ports(port_src, default_port, len(urls))
    url_port_pairs = list(zip(urls, ports))
    multi_port = len(set(ports)) > 1

    all_results = []  # list of (room_label, [(name, count), ...])

    def run_one_driver(driver, one_url, room_label):
        if debug:
            print(f"[DEBUG] {room_label} โหลดหน้า", file=sys.stderr)
        _reload_current_page_and_wait(driver, wait_seconds=5)
        rows = get_all_conversation_rows(driver, wait_seconds=5, debug=debug, today_yesterday_only=True)
        if debug:
            print(f"[DEBUG] {room_label} ได้ {len(rows)} แชท (วันนี้/เมื่อวาน)", file=sys.stderr)
        if debug and not rows:
            print(f"[DEBUG] ไม่มีแชทวันนี้หรือเมื่อวาน ในรายการซ้าย", file=sys.stderr)
        long_chats = []
        conv_xpath = CONVERSATION_SELECTORS[0][0]
        name_xpath = CONVERSATION_SELECTORS[0][1]
        for row in rows:
            try:
                elem = row["element"]
                try:
                    _open_conversation(driver, elem)
                except Exception as stale_err:
                    if not isinstance(stale_err, StaleElementReferenceException):
                        raise
                    convs = driver.find_elements(By.XPATH, conv_xpath)
                    elem = None
                    for c in convs:
                        if (safe_find_text(c, name_xpath) or "").strip() == row["name"]:
                            elem = c
                            break
                    if elem is None:
                        if debug:
                            print(f"[DEBUG] ไม่เจอแชท {row['name']!r} ข้าม", file=sys.stderr)
                        continue
                    _open_conversation(driver, elem)
                if debug:
                    print(f"[DEBUG] เปิดแชท: {row['name']!r}", file=sys.stderr)
                our_names = _get_our_chat_header_names()
                count = count_exchanges_in_open_chat(driver, our_names=our_names, max_scrolls=50, pause=0.4, debug=debug)
                if debug:
                    status = "เกิน threshold" if count > threshold else "ไม่เกิน"
                    print(f"[DEBUG] {row['name']!r}: {count} บทสนทนา ({status}, threshold={threshold})", file=sys.stderr)
                if count > threshold:
                    long_chats.append((row["name"], count))
                _back_to_list(driver)
                _random_delay(1.0, 2.5)
            except Exception as e:
                if debug:
                    print(f"[DEBUG] skip {row.get('name')!r}: {e}", file=sys.stderr)
                try:
                    _back_to_list(driver)
                except Exception:
                    pass
                _random_delay(0.8, 2.0)
        all_results.append((room_label, long_chats))

    if multi_port:
        for i, (one_url, port) in enumerate(url_port_pairs):
            try:
                port_num = int(port)
            except ValueError:
                port_num = 9222
            if not _is_port_in_use(port_num):
                print(f"Port {port} ไม่ได้เปิดอยู่ ข้าม {one_url}", file=sys.stderr)
                continue
            try:
                d = _connect_to_existing_chrome(port)
                d.get(one_url)
                time.sleep(0.8)
                room = _room_label_from_url(one_url, i)
                run_one_driver(d, one_url, room)
                d.quit()
            except Exception as e:
                print(f"ผิดพลาดที่ port {port}: {e}", file=sys.stderr)
    else:
        first_port = ports[0]
        try:
            port_num = int(first_port)
        except ValueError:
            port_num = 9222
        if not _is_port_in_use(port_num):
            print(f"Port {first_port} is not in use. Run start_chrome_for_script first.", file=sys.stderr)
            raise SystemExit(1)
        try:
            driver = _connect_to_existing_chrome(first_port)
        except Exception as e:
            print(f"เชื่อมต่อ Chrome ไม่สำเร็จ: {e}", file=sys.stderr)
            raise SystemExit(1)
        if len(urls) == 1:
            from line_oa_unread_messages import _switch_to_line_oa_tab
            _switch_to_line_oa_tab(driver, urls[0])
        else:
            from line_oa_unread_messages import _ensure_tab_for_url
            _ensure_tab_for_url(driver, urls[0])
        room = _room_label_from_url(urls[0], 0) if len(urls) == 1 else "LINE OA"
        try:
            run_one_driver(driver, urls[0], room)
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    # สร้างรายงาน
    lines = []
    lines.append(f"Line แชทที่คุยกันเกิน {threshold} บทสนทนา")
    lines.append("---")
    for room_label, long_chats in all_results:
        if len(all_results) > 1:
            lines.append(f"【{room_label}】")
        for name, count in long_chats:
            lines.append(f"ชื่อ: {name} — {count} บทสนทนา")
        if len(all_results) > 1 and long_chats:
            lines.append("")
    if not any(long_chats for _, long_chats in all_results):
        lines.append("ไม่พบแชทที่คุยกันเกินจำนวนที่กำหนด")
    report_text = "\n".join(lines)
    print(report_text)


if __name__ == "__main__":
    default_url = os.environ.get("LINE_OA_URL", "").strip()
    chrome_port = (
        (os.environ.get("LINE_OA_CHROME_DEBUG_PORT") or os.environ.get("CHROME_DEBUG_PORT") or "").strip() or None
    )
    line_oa_ports = (os.environ.get("LINE_OA_PORTS", "") or "").strip() or chrome_port

    parser = argparse.ArgumentParser(
        description="LINE OA - รายงานแชทที่คุยกันเกิน N บทสนทนา (รันครั้งเดียว)"
    )
    parser.add_argument("--url", default=default_url, help="URL หน้าแชท LINE OA (หรือใช้ LINE_OA_URL ใน .env)")
    parser.add_argument("--connect-chrome", type=str, default=chrome_port, metavar="PORT",
                        help="เชื่อมต่อ Chrome (หรือใช้ LINE_OA_CHROME_DEBUG_PORT ใน .env)")
    parser.add_argument("--ports", type=str, default=line_oa_ports, metavar="PORTS",
                        help="รายการ port คั่น comma สอดคล้องกับ --url (หลายห้อง)")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, metavar="N",
                        help=f"รายงานเมื่อจำนวนบทสนทนา (ลูกค้า↔เราตอบกัน) มากกว่า N (ค่าเริ่มต้น {DEFAULT_THRESHOLD})")
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    args = parser.parse_args()

    if not args.url:
        print("กรุณาตั้ง LINE_OA_URL ใน .env หรือส่ง --url", file=sys.stderr)
        sys.exit(1)

    run_long_chats_report(
        args.url,
        chrome_debug_port=args.connect_chrome,
        chrome_debug_ports=args.ports,
        threshold=args.threshold,
        debug=args.debug,
    )
