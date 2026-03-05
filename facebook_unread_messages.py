# -*- coding: utf-8 -*-
"""
Facebook Inbox (Biz Web) - ดึงรายการแชท ยังไม่อ่าน / อ่านแล้วแต่ยังไม่ตอบ
ใช้โครงสร้าง HTML หน้า Inbox (data-surface bizweb:INBOX/thread_row, class _at41, _284c, _at42 ฯลฯ)
รันด้วย --debug เพื่อดู HTML/class ถ้า selector ไม่ตรง
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from calendar import monthrange
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv():
    """โหลด .env แบบง่าย (ไม่ต้องติดตั้ง python-dotenv)"""
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

DEFAULT_WAIT = 15
CHROME_USER_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "chrome_profile_facebook"))

# Facebook Inbox: แถวแชท = div._at41._8gcz ที่มี span[data-surface*="bizweb:INBOX/thread_row"]
# ชื่อ = ._4k8x // div.x12nagc, preview = ._at42, เวลา = ._at43
# แถวที่มี _284c = ยังไม่อ่าน (ตัวหนา); แถวที่อ่านแล้วไม่มี _284c มักมี _2tms (ข้อความสีจาง)
# แถวยังไม่อ่าน: div[role=presentation] มี class แบบ " _at41 _8gcz _at_m _5_n1 _284c _5m10"
# แถวอ่านแล้ว: div[role=presentation] มี class แบบ " _at41 _8gcz _at_m _2tms _5_n1 _5m10" (ไม่มี _284c มี _2tms)
# ตอบแล้ว = ข้อความใน ._at42 ขึ้นต้น "คุณ:"
CONVERSATION_SELECTORS = [
    (
        "//span[contains(@data-surface,'bizweb:INBOX/thread_row')]/ancestor::div[contains(@class,'_at41')][1]",
        ".//div[contains(@class,'_4k8x')]//div[contains(@class,'x12nagc')]",
        ".//div[contains(@class,'_at42')]//div[contains(@class,'_4ik4')]",
        ".//div[contains(@class,'_at43')]",
    ),
    (
        "//div[contains(@class,'_at41') and contains(@class,'_8gcz')]",
        ".//div[contains(@class,'_4k8x')]//div[contains(@class,'x12nagc')]",
        ".//div[contains(@class,'_at42')]//div[contains(@class,'_4ik4')]",
        ".//div[contains(@class,'_at43')]",
    ),
]

# แถวที่มี class _284c = ยังไม่อ่าน (ตัวหนา); แถวอ่านแล้วไม่มี _284c แต่มี _2tms (สีจาง)
UNREAD_MARKER_CLASS = "_284c"
READ_MARKER_CLASS = "_2tms"
# ข้อความที่เราตอบแล้วจะขึ้นต้นด้วย "คุณ:" (ใน ._at42); ถ้าไม่มี "คุณ:" = ยังไม่ตอบ
REPLIED_PREFIX = "คุณ:"
# ข้อความระบบของ Facebook = นับว่าอ่านแล้ว ไม่แจ้งเตือน
SYSTEM_PREVIEW_PREFIXES = [
    "ตั้งระยะข้อมูลลูกค้า",
]

# ตัวย่อวันภาษาไทย (จ. อ. พ. ฯลฯ) -> weekday (0=จันทร์, 6=อาทิตย์)
THAI_DAY_ABBREVS = {"จ.": 0, "อ.": 1, "พ.": 2, "พฤ.": 3, "ศ.": 4, "ส.": 5, "อา.": 6}
# ชื่อวันเต็มจาก FB Inbox (span.accessible_elem เช่น วันจันทร์, วันอังคาร)
THAI_DAY_FULL_NAMES = {"วันจันทร์": 0, "วันอังคาร": 1, "วันพุธ": 2, "วันพฤหัสบดี": 3, "วันศุกร์": 4, "วันเสาร์": 5, "วันอาทิตย์": 6}
# ค่าเริ่มต้น: 3 วัน = วันนี้, เมื่อวาน, เมื่อวานก่อน (FB มักแสดงเป็นวันในสัปดาห์ จ. อ. พ. แทนคำว่า เมื่อวาน)
WITHIN_DAYS_DEFAULT = 3


def _allowed_weekdays_for_days_back(within_days):
    """
    ใช้ datetime บอกวันปัจจุบัน แล้วนับถอยหลัง within_days วัน หาว่าแต่ละวันเป็นวันอะไรของสัปดาห์ (0=จันทร์, 6=อาทิตย์)
    คืน set ของ weekday ที่อยู่ในช่วงวันนี้ ~ เมื่อวาน(ก่อน) ตาม within_days
    """
    now = datetime.now()
    allowed = set()
    for i in range(within_days):
        d = now - timedelta(days=i)
        allowed.add(d.weekday())
    return allowed


def _is_time_within_week(time_text, within_days=WITHIN_DAYS_DEFAULT):
    """
    เช็คว่าข้อความเวลา (จาก FB Inbox) อยู่ในช่วง within_days วันหรือไม่
    ใช้วันปัจจุบัน (datetime) นับถอยหลัง within_days วัน แล้วดูว่าเป็นวันอะไรของสัปดาห์; ถ้า FB แสดงเป็นจ. อ. พ. หรือวันจันทร์ ฯลฯ เราเทียบว่า weekday นั้นอยู่ในเซตนี้หรือไม่
    รองรับ: วันนี้, เมื่อวาน, เมื่อวานก่อน, ชื่อวันเต็ม (วันจันทร์ ฯลฯ), ตัวย่อวัน (จ. อ. พ. ฯลฯ), วันที่ เช่น 26 ก.พ.
    """
    if not (time_text or "").strip():
        return True
    s = (time_text or "").strip()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    allowed_weekdays = _allowed_weekdays_for_days_back(within_days)

    if "วันนี้" in s:
        return True
    if "เมื่อวาน" in s or "วานนี้" in s:
        return within_days >= 1
    if "เมื่อวานก่อน" in s or "วานก่อน" in s:
        return within_days >= 2

    # เช็คชื่อวันเต็ม (วันจันทร์ ฯลฯ): ใช้เซตวันที่อนุญาตจากวันปัจจุบันนับถอยหลัง
    for day_name, weekday in THAI_DAY_FULL_NAMES.items():
        if day_name in s:
            return weekday in allowed_weekdays

    # เช็คตัวย่อวัน (จ. อ. พ. ฯลฯ): เทียบกับเซตวันที่อนุญาต
    for abbr, weekday in THAI_DAY_ABBREVS.items():
        if abbr in s:
            return weekday in allowed_weekdays

    thai_month_abbrevs = [
        "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
    ]
    for i, m in enumerate(thai_month_abbrevs):
        if m in s:
            match = re.search(r"(\d{1,2})\s*" + re.escape(m), s)
            if match:
                try:
                    day = int(match.group(1))
                    month = i + 1
                    msg_date = now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
                    maxday = monthrange(msg_date.year, msg_date.month)[1]
                    msg_date = msg_date.replace(day=min(day, maxday))
                    if msg_date > now:
                        msg_date = msg_date.replace(year=now.year - 1)
                    delta = (today_start - msg_date).days
                    return 0 <= delta <= within_days
                except (ValueError, TypeError):
                    pass
            return True
    return True


def _is_time_today(time_text):
    """เช็คว่าข้อความเวลาอ้างถึงวันนี้เท่านั้น (มี "วันนี้" ในข้อความจาก FB Inbox)"""
    if not (time_text or "").strip():
        return False
    return "วันนี้" in (time_text or "").strip()


def _is_weekday_style_time(time_text):
    """
    เช็คว่าเวลาอยู่ในรูปแบบ "วันในสัปดาห์" (วันนี้, เมื่อวาน, จ. อ. พ. วันจันทร์ ฯลฯ)
    คืน False ถ้าเป็น "วันที่" เช่น 26 ก.พ. = เลื่อนเลยสัปดาห์แล้ว
    """
    if not (time_text or "").strip():
        return False
    s = (time_text or "").strip()
    if "วันนี้" in s or "เมื่อวาน" in s or "วานนี้" in s or "เมื่อวานก่อน" in s or "วานก่อน" in s:
        return True
    for abbr in THAI_DAY_ABBREVS:
        if abbr in s:
            return True
    for name in THAI_DAY_FULL_NAMES:
        if name in s:
            return True
    thai_month_abbrevs = [
        "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
        "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
    ]
    for m in thai_month_abbrevs:
        if re.search(r"\d{1,2}\s*" + re.escape(m), s):
            return False
    return False


def _scroll_through_rows_one_by_one(driver, rows, scroll_pause=0.25):
    """
    เลื่อน container ลงทีละแถว (scrollTop เพิ่ม) เพื่อให้ Facebook โหลดแถวแชทด้านล่างเพิ่ม
    เรียกหลังจากตรวจ/ประมวลผลทุก element ปัจจุบันครบแล้ว
    """
    if not rows or len(rows) == 0:
        return
    try:
        first_row = rows[0]
        scrollable = driver.execute_script("""
            var el = arguments[0];
            var p = el.parentElement;
            while (p) {
                if (p.scrollHeight > p.clientHeight && p.scrollHeight > 200) return p;
                p = p.parentElement;
            }
            return null;
        """, first_row)
        if not scrollable:
            return
        for row in rows:
            try:
                row_height = driver.execute_script(
                    "return arguments[0].offsetHeight || 100;", row
                )
                driver.execute_script(
                    "var s = arguments[0]; s.scrollTop = s.scrollTop + arguments[1];",
                    scrollable,
                    row_height,
                )
                time.sleep(scroll_pause)
            except Exception:
                continue
    except Exception:
        pass


def _is_system_preview(preview_text):
    """เช็คว่า preview เป็นข้อความระบบของ Facebook = นับว่าอ่านแล้ว"""
    if not (preview_text or "").strip():
        return False
    s = (preview_text or "").strip()
    for prefix in SYSTEM_PREVIEW_PREFIXES:
        if prefix and s.startswith(prefix):
            return True
    return False


def is_counted_as_read(preview_text):
    """นับว่าอ่านแล้ว = ขึ้นต้น "คุณ:" (เราตอบ) หรือเป็นข้อความระบบ -> ไม่เอาเข้ารายงานอ่านแล้วแต่ยังไม่ตอบ"""
    return is_replied_by_us(preview_text) or _is_system_preview(preview_text)


def is_unread_element(element):
    """แถวที่มี _284c = ยังไม่อ่าน (ตัวหนา); แถวอ่านแล้วไม่มี _284c (มักมี _2tms สีจาง)"""
    try:
        cls = (element.get_attribute("class") or "")
        return UNREAD_MARKER_CLASS in cls
    except Exception:
        return False


def is_read_element(element):
    """แถวที่อ่านแล้ว = ไม่มี _284c และมี _2tms (ข้อความสีจาง); ใช้ร่วมกับ is_replied_by_us เพื่อเช็ค อ่านแล้วแต่ยังไม่ตอบ"""
    try:
        cls = (element.get_attribute("class") or "")
        return UNREAD_MARKER_CLASS not in cls and READ_MARKER_CLASS in cls
    except Exception:
        return False


def is_replied_by_us(preview_text):
    """ถ้า preview ขึ้นต้นด้วย 'คุณ:' = เราเป็นคนตอบล่าสุด = ตอบแล้ว; ถ้าไม่มี 'คุณ:' = ยังไม่ตอบ (ใช้ตรวจสอบ อ่านแล้วแต่ยังไม่ตอบ)"""
    if not (preview_text or "").strip():
        return False
    return (preview_text or "").strip().startswith(REPLIED_PREFIX)


def is_read_not_replied(row, preview_text):
    """
    ตรวจว่าแถวนี้คือ อ่านแล้วแต่ยังไม่ตอบ หรือไม่
    หลักการ: 1) แถวอ่านแล้ว = ไม่มี _284c แต่มี _2tms  2) ข้อความไม่มี "คุณ:" = ยังไม่ตอบ
    ถ้าข้อความขึ้นต้น "คุณ:" หรือเป็นข้อความระบบ = นับว่าอ่านแล้วและตอบแล้ว/ระบบ → ไม่ใช่ read_not_replied
    """
    if is_unread_element(row):
        return False
    if is_replied_by_us(preview_text) or _is_system_preview(preview_text):
        return False
    return True


def safe_find_text(parent, xpath, default=""):
    """หา element เดียวแล้วเอา .text หรือ textContent ถ้าไม่เจอคืน default"""
    try:
        el = parent.find_element(By.XPATH, xpath)
        if not el:
            return default
        s = (el.text or "").strip()
        if not s:
            s = (el.get_attribute("textContent") or "").strip()
        return s or default
    except Exception:
        return default


def get_facebook_threads(driver, unread_only=False, read_not_replied_only=False, within_week=True,
                        within_days=WITHIN_DAYS_DEFAULT, within_today_only=False,
                        scroll_to_load_week=False, scroll_pause=0.5, max_scroll_rounds=25,
                        wait_seconds=DEFAULT_WAIT, debug=False):
    """
    ดึงรายการแชทจาก Facebook Inbox
    unread_only=True: เฉพาะแถวที่มี _284c (ยังไม่อ่าน)
    read_not_replied_only=True: เฉพาะแถวที่อ่านแล้วแต่ยังไม่ตอบ (ข้ามแชทที่ยังไม่อ่าน และแถวที่ preview ขึ้นต้น "คุณ:" หรือข้อความระบบ)
    within_week=True: กรองเฉพาะแชทที่เวลาอยู่ในช่วง within_days วัน
    within_today_only=True: กรองเฉพาะแชทที่เวลาเป็น "วันนี้" เท่านั้น
    scroll_to_load_week=True: หลังตรวจทุกแถวที่โหลดแล้ว เลื่อนลงทีละ 1 แถว แล้วลูปตรวจใหม่ จนกว่าแถวที่เห็นจะเป็น "วันที่" (ไม่มีวันตามสัปดาห์ เช่น 26 ก.พ.) จึงหยุด
    """
    result = []
    seen_keys = set()
    try:
        wait = WebDriverWait(driver, wait_seconds)
        for conv_xpath, _n, _p, _t in CONVERSATION_SELECTORS:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
                break
            except Exception:
                continue

        prev_count = 0
        for _round in range(max_scroll_rounds if scroll_to_load_week else 1):
            for conv_xpath, name_xpath, preview_xpath, time_xpath in CONVERSATION_SELECTORS:
                try:
                    rows = driver.find_elements(By.XPATH, conv_xpath)
                except Exception:
                    rows = []
                if not rows:
                    continue

                read_marker_used = any(
                    UNREAD_MARKER_CLASS in (r.get_attribute("class") or "") for r in rows
                )
                time_texts_in_batch = []

                for row in rows:
                    try:
                        name_text = safe_find_text(row, name_xpath)
                        preview_text = safe_find_text(row, preview_xpath)
                        time_text = safe_find_text(row, time_xpath)
                        time_texts_in_batch.append(time_text or "")
                        if unread_only:
                            if not is_unread_element(row):
                                continue
                        if read_not_replied_only:
                            if read_marker_used and is_unread_element(row):
                                continue
                            if is_counted_as_read(preview_text):
                                continue
                        if not (name_text or preview_text or time_text):
                            continue
                        key = (name_text or "", time_text or "", (preview_text or "")[:80])
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        item = {
                            "sender": name_text or "(ไม่มีชื่อ)",
                            "message": preview_text or "(ไม่มีข้อความ)",
                            "time": time_text or "(ไม่มีเวลา)",
                        }
                        if not scroll_to_load_week:
                            item["element"] = row
                        result.append(item)
                        if debug:
                            print(f"[DEBUG] sender={item['sender']!r}, preview={item['message'][:50]!r}...", file=sys.stderr)
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG] skip row: {e}", file=sys.stderr)
                        continue

                if result:
                    break
            if not result and _round == 0:
                break
            if scroll_to_load_week:
                if not time_texts_in_batch:
                    break
                has_passed_boundary = any(
                    (t or "").strip() and not _is_time_within_week(t, within_days=within_days)
                    for t in time_texts_in_batch
                )
                if has_passed_boundary:
                    break
                _scroll_through_rows_one_by_one(driver, rows, scroll_pause=scroll_pause)
            else:
                break
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงรายการแชท Facebook: {e}", file=sys.stderr)

    if within_week and result:
        result = [t for t in result if _is_time_within_week(t.get("time") or "", within_days=within_days)]
    if within_today_only and result:
        result = [t for t in result if _is_time_today(t.get("time") or "")]
    return result


def debug_page_structure(driver, wait_seconds=DEFAULT_WAIT):
    """โหมด debug: พิมพ์จำนวนแถวแชทและ class ของแถวแรก"""
    print("\n--- โหมด Debug: กำลังรอให้หน้าโหลด... ---", file=sys.stderr)
    time.sleep(wait_seconds)
    try:
        for conv_xpath, _n, _p, _t in CONVERSATION_SELECTORS:
            rows = driver.find_elements(By.XPATH, conv_xpath)
            if rows:
                print(f"เจอ {len(rows)} แถว (selector ชุดที่ใช้)", file=sys.stderr)
                cls = (rows[0].get_attribute("class") or "")
                print(f"แถวแรก class: {cls!r}", file=sys.stderr)
                break
        else:
            print("ไม่พบแถวแชท — ลองตรวจ selector หรือรอให้หน้าโหลด", file=sys.stderr)
    except Exception as e:
        print(f"Debug error: {e}", file=sys.stderr)
    print("--- สิ้นสุด Debug ---\n", file=sys.stderr)


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


def _find_openclaw_cmd(openclaw_cmd=None):
    if openclaw_cmd and os.path.isfile(openclaw_cmd):
        return openclaw_cmd
    for path in ("/opt/homebrew/bin/openclaw", "/usr/local/bin/openclaw"):
        if os.path.isfile(path):
            return path
    extra_paths = os.pathsep.join([
        os.environ.get("PATH", ""),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ])
    found = shutil.which("openclaw", path=extra_paths)
    return found if found else "openclaw"


def send_via_openclaw(message, target="webchat", openclaw_cmd=None):
    if not message or not message.strip():
        return False
    cmd = _find_openclaw_cmd(openclaw_cmd)
    env = os.environ.copy()
    env.setdefault("PATH", "")
    for p in ("/opt/homebrew/bin", "/usr/local/bin"):
        if p not in env["PATH"]:
            env["PATH"] = p + os.pathsep + env["PATH"]
    try:
        result = subprocess.run(
            [cmd, "message", "send", "-t", target, "--message", message.strip()],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
            print(f"[openclaw] returncode={result.returncode} target={target!r}", file=sys.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print("ไม่พบคำสั่ง openclaw — ส่งผลไปไลน์ไม่สำเร็จ", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ส่ง openclaw ไม่สำเร็จ: {e}", file=sys.stderr)
        return False


def _send_report_to_openclaw_targets(message, send_openclaw_target):
    if not message or not send_openclaw_target:
        return
    targets = [t.strip() for t in str(send_openclaw_target).split(",") if t.strip()]
    for t in targets:
        send_via_openclaw(message, target=t)


def _switch_to_fb_inbox_tab(driver, url):
    """สลับไปแท็บที่มีหน้า FB Inbox หรือเปิด url"""
    url = (url or "").strip()
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        cur = (driver.current_url or "").strip()
        if url and (cur == url or url in cur):
            return True
        if "business.facebook.com" in cur or "facebook.com" in cur and "inbox" in cur.lower():
            if not url:
                return True
            if url in cur:
                return True
    if url:
        driver.get(url)
    return True


def scrape_facebook_inbox(url, report_format="summary-once", chrome_debug_port=None,
                          send_openclaw_target=None, unread_only=True, within_days=WITHIN_DAYS_DEFAULT,
                          within_today_only=False, scroll_to_load_week=True, debug=False):
    """
    เปิด Chrome ไปที่ url (FB Inbox), ดึงรายการแชท ตาม report_format
    report_format: summary-once | read-not-replied-today
    within_days: กรองเฉพาะแชทภายในกี่วัน (ค่าเริ่มต้น 3 = วันนี้, เมื่อวาน, เมื่อวานก่อน)
    within_today_only: กรองเฉพาะแชทที่เวลาเป็น "วันนี้" เท่านั้น
    scroll_to_load_week: หลังตรวจทุกแถวที่โหลดแล้วเลื่อนไปแถวสุดท้ายเพื่อโหลดแถวเพิ่มจนครบสัปดาห์
    """
    if not url or not url.strip():
        print("ไม่พบ URL กรุณาระบุ --url หรือ FB_INBOX_URL ใน .env", file=sys.stderr)
        raise SystemExit(1)

    driver = None
    use_existing = chrome_debug_port is not None and str(chrome_debug_port).strip() != ""

    if use_existing:
        port = str(chrome_debug_port).strip()
        try:
            port_num = int(port)
        except ValueError:
            port_num = 9222
        if not _is_port_in_use(port_num):
            print(f"Port {port} is not in use. Run start_chrome_for_script.bat first.", file=sys.stderr)
            raise SystemExit(1)
        try:
            driver = _connect_to_existing_chrome(port)
        except Exception as e:
            print(f"Connection failed: {e}", file=sys.stderr)
            raise SystemExit(1)
        _switch_to_fb_inbox_tab(driver, url)
        print("Connected to Chrome.", file=sys.stderr)
    else:
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
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except SessionNotCreatedException:
            print("Chrome เปิดไม่สำเร็จ แนะนำให้ใช้ --connect-chrome 9222 กับ Chrome ที่เปิดแล้ว", file=sys.stderr)
            raise SystemExit(1)
        driver.set_window_size(1280, 900)
        driver.get(url)
        time.sleep(2)
        print("โปรดล็อกอิน Facebook Inbox ในเบราว์เซอร์ที่เปิดขึ้นมา (ถ้ายัง)", file=sys.stderr)

    try:
        if debug:
            debug_page_structure(driver, wait_seconds=DEFAULT_WAIT)

        if report_format == "read-not-replied-today":
            threads = get_facebook_threads(driver, unread_only=False, read_not_replied_only=True,
                                           within_week=True, within_days=within_days,
                                           within_today_only=within_today_only,
                                           scroll_to_load_week=scroll_to_load_week,
                                           wait_seconds=DEFAULT_WAIT, debug=debug)
            lines = []
            if threads:
                lines.append("📋 Facebook Inbox: อ่านแล้วแต่ยังไม่ตอบ" + (" (วันนี้เท่านั้น)" if within_today_only else " (ทั้งสัปดาห์)"))
                for t in threads:
                    msg = (t['message'] or '')[:80]
                    if len(t.get('message') or '') > 80:
                        msg += "..."
                    lines.append(f"ชื่อ: **{t['sender']}** ข้อความ: **{msg}** เวลา: **{t['time']}**")
                lines.append(f"--- รวม {len(threads)} รายการ ---")
            else:
                lines.append("ไม่พบรายการที่อ่านแล้วและยังไม่ตอบ")
            report_text = "\n".join(lines)
            print(report_text)
            if send_openclaw_target:
                _send_report_to_openclaw_targets(report_text, send_openclaw_target)
            return

        threads = get_facebook_threads(driver, unread_only=unread_only, read_not_replied_only=False,
                                       within_week=True, within_days=within_days,
                                       within_today_only=within_today_only,
                                       scroll_to_load_week=scroll_to_load_week,
                                       wait_seconds=DEFAULT_WAIT, debug=debug)
        lines = []
        if threads:
            title = "📥 Facebook Inbox: ยังไม่อ่าน" + (" (วันนี้เท่านั้น)" if (unread_only and within_today_only) else "") if unread_only else "📥 Facebook Inbox: รายการแชท"
            lines.append(title)
            for t in threads:
                msg = (t.get('message') or '')[:80]
                if len(t.get('message') or '') > 80:
                    msg += "..."
                lines.append(f"ชื่อ: **{t['sender']}** ข้อความ: **{msg}** เวลา: **{t['time']}**")
            lines.append(f"--- รวม {len(threads)} รายการ ---")
        else:
            lines.append("ไม่พบรายการแชท" if not unread_only else "ไม่พบข้อความที่ยังไม่อ่าน")
        report_text = "\n".join(lines)
        print(report_text)
        if send_openclaw_target:
            _send_report_to_openclaw_targets(report_text, send_openclaw_target)
    finally:
        if driver and not use_existing:
            driver.quit()


if __name__ == "__main__":
    default_url = (os.environ.get("FB_INBOX_URL") or "").strip()
    chrome_port = (os.environ.get("CHROME_DEBUG_PORT") or "").strip() or None
    openclaw_target = (os.environ.get("FB_OPENCLAW_TARGET") or os.environ.get("LINE_OA_OPENCLAW_TARGET") or "").strip() or None

    parser = argparse.ArgumentParser(description="Facebook Inbox - รายการแชท (ยังไม่อ่าน / ทั้งหมด)")
    parser.add_argument("--url", default=default_url, help="URL หน้า Facebook Inbox (หรือใช้ FB_INBOX_URL ใน .env)")
    parser.add_argument("--connect-chrome", type=str, default=chrome_port, metavar="PORT",
                        help="เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (เช่น 9222)")
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
                        help="ส่งผลไป openclaw -t TARGET (หรือใช้ FB_OPENCLAW_TARGET ใน .env)")
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    args = parser.parse_args()

    if not args.url:
        print("กรุณาตั้ง FB_INBOX_URL ใน .env หรือส่ง --url", file=sys.stderr)
        raise SystemExit(1)

    scrape_facebook_inbox(
        args.url,
        report_format="summary-once",
        chrome_debug_port=args.connect_chrome,
        send_openclaw_target=args.send_openclaw_target,
        unread_only=args.unread_only,
        within_days=args.within_days,
        within_today_only=args.today_only,
        scroll_to_load_week=not args.no_scroll,
        debug=args.debug,
    )
