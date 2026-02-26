# -*- coding: utf-8 -*-
"""
LINE OA - ดึงข้อความที่ยังไม่อ่าน (แก้ selector ให้ยืดหยุ่น + โหมด debug)
ถ้า selector ยังไม่ตรงกับหน้าเว็บ ให้รันด้วย --debug ก่อน แล้วดู HTML/class ที่พิมพ์ออกมา
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import argparse
import os
import re
import socket
import subprocess
import sys

# โฟลเดอร์เดียวกับสคริปต์
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

# รอสูงสุด (วินาที)
DEFAULT_WAIT = 15
# โฟลเดอร์เก็บ profile Chrome ของสคริปต์ (ล็อกอินจะถูกจำไว้ในโฟลเดอร์นี้ เปิดครั้งถัดไปจะยังล็อกอินอยู่)
# ลบโฟลเดอร์นี้ = คืนพื้นที่ แต่ครั้งถัดไปต้องล็อกอินใหม่
CHROME_USER_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "chrome_profile_line_oa"))
# โฟลเดอร์เก็บ profile Chrome ของสคริปต์ (ล็อกอินจะถูกจำไว้ในโฟลเดอร์นี้ เปิดครั้งถัดไปจะยังล็อกอินอยู่)
# ลบโฟลเดอร์นี้ = คืนพื้นที่ แต่ครั้งถัดไปต้องล็อกอินใหม่
CHROME_USER_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "chrome_profile_line_oa"))

# รายการ selector ที่จะลองตามลำดับ
# โครงสร้าง: แถวแชท > div.flex-1.hide-on-collapse > (ชื่อใน h6, ข้อความใน div.text-muted.small.text-truncate-box)
# รายการ selector ที่จะลองตามลำดับ
# โครงสร้าง: แถวแชท > div.flex-1.hide-on-collapse > (ชื่อใน h6, ข้อความใน div.text-muted.small.text-truncate-box)
# แถวแรก = รายการแชท, ตามด้วย ชื่อ, ข้อความล่าสุด, เวลา
CONVERSATION_SELECTORS = [
    # รูปแบบจริงของ LINE OA: ข้อความอยู่ใน div.flex-1 ภายใน div.text-muted.small.text-truncate-box
    (
        "//div[contains(@class, 'list-group-item-chat')]",
        ".//div[contains(@class, 'flex-1') and contains(@class, 'hide-on-collapse')]//h6[contains(@class, 'text-truncate')]",
        ".//div[contains(@class, 'flex-1') and contains(@class, 'hide-on-collapse')]/div[contains(@class, 'text-muted') and contains(@class, 'text-truncate-box')]",
        ".//div[contains(@class, 'datetime')]",
    ),
    # fallback: หาแบบกว้างในแถว
    # รูปแบบจริงของ LINE OA: ข้อความอยู่ใน div.flex-1 ภายใน div.text-muted.small.text-truncate-box
    (
        "//div[contains(@class, 'list-group-item-chat')]",
        ".//div[contains(@class, 'flex-1') and contains(@class, 'hide-on-collapse')]//h6[contains(@class, 'text-truncate')]",
        ".//div[contains(@class, 'flex-1') and contains(@class, 'hide-on-collapse')]/div[contains(@class, 'text-muted') and contains(@class, 'text-truncate-box')]",
        ".//div[contains(@class, 'datetime')]",
    ),
    # fallback: หาแบบกว้างในแถว
    (
        "//div[contains(@class, 'list-group-item-chat')]",
        ".//h6[contains(@class, 'text-truncate')]",
        ".//div[contains(@class, 'text-muted') and contains(@class, 'small') and contains(@class, 'text-truncate')]",
        ".//div[contains(@class, 'datetime')]",
    ),
    # รูปแบบเดิม (fallback)
    (
        "//div[contains(@class, 'chat-list-item')]",
        ".//span[contains(@class, 'sender-name')]",
        ".//div[contains(@class, 'last-message-preview')]",
        ".//span[contains(@class, 'message-time')]",
    ),
    # รูปแบบที่ 2: อาจใช้ role หรือ list
    (
        "//*[@role='listitem' or @role='row']",
        ".//*[contains(@class, 'name') or contains(@class, 'sender') or contains(@class, 'title')]",
        ".//*[contains(@class, 'message') or contains(@class, 'preview') or contains(@class, 'content') or contains(@class, 'text')]",
        ".//*[contains(@class, 'time') or contains(@class, 'date')]",
    ),
    # รูปแบบที่ 3: โครงสร้างทั่วไป - div ใน list/ul
    (
        "//div[contains(@class, 'conversation')] | //li[contains(@class, 'chat')] | //*[contains(@class, 'thread')]",
        ".//span | .//*[contains(@class, 'name')]",
        ".//*[contains(@class, 'message') or contains(@class, 'body')]",
        ".//*[contains(@class, 'time') or contains(@class, 'meta')]",
    ),
]

# ไม่ใส่ "selected" / "active" เพราะแถวที่เปิดอยู่ (select) จะได้ class เหล่านั้น แต่แชทอาจอ่านแล้ว
# ใช้เฉพาะ "unread", "has-new", "new-message" เป็น fallback; ตัวตัดสินหลัก = มี span.badge-pin หรือไม่
UNREAD_CLASS_PATTERNS = ["unread", "has-new", "new-message"]

# LINE OA: ใช้เฉพาะจุดสีน้ำเงิน (badge-pin) เป็นตัวบอกยังไม่อ่าน
# มี span.badge-pin ใน div.text-right = ยังไม่อ่าน | ไม่มี badge = อ่านแล้ว (แม้แถวจะถูก select อยู่)
# หมายเหตุ: ตัวเลข (3), (7) ข้างชื่ออาจยังโชว์หลังอ่านแล้ว จึงไม่ใช้เป็นตัวตัดสิน
UNREAD_BADGE_XPATH = ".//span[contains(@class, 'badge-pin')]"

# ถ้า True จะนับเฉพาะรายการที่มี badge-pin; ถ้า False จะดึงทุกรายการ
STRICT_UNREAD_ONLY = True

# ชื่อที่ถือว่าเป็น "ของเรา" ใน chat-header (ข้อความล่าสุดจากชื่อเหล่านี้ = ตอบแล้ว)
# แก้รายการด้านล่างได้เลย ไม่ต้องเก็บใน .env
OUR_CHAT_HEADER_NAMES = [
    "exa","exa","exa"
]

# หน้ารายละเอียดแชท: block แชทหนึ่งกลุ่ม และ chat-header > span (ชื่อผู้ส่ง)
CHAT_BLOCK_CSS = "div.chat.chat-text-dark.chat-reverse.chat-success"
# บล็อกแชททุกประเภท (เรา + ลูกค้า) เรียงตาม DOM = ตามเวลา ใช้หาข้อความตัวสุดท้าย
LAST_CHAT_BLOCK_CSS = "div.chat.chat-text-dark[class*='chat-reverse'], div.chat.chat-text-dark[class*='chat-secondary']"
CHAT_HEADER_SPAN_XPATH = ".//div[contains(@class, 'chat-header')]//span"

# รูปแบบเวลาวันนี้ (เช่น 17:27, 9:05); ถ้าไม่ตรง = แสดงเป็นข้อความเช่น เมื่อวาน
TIME_TODAY_PATTERN = re.compile(r"^\s*\d{1,2}\s*:\s*\d{2}\s*$")
# คำที่แสดงแทนเวลาเมื่อไม่ใช่วันนี้ (ข้าม)
NOT_TODAY_KEYWORDS = ("เมื่อวาน", "yesterday", "วานนี้", "days ago", "day ago", "ที่แล้ว", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")


def _get_our_chat_header_names():
    """คืนรายการชื่อ 'ของเรา' จาก OUR_CHAT_HEADER_NAMES"""
    return list(OUR_CHAT_HEADER_NAMES)


def _is_time_today(time_text):
    """เช็คว่า time_text เป็นรูปแบบเวลาวันนี้ (เช่น 17:27) ไม่ใช่เมื่อวาน/วันที่ผ่านมา"""
    if not (time_text or "").strip():
        return False
    t = (time_text or "").strip()
    if TIME_TODAY_PATTERN.search(t):
        return True
    lower = t.lower()
    for kw in NOT_TODAY_KEYWORDS:
        if kw in lower:
            return False
    return False


def is_unread_element(element):
    """เช็คว่าแถวแชทนี้ยังไม่อ่านหรือไม่ (LINE OA: ใช้เฉพาะ span.badge-pin เป็นหลัก)"""
    try:
        # LINE OA: ใช้เฉพาะ badge-pin เป็นตัวตัดสิน — ถ้าไม่มี badge = อ่านแล้ว (แม้แถวจะ selected อยู่)
        try:
            if element.find_elements(By.XPATH, UNREAD_BADGE_XPATH):
                return True
        except Exception:
            pass
        # fallback สำหรับ UI อื่น: class หรือ aria ที่บ่ง unread
        cls = (element.get_attribute("class") or "").lower()
        for pattern in UNREAD_CLASS_PATTERNS:
            if pattern in cls:
                return True
        aria = (element.get_attribute("aria-label") or "").lower()
        if "unread" in aria or "new" in aria:
            return True
    except Exception:
        pass
    return False


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


def get_unread_messages(driver, wait_seconds=DEFAULT_WAIT, debug=False):
    unread_messages_data = []
    try:
        wait = WebDriverWait(driver, wait_seconds)
        # รอให้มีอย่างน้อย container ของรายการแชทโหลด (ลองหลายแบบ)
        for conv_xpath, _name_xpath, _preview_xpath, _time_xpath in CONVERSATION_SELECTORS:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
                break
            except Exception:
                continue

        for conv_xpath, name_xpath, preview_xpath, time_xpath in CONVERSATION_SELECTORS:
            try:
                conversations = driver.find_elements(By.XPATH, conv_xpath)
            except Exception:
                conversations = []

            for conv in conversations:
                try:
                    if STRICT_UNREAD_ONLY and not is_unread_element(conv):
                        continue  # ข้ามแชทที่ไม่มีสัญญาณ unread
                    name_text = safe_find_text(conv, name_xpath)
                    message_text = safe_find_text(conv, preview_xpath)
                    time_text = safe_find_text(conv, time_xpath)
                    if name_text or message_text or time_text:
                        unread_messages_data.append({
                            "sender": name_text or "(ไม่มีชื่อ)",
                            "message": message_text or "(ไม่มีข้อความ)",
                            "time": time_text or "(ไม่มีเวลา)",
                        })
                        if debug:
                            print(f"[DEBUG] found: sender={name_text!r}, message={message_text!r}, time={time_text!r}")
                except Exception as e:
                    if debug:
                        print(f"[DEBUG] skip conv: {e}")
                    continue

            if unread_messages_data:
                break  # เจอแล้วไม่ต้องลอง selector ชุดอื่น

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลแชท: {e}")
    return unread_messages_data


def get_read_today_conversations(driver, wait_seconds=DEFAULT_WAIT, debug=False):
    """ดึงรายการแชทที่อ่านแล้วและของวันนี้ (เวลาแสดงเป็น HH:MM) พร้อม element สำหรับคลิกเข้า"""
    result = []
    try:
        wait = WebDriverWait(driver, wait_seconds)
        for conv_xpath, _name_xpath, _preview_xpath, _time_xpath in CONVERSATION_SELECTORS:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
                break
            except Exception:
                continue

        for conv_xpath, name_xpath, preview_xpath, time_xpath in CONVERSATION_SELECTORS:
            try:
                conversations = driver.find_elements(By.XPATH, conv_xpath)
            except Exception:
                conversations = []

            for conv in conversations:
                try:
                    if is_unread_element(conv):
                        continue  # ข้ามที่ยังไม่อ่าน (มี badge-pin)
                    time_text = safe_find_text(conv, time_xpath)
                    if not _is_time_today(time_text):
                        continue  # ข้ามที่ไม่ใช่วันนี้
                    name_text = safe_find_text(conv, name_xpath)
                    message_text = safe_find_text(conv, preview_xpath)
                    result.append({
                        "sender": name_text or "(ไม่มีชื่อ)",
                        "message": message_text or "(ไม่มีข้อความ)",
                        "time": time_text or "(ไม่มีเวลา)",
                        "element": conv,
                    })
                    if debug:
                        print(f"[DEBUG] read+today: sender={name_text!r}, time={time_text!r}")
                except Exception as e:
                    if debug:
                        print(f"[DEBUG] skip conv: {e}")
                    continue

            if result:
                break
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงรายการอ่านแล้ววันนี้: {e}")
    # เรียงให้แชทที่แสดง Yesterday อยู่ก่อน (สำหรับทดสอบ หรือตรวจจาก Yesterday ก่อน)
    result.sort(key=lambda r: (0 if "yesterday" in (r.get("time") or "").lower() else 1))
    return result


def debug_page_structure(driver, wait_seconds=DEFAULT_WAIT):
    """โหมด debug: พิมพ์โครงสร้าง/class ที่มีในหน้า เพื่อให้ไปใส่ selector ได้"""
    print("\n=== โหมด Debug: กำลังรอให้หน้าโหลด... ===")
    time.sleep(wait_seconds)
    print("\n--- ทุก element ที่มี class เกี่ยวกับ chat / list / message / unread ---")
    try:
        for xpath in [
            "//*[contains(@class, 'chat')]",
            "//*[contains(@class, 'list')]",
            "//*[contains(@class, 'message')]",
            "//*[contains(@class, 'unread')]",
            "//*[contains(@class, 'conversation')]",
            "//*[contains(@class, 'thread')]",
            "//*[contains(@class, 'sender')]",
            "//*[contains(@class, 'preview')]",
            "//*[contains(@class, 'time')]",
        ]:
            try:
                els = driver.find_elements(By.XPATH, xpath)
                for i, el in enumerate(els[:5]):  # แค่ 5 ตัวแรก
                    tag = el.tag_name
                    cls = el.get_attribute("class") or ""
                    text = (el.text or "")[:60]
                    print(f"  {xpath} -> tag={tag} class={cls!r} text={text!r}")
            except Exception as e:
                print(f"  {xpath} -> error: {e}")
    except Exception as e:
        print(f"Debug error: {e}")
    print("\n--- สิ้นสุด Debug (นำ class ที่เห็นไปใส่ใน CONVERSATION_SELECTORS ได้) ---\n")


def _is_port_in_use(port=9222):
    """Check if something is listening on this port (e.g. Chrome with remote debugging). Tries both IPv4 and IPv6 on Windows."""
    port = int(port)
    # Try IPv4 then IPv6 (Chrome on Windows may listen on either)
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
    """เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (ต้องเปิด Chrome ด้วย --remote-debugging-port=9222 ก่อน)"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def _switch_to_line_oa_tab(driver, url):
    """สลับไปแท็บที่มีหน้า LINE OA (chat.line.biz)"""
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "chat.line.biz" in (driver.current_url or ""):
            return True
    driver.get(url)
    return False


def send_via_openclaw(message, target="webchat", openclaw_cmd=None):
    """
    ส่งข้อความออกผ่าน openclaw (เรียก subprocess)
    target = ค่าให้ -t/--target เช่น webchat
    openclaw_cmd = path ของ openclaw (ถ้า None จะใช้ openclaw จาก PATH)
    """
    if not message or not message.strip():
        return False
    cmd = openclaw_cmd or "openclaw"
    if os.path.isfile(cmd):
        pass
    elif os.path.isfile("/opt/homebrew/bin/openclaw"):
        cmd = "/opt/homebrew/bin/openclaw"
    try:
        result = subprocess.run(
            [cmd, "message", "send", "-t", target, "--message", message.strip()],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 and result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"ส่ง openclaw ไม่สำเร็จ: {e}", file=sys.stderr)
        return False


def _open_conversation(driver, row_element):
    """คลิกแถวแชทเพื่อเข้าหน้ารายละเอียด แล้วรอให้โหลด"""
    try:
        row_element.click()
    except Exception:
        try:
            link = row_element.find_element(By.XPATH, ".//a")
            link.click()
        except Exception:
            raise
    wait = WebDriverWait(driver, DEFAULT_WAIT)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.chat-content, div.chat-body")))
    except Exception:
        pass
    time.sleep(0.5)


def _back_to_list(driver):
    """กลับจากหน้ารายละเอียดแชทไปหน้ารายการ"""
    conv_xpath = CONVERSATION_SELECTORS[0][0]
    try:
        back_btn = driver.find_elements(By.XPATH, "//button[contains(@class,'back')] | //a[contains(@class,'back')] | //*[@aria-label='back']")
        if back_btn:
            back_btn[0].click()
        else:
            driver.back()
    except Exception:
        driver.back()
    wait = WebDriverWait(driver, DEFAULT_WAIT)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
    except Exception:
        pass
    time.sleep(0.5)


def is_last_message_from_us(driver, our_names, wait_seconds=5):
    """
    ตรวจว่าข้อความล่าสุดในหน้านี้เป็นของเราหรือไม่
    - ใช้บล็อกตัวสุดท้ายจริง (chronological): ทั้ง chat-reverse และ chat-secondary
    - ไม่มี chat-header = แชท 1:1 ฝั่งลูกค้า → ไม่ใช่เรา
    - มี chat-header → เทียบกับ OUR_CHAT_HEADER_NAMES เท่านั้น (ตรง = เรา, ไม่ตรง = ลูกค้าแชทกลุ่ม)
    """
    if not our_names:
        return False
    try:
        wait = WebDriverWait(driver, wait_seconds)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, LAST_CHAT_BLOCK_CSS)))
    except Exception:
        return False
    try:
        blocks = driver.find_elements(By.CSS_SELECTOR, LAST_CHAT_BLOCK_CSS)
        if not blocks:
            return False
        last_block = blocks[-1]
        span_els = last_block.find_elements(By.XPATH, CHAT_HEADER_SPAN_XPATH)
        if not span_els:
            return False  # ไม่มี chat-header = แชท 1:1 ฝั่งลูกค้า
        header_text = (span_els[0].text or span_els[0].get_attribute("textContent") or "").strip()
        header_text = " ".join(header_text.split())
        for name in our_names:
            if not name:
                continue
            name_norm = " ".join(name.strip().split())
            if name_norm and (header_text == name_norm or name_norm in header_text):
                return True
        return False  # มี header แต่ไม่ตรงชื่อเรา = ลูกค้าแชทกลุ่ม
    except Exception:
        return False


def get_read_not_replied_today(driver, our_names=None, wait_seconds=DEFAULT_WAIT, debug=False, for_test=False):
    """
    หารายการที่อ่านแล้ว + วันนี้ + ยังไม่ได้ตอบ (ข้อความล่าสุดไม่ใช่ของเรา)
    กดเข้าแต่ละแชทที่อ่านแล้วของวันนี้ เพื่อเช็ค chat-header ตัวสุดท้าย
    ถ้า for_test=True จะเช็คเฉพาะแชทที่แสดงเวลา "Yesterday" (สำหรับทดสอบ)
    """
    if our_names is None:
        our_names = _get_our_chat_header_names()
    rows = get_read_today_conversations(driver, wait_seconds=wait_seconds, debug=debug)
    if for_test:
        rows = [r for r in rows if "yesterday" in (r.get("time") or "").lower()]
        if debug and rows:
            print(f"[DEBUG] for_test: ตรวจเฉพาะ Yesterday เหลือ {len(rows)} รายการ")
    read_not_replied = []
    for row in rows:
        # ถ้า preview แสดง "You sent a sticker." = เราส่งสติกเกอร์ไปแล้ว ถือว่าตอบแล้ว ข้าม (ไม่ต้องกดเข้าแชท)
        if "You sent a sticker." in (row.get("message") or ""):
            if debug:
                print(f"[DEBUG] ข้าม (เราส่งสติกเกอร์แล้ว): {row.get('sender')!r}")
            continue
        try:
            _open_conversation(driver, row["element"])
            from_us = is_last_message_from_us(driver, our_names, wait_seconds=wait_seconds)
            if not from_us:
                read_not_replied.append({
                    "sender": row["sender"],
                    "message": row["message"],
                    "time": row["time"],
                })
                if debug:
                    print(f"[DEBUG] read+today+not replied: {row['sender']!r}")
            _back_to_list(driver)
        except Exception as e:
            if debug:
                print(f"[DEBUG] skip row {row.get('sender')}: {e}")
            try:
                _back_to_list(driver)
            except Exception:
                pass
            continue
    return read_not_replied


def scrape_line_oa_unread_messages_continuous(url, check_interval_seconds=60, debug=False, max_hours=None, chrome_debug_port=None, report_format="full", send_openclaw_target=None, for_test=False):
    """
    รันตรวจสอบข้อความที่ยังไม่อ่านต่อเนื่อง
    ถ้าใส่ chrome_debug_port (หรือ CHROME_DEBUG_PORT ใน .env) = ใช้ Chrome ที่เปิดอยู่แล้ว ไม่ต้องเปิดใหม่
    for_test: ใช้กับ report_format read-not-replied-today เท่านั้น — เช็คเฉพาะแชทที่แสดง Yesterday
    """
    driver = None
    use_existing = chrome_debug_port is not None and str(chrome_debug_port).strip() != ""

    if use_existing:
        port = str(chrome_debug_port).strip()
        try:
            port_num = int(port)
        except ValueError:
            port_num = 9222
        if not _is_port_in_use(port_num):
            print(f"Port {port} is not in use (no Chrome with remote debugging found).")
            print("  -> Run start_chrome_for_script.bat first, then run this script again.")
            raise SystemExit(1)
        print(f"Port {port} is in use. Connecting to Chrome...")
        try:
            driver = _connect_to_existing_chrome(port)
        except Exception:
            print("Connection failed (not a Chrome instance started by the script?).")
            print("  -> Run start_chrome_for_script.bat, log in to LINE OA, then run this script again.")
            raise
        _switch_to_line_oa_tab(driver, url)
        print("Connected to Chrome (using your existing LINE OA session).")
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
        chrome_options.add_argument("--disable-background-networking")
        service = Service(ChromeDriverManager().install())
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except SessionNotCreatedException as e:
            if "crashed" in str(e).lower() or "DevToolsActivePort" in str(e):
                print("Chrome เปิดไม่สำเร็จ แนะนำให้ใช้โหมดเชื่อมต่อกับ Chrome ที่เปิดแล้ว (ดูใน .env ใส่ CHROME_DEBUG_PORT=9222)")
            raise
        driver.set_window_size(1280, 900)
        driver.get(url)
        try:
            has_chat_list = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'list-group-item-chat')]")) > 0
        except Exception:
            has_chat_list = False
        if not has_chat_list:
            if report_format in ("summary-once", "read-not-replied-today"):
                print("❌ ยังไม่ได้เข้าสู่ระบบ LINE OA และคุณกำลังรันในโหมดอัตโนมัติ (Cron Job) กรุณาเข้าสู่ระบบในเบราว์เซอร์ด้วยตนเองก่อน")
                return  # จบการทำงานทันที ไม่รอ input เพื่อไม่ให้ cron job ค้าง
            print("โปรดล็อกอินเข้าสู่ระบบ LINE OA ในเบราว์เซอร์ที่เปิดขึ้นมา")
            try:
                input("เมื่อล็อกอินเสร็จแล้วและเห็นหน้าแชทแล้ว โปรดกด Enter เพื่อดำเนินการต่อ...")
            except EOFError:
                print("⚠️ พบข้อผิดพลาดในการรับค่า Input (คาดว่ารันในเบื้องหลัง) กรุณาตรวจสอบการล็อกอิน")
                return
        else:
            print("✅ เข้าสู่ระบบเรียบร้อยแล้ว")

    start_time = time.time()
    try:

        if debug:
            debug_page_structure(driver, wait_seconds=5)
        
        # ถ้ารันแบบ One-shot เพื่อรายงานสรุป (สำหรับ cron job)
        if report_format == "summary-once":
            current_unread_messages = get_unread_messages(driver, wait_seconds=5, debug=debug)
            lines = []
            if current_unread_messages:
                lines.append(f"📥 รายงานข้อความที่ยังไม่ได้อ่าน [รวม {len(current_unread_messages)} รายการ]")
                for msg in current_unread_messages:
                    lines.append(f"ชื่อ: **{msg['sender']}** เวลา: **{msg['time']} น.**")
            else:
                lines.append("ไม่พบข้อความที่ยังไม่ได้อ่าน")
            report_text = "\n".join(lines)
            print(report_text)
            if send_openclaw_target:
                if send_via_openclaw(report_text, target=send_openclaw_target):
                    print("(ส่งผลไป openclaw แล้ว)", file=sys.stderr)
                else:
                    print("(ส่ง openclaw ไม่สำเร็จ)", file=sys.stderr)
            return  # จบการทำงานหลังจากรายงาน

        # รายงานอ่านแล้วแต่ยังไม่ตอบของวันนี้ (one-shot)
        if report_format == "read-not-replied-today":
            if for_test:
                print("[For test] ตรวจเฉพาะแชทที่แสดง Yesterday", file=sys.stderr)
            read_not_replied = get_read_not_replied_today(driver, wait_seconds=5, debug=debug, for_test=for_test)
            lines = []
            if read_not_replied:
                prefix = "📋 อ่านแล้วแต่ยังไม่ตอบ (Yesterday เท่านั้น)" if for_test else "📋 อ่านแล้วแต่ยังไม่ตอบของวันนี้"
                lines.append(f"{prefix} [รวม {len(read_not_replied)} รายการ]")
                for msg in read_not_replied:
                    lines.append(f"ชื่อ: **{msg['sender']}** ข้อความ: **{msg['message']}** เวลา: **{msg['time']}**")
                lines.append("")
                lines.append(f"--- สรุป: อ่านแล้วแต่ยังไม่ตอบ {len(read_not_replied)} รายการ ---")
            else:
                lines.append("ไม่พบรายการที่อ่านแล้วและยังไม่ตอบของวันนี้" if not for_test else "ไม่พบแชทที่แสดง Yesterday ที่อ่านแล้วแต่ยังไม่ตอบ")
                lines.append("")
                lines.append("--- สรุป: อ่านแล้วแต่ยังไม่ตอบ 0 รายการ ---")
            report_text = "\n".join(lines)
            print(report_text)
            if send_openclaw_target:
                if send_via_openclaw(report_text, target=send_openclaw_target):
                    print("(ส่งผลไป openclaw แล้ว)", file=sys.stderr)
                else:
                    print("(ส่ง openclaw ไม่สำเร็จ)", file=sys.stderr)
            return

        # โหมดรันต่อเนื่อง (สำหรับรันด้วยตนเอง)
        print(f"เริ่มตรวจสอบข้อความที่ยังไม่อ่านทุกๆ {check_interval_seconds} วินาที...")
        if max_hours:
            print(f"จะหยุดหลังรันครบ {max_hours} ชั่วโมง (แนะนำให้ใช้ scheduler รันใหม่)")
        print("(จะแสดงรายการที่ยังไม่อ่านทุกครั้ง จนกว่าจะเปิดอ่านแล้ว badge จึงหาย)\n")
        if max_hours:
            print(f"จะหยุดหลังรันครบ {max_hours} ชั่วโมง (แนะนำให้ใช้ scheduler รันใหม่)")
        print("(จะแสดงรายการที่ยังไม่อ่านทุกครั้ง จนกว่าจะเปิดอ่านแล้ว badge จึงหาย)\n")
        while True:
            if max_hours and (time.time() - start_time) >= max_hours * 3600:
                print(f"\nครบ {max_hours} ชั่วโมง แล้ว หยุดทำงาน (ให้ scheduler รันสคริปต์ใหม่)")
                break
            try:
                current_unread_messages = get_unread_messages(driver, wait_seconds=5, debug=debug)
                if current_unread_messages:
                    print("\n--- ข้อความที่ยังไม่อ่าน (ปัจจุบัน) ---")
                    for msg in current_unread_messages:
                        # ใช้รูปแบบที่คุณกำหนดสำหรับ "list" และ "all"
                        print(f"ชื่อ: **{msg['sender']}**")
                        print(f"ข้อความ: **{msg['message']}**")
                        print(f"เวลา: **{msg['time']} น.**")
                        print() # เว้นบรรทัด
                    print(f"รวม {len(current_unread_messages)} รายการ\n")
                else:
                    print("ไม่พบข้อความที่ยังไม่อ่าน")
            except Exception as e:
                print(f"รอบนี้ดึงข้อมูลไม่สำเร็จ (ข้ามไป): {e}")
            print(f"รอ {check_interval_seconds} วินาที ก่อนตรวจสอบอีกครั้ง...")
            time.sleep(check_interval_seconds)

    except KeyboardInterrupt:
        print("\nหยุดการทำงานด้วยตนเอง")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    default_url = os.environ.get("LINE_OA_URL")
    try:
        default_interval = int(os.environ.get("LINE_OA_INTERVAL", "30"))
    except ValueError:
        default_interval = 30
    chrome_port = os.environ.get("CHROME_DEBUG_PORT", "").strip()
    parser = argparse.ArgumentParser(description="LINE OA - ตรวจสอบข้อความที่ยังไม่อ่าน")
    parser.add_argument("--url", default=default_url, help="URL หน้าแชท LINE OA")
    parser.add_argument("--interval", type=int, default=default_interval, help="ระยะห่างตรวจสอบ วินาที")
    parser.add_argument("--debug", action="store_true", help="โหมด debug")
    parser.add_argument("--max-hours", type=float, default=None, help="หยุดหลังรันครบ N ชม.")
    parser.add_argument("--connect-chrome", type=str, default=chrome_port or None, metavar="PORT", help="เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (port 9222 ถ้าใช้ start_chrome_for_script.bat)")
    parser.add_argument("--report-format", type=str, choices=["full", "summary-once", "read-not-replied-today"], default="full",
                        help="รูปแบบการรายงาน: full (ข้อความเต็ม), summary-once (ชื่อและเวลา, รันครั้งเดียว), read-not-replied-today (อ่านแล้วยังไม่ตอบของวันนี้)")
    parser.add_argument("--send-openclaw-target", type=str, default=None, metavar="TARGET",
                        help="ส่งผลรายงานไป openclaw -t TARGET (ใช้คู่กับ summary-once หรือ read-not-replied-today)")
    parser.add_argument("--for-test", action="store_true", dest="for_test",
                        help="โหมดทดสอบ: ใช้กับ read-not-replied-today — เช็คเฉพาะแชทที่แสดง Yesterday")
    args = parser.parse_args()

    scrape_line_oa_unread_messages_continuous(
        args.url,
        check_interval_seconds=args.interval,
        debug=args.debug,
        max_hours=args.max_hours,
        chrome_debug_port=args.connect_chrome,
        report_format=args.report_format,
        send_openclaw_target=args.send_openclaw_target,
        for_test=args.for_test,
    )
