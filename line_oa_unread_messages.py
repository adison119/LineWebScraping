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
import shutil
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
    ". 𝒩𝒶𝓃’𝓃","merl","Bell","พอย","Ka Reem"
]

# หน้ารายละเอียดแชท: block แชทหนึ่งกลุ่ม และ chat-header > span (ชื่อผู้ส่ง)
CHAT_BLOCK_CSS = "div.chat.chat-text-dark.chat-reverse.chat-success"
# บล็อกแชททุกประเภท (เรา + ลูกค้า) เรียงตาม DOM = ตามเวลา ใช้หาข้อความตัวสุดท้าย
# chat-reverse = ฟองเรา, chat-secondary = ฟองลูกค้า (ใช้เมื่อไม่มี chat-header)
LAST_CHAT_BLOCK_CSS = "div.chat.chat-text-dark[class*='chat-reverse'], div.chat.chat-text-dark[class*='chat-secondary']"
CHAT_HEADER_SPAN_XPATH = ".//div[contains(@class, 'chat-header')]//span"
# บล็อกข้อความล่าสุด: -1 = ข้อความล่างสุด (DOM เก่าบน-ใหม่ล่าง), 0 = ข้อความบนสุด (DOM ใหม่บน)
LAST_MESSAGE_BLOCK_INDEX = -1

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


def _is_time_yesterday(time_text):
    """เช็คว่า time_text แสดงเมื่อวาน (Yesterday / เมื่อวาน)"""
    if not (time_text or "").strip():
        return False
    lower = (time_text or "").strip().lower()
    return "yesterday" in lower or "เมื่อวาน" in lower or "วานนี้" in lower


# ชื่อวันตามสัปดาห์ (อังกฤษ/ไทย) = เก่ากว่าเมื่อวาน → ใช้เป็นจุดหยุดดึงรายการ
WEEKDAY_NAMES = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "จันทร์", "อังคาร", "พุธ", "พฤหัส", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์",
)


def _is_time_weekday_or_older(time_text):
    """เช็คว่า time_text เป็นชื่อวัน (Monday / จันทร์ ฯลฯ) = เก่ากว่าเมื่อวาน → ให้หยุดดึงรายการ"""
    if not (time_text or "").strip():
        return False
    lower = (time_text or "").strip().lower()
    return any(day in lower for day in WEEKDAY_NAMES)


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


def _scroll_chat_list_until_weekday(driver, step_px=400, max_scrolls=80, pause=0.3):
    """
    เลื่อนรายการแชทลงทีละน้อย จนกว่าจะเจอแชทที่เวลาเป็นวันตามสัปดาห์ (Monday / จันทร์ ฯลฯ)
    แล้วหยุด = มีแชทวันนี้+เมื่อวานครบแล้ว ไม่เลื่อนเกินจำเป็น
    """
    conv_xpath = CONVERSATION_SELECTORS[0][0]
    time_xpath = CONVERSATION_SELECTORS[0][3]
    try:
        els = driver.find_elements(By.XPATH, conv_xpath)
        if not els:
            return
        container = None
        try:
            first = els[0]
            for xpath in [
                "./ancestor::div[contains(@class,'list-group')][1]",
                "./ancestor::div[contains(@class,'overflow')][1]",
                "./ancestor::div[contains(@class,'scroll')][1]",
                "./ancestor::div[contains(@class,'sidebar') or contains(@class,'chat-list')][1]",
                "./..",
            ]:
                try:
                    parent = first.find_element(By.XPATH, xpath)
                    if parent:
                        sh = driver.execute_script("return arguments[0].scrollHeight;", parent)
                        ch = driver.execute_script("return arguments[0].clientHeight;", parent)
                        if sh > ch + 10:
                            container = parent
                            break
                except Exception:
                    continue
        except Exception:
            pass
        if not container:
            try:
                container = driver.find_element(By.TAG_NAME, "body")
            except Exception:
                return
        last_top = -1
        for scroll_i in range(max_scrolls):
            try:
                # เช็คว่ามีแถวที่เวลาเป็นวัน (Monday ฯลฯ) แล้วหรือยัง → เจอแล้วหยุด scroll
                conversations = driver.find_elements(By.XPATH, conv_xpath)
                for conv in conversations:
                    t = safe_find_text(conv, time_xpath)
                    if _is_time_weekday_or_older(t):
                        return
                driver.execute_script("arguments[0].scrollTop += arguments[1];", container, step_px)
                time.sleep(pause)
                top = driver.execute_script("return arguments[0].scrollTop;", container)
                height = driver.execute_script("return arguments[0].clientHeight;", container)
                total = driver.execute_script("return arguments[0].scrollHeight;", container)
                at_bottom = top + height >= total - 2
                no_progress = top == last_top
                if at_bottom:
                    # อาจเป็นแค่กำลังโหลดข้อความเพิ่ม — รอแล้วเช็ค scrollHeight อีกครั้ง
                    for wait_attempt in range(3):
                        time.sleep(0.8)
                        total2 = driver.execute_script("return arguments[0].scrollHeight;", container)
                        if total2 > total:
                            total = total2
                            at_bottom = False
                            break
                    if at_bottom:
                        break
                if no_progress:
                    break
                last_top = top
            except Exception:
                break
    except Exception:
        pass


def get_read_today_and_yesterday_conversations(driver, wait_seconds=DEFAULT_WAIT, debug=False):
    """ดึงรายการแชทที่อ่านแล้วของวันนี้ + เมื่อวาน แยกเป็น (today_list, yesterday_list)"""
    today_list = []
    yesterday_list = []
    try:
        wait = WebDriverWait(driver, wait_seconds)
        for conv_xpath, _name_xpath, _preview_xpath, _time_xpath in CONVERSATION_SELECTORS:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
                break
            except Exception:
                continue

        # เลื่อนรายการแชทจนเจอแชทที่เวลาเป็นวัน (Monday ฯลฯ) แล้วหยุด = ได้แค่วันนี้+เมื่อวาน
        _scroll_chat_list_until_weekday(driver)

        for conv_xpath, name_xpath, preview_xpath, time_xpath in CONVERSATION_SELECTORS:
            try:
                conversations = driver.find_elements(By.XPATH, conv_xpath)
            except Exception:
                conversations = []

            for conv in conversations:
                try:
                    if is_unread_element(conv):
                        continue
                    time_text = safe_find_text(conv, time_xpath)
                    # เจอแชทที่เวลาเป็นวันตามสัปดาห์ (Monday / จันทร์ ฯลฯ) = เก่ากว่าเมื่อวาน → หยุดไม่ดึงต่อ
                    if _is_time_weekday_or_older(time_text):
                        if debug:
                            print(f"[DEBUG] หยุดดึงรายการ: เจอวันเก่ากว่าเมื่อวาน time={time_text!r}")
                        break
                    if _is_time_today(time_text):
                        name_text = safe_find_text(conv, name_xpath)
                        message_text = safe_find_text(conv, preview_xpath)
                        today_list.append({
                            "sender": name_text or "(ไม่มีชื่อ)",
                            "message": message_text or "(ไม่มีข้อความ)",
                            "time": time_text or "(ไม่มีเวลา)",
                            "element": conv,
                        })
                        if debug:
                            print(f"[DEBUG] read+today: sender={name_text!r}, time={time_text!r}")
                    elif _is_time_yesterday(time_text):
                        name_text = safe_find_text(conv, name_xpath)
                        message_text = safe_find_text(conv, preview_xpath)
                        yesterday_list.append({
                            "sender": name_text or "(ไม่มีชื่อ)",
                            "message": message_text or "(ไม่มีข้อความ)",
                            "time": time_text or "(ไม่มีเวลา)",
                            "element": conv,
                        })
                        if debug:
                            print(f"[DEBUG] read+yesterday: sender={name_text!r}, time={time_text!r}")
                except Exception as e:
                    if debug:
                        print(f"[DEBUG] skip conv: {e}")
                    continue

            if today_list or yesterday_list:
                break
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงรายการอ่านแล้ววันนี้/เมื่อวาน: {e}")
    return (today_list, yesterday_list)


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


def _room_label_from_url(url, index=0):
    """สร้างชื่อห้องจาก URL สำหรับแสดงในรายงาน (ใช้ path สุดท้าย หรือ Room 1, 2)"""
    if not url or not url.strip():
        return f"Room {index + 1}"
    u = url.strip().rstrip("/")
    if "/" in u:
        part = u.split("/")[-1]
        if part and len(part) > 2:
            return part[:32]  # จำกัดความยาว
    return f"Room {index + 1}"


def _switch_to_line_oa_tab(driver, url):
    """สลับไปแท็บที่มีหน้า LINE OA (chat.line.biz) ถ้าไม่มีจะเปิด url ในแท็บปัจจุบัน"""
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        cur = (driver.current_url or "").strip()
        if "chat.line.biz" in cur and (not url or url.strip() in cur or cur.strip() == url.strip()):
            return True
    driver.get(url)
    return False


def _ensure_tab_for_url(driver, url):
    """
    สลับไปแท็บที่เปิด url นี้อยู่แล้ว ถ้าไม่มีให้เปิดแท็บใหม่แล้วไปที่ url
    คืน True ถ้าสลับ/เปิดสำเร็จ
    """
    url = (url or "").strip()
    if not url:
        return False
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        cur = (driver.current_url or "").strip()
        if cur == url or (url in cur and "chat.line.biz" in cur):
            return True
    # เปิดแท็บใหม่
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url)
    return True


def _find_openclaw_cmd(openclaw_cmd=None):
    """หา path ของ openclaw ให้ทำงานเมื่อรันจาก cron (PATH อาจไม่รวม openclaw)"""
    if openclaw_cmd and os.path.isfile(openclaw_cmd):
        return openclaw_cmd
    for path in ("/opt/homebrew/bin/openclaw", "/usr/local/bin/openclaw"):
        if os.path.isfile(path):
            return path
    # รันจาก cron มักมี PATH สั้น — เพิ่ม path ที่มักมี openclaw
    extra_paths = os.pathsep.join([
        os.environ.get("PATH", ""),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ])
    env_path = os.environ.copy()
    env_path["PATH"] = extra_paths
    found = shutil.which("openclaw", path=extra_paths)
    if found:
        return found
    return "openclaw"


def send_via_openclaw(message, target="webchat", openclaw_cmd=None):
    """
    ส่งข้อความออกผ่าน openclaw (เรียก subprocess)
    target = ค่าให้ -t/--target เช่น webchat (ส่งไปไลน์ต้องให้ OpenClaw Gateway รันอยู่และตั้งค่า channel ไว้)
    openclaw_cmd = path ของ openclaw (ถ้า None จะหาจาก PATH / homebrew)
    """
    if not message or not message.strip():
        return False
    cmd = _find_openclaw_cmd(openclaw_cmd)
    # ให้ subprocess มี PATH เพียงพอ (เมื่อรันจาก cron)
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
            if result.stdout:
                print(result.stdout.strip(), file=sys.stderr)
            print(f"[openclaw] returncode={result.returncode} target={target!r}", file=sys.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print(f"ไม่พบคำสั่ง openclaw (ลองติดตั้งหรือใส่ path ใน OPENCLAW_CMD) — ส่งผลไปไลน์ไม่สำเร็จ", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ส่ง openclaw ไม่สำเร็จ: {e}", file=sys.stderr)
        return False


def _send_report_to_openclaw_targets(message, send_openclaw_target):
    """
    ส่งรายงานไปทุก target ที่กำหนด (รองรับหลายบัญชี)
    send_openclaw_target = string คั่นด้วย comma เช่น "webchat,line_group_2" หรือ target เดียว "webchat"
    """
    if not message or not send_openclaw_target:
        return
    targets = [t.strip() for t in str(send_openclaw_target).split(",") if t.strip()]
    if not targets:
        return
    ok = 0
    for t in targets:
        if send_via_openclaw(message, target=t):
            ok += 1
    if ok == len(targets):
        print("(ส่งผลไป openclaw ทุก target แล้ว)", file=sys.stderr)
    else:
        print(f"(ส่ง openclaw สำเร็จ {ok}/{len(targets)} target)", file=sys.stderr)


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
    - ใช้บล็อกตัวสุดท้ายตาม LAST_MESSAGE_BLOCK_INDEX (chronological)
    - มี chat-header → เทียบกับ OUR_CHAT_HEADER_NAMES (ตรง = เรา)
    - ไม่มี chat-header → ดู class: chat-reverse = เรา, chat-secondary = ลูกค้า (ไม่ถือว่าตอบแล้ว)
    """
    try:
        wait = WebDriverWait(driver, wait_seconds)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, LAST_CHAT_BLOCK_CSS)))
    except Exception:
        return False
    try:
        blocks = driver.find_elements(By.CSS_SELECTOR, LAST_CHAT_BLOCK_CSS)
        if not blocks:
            return False
        last_block = blocks[LAST_MESSAGE_BLOCK_INDEX]
        span_els = last_block.find_elements(By.XPATH, CHAT_HEADER_SPAN_XPATH)
        if span_els:
            header_text = (span_els[0].text or span_els[0].get_attribute("textContent") or "").strip()
            header_text = " ".join(header_text.split())
            if our_names:
                for name in our_names:
                    if not name:
                        continue
                    name_norm = " ".join(name.strip().split())
                    if name_norm and (header_text == name_norm or name_norm in header_text):
                        return True
            return False  # มี header แต่ไม่ตรงชื่อเรา = ลูกค้าแชทกลุ่ม
        # ไม่มี chat-header: ดู class — ฟองเรา = chat-reverse, ฟองลูกค้า = chat-secondary
        block_class = (last_block.get_attribute("class") or "").lower()
        if "chat-reverse" in block_class:
            return True
        return False
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
        preview = (row.get("message") or "").strip()
        # ถ้า preview บ่งชี้ว่าเราส่งข้อความ/สติกเกอร์/รูปไปแล้ว = ถือว่าตอบแล้ว ข้าม (ไม่ต้องกดเข้าแชท)
        if preview.startswith("You sent ") or "You sent a sticker." in preview:
            if debug:
                print(f"[DEBUG] ข้าม (เราส่งไปแล้ว): {row.get('sender')!r} preview={preview[:50]!r}")
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


def _process_read_not_replied_rows(driver, rows, our_names, wait_seconds=DEFAULT_WAIT, debug=False):
    """
    วนแต่ละ row เปิดแชท → เช็ค is_last_message_from_us → ถ้าไม่ใช่ของเรา append เข้า result → กลับรายการ
    ข้ามแถวที่ preview เป็น "You sent ..." / "You sent a sticker." เพื่อลดขั้นตอน (ไม่ต้องเปิดเข้าแชท)
    """
    if our_names is None:
        our_names = _get_our_chat_header_names()
    result = []
    for row in rows:
        preview = (row.get("message") or "").strip()
        if preview.startswith("You sent ") or "You sent a sticker." in preview:
            if debug:
                print(f"[DEBUG] ข้าม (เราส่งไปแล้ว): {row.get('sender')!r} preview={preview[:50]!r}")
            continue
        try:
            _open_conversation(driver, row["element"])
            from_us = is_last_message_from_us(driver, our_names, wait_seconds=wait_seconds)
            if not from_us:
                result.append({
                    "sender": row["sender"],
                    "message": row["message"],
                    "time": row["time"],
                })
                if debug:
                    print(f"[DEBUG] read+not replied: {row['sender']!r}")
            _back_to_list(driver)
        except Exception as e:
            if debug:
                print(f"[DEBUG] skip row {row.get('sender')}: {e}")
            try:
                _back_to_list(driver)
            except Exception:
                pass
            continue
    return result


def get_read_not_replied_today_and_yesterday(driver, our_names=None, wait_seconds=DEFAULT_WAIT, debug=False):
    """
    ดึงรายการอ่านแล้วแต่ยังไม่ตอบ แยกวันนี้และเมื่อวาน
    return (read_not_replied_today, read_not_replied_yesterday)
    """
    today_rows, yesterday_rows = get_read_today_and_yesterday_conversations(driver, wait_seconds=wait_seconds, debug=debug)
    read_not_replied_today = _process_read_not_replied_rows(driver, today_rows, our_names, wait_seconds=wait_seconds, debug=debug)
    read_not_replied_yesterday = _process_read_not_replied_rows(driver, yesterday_rows, our_names, wait_seconds=wait_seconds, debug=debug)
    return (read_not_replied_today, read_not_replied_yesterday)


def _parse_urls(url):
    """รับ url เป็น string (เดียวหรือคั่นด้วย comma) หรือ list คืนเป็น list ของ URL"""
    if isinstance(url, (list, tuple)):
        return [u.strip() for u in url if (u and str(u).strip())]
    s = str(url).strip()
    if not s:
        return []
    return [u.strip() for u in s.split(",") if u.strip()]


def scrape_line_oa_unread_messages_continuous(url, check_interval_seconds=60, debug=False, max_hours=None, chrome_debug_port=None, report_format="full", send_openclaw_target=None, for_test=False):
    """
    รันตรวจสอบข้อความที่ยังไม่อ่านต่อเนื่อง
    url รับได้เป็น URL เดียว หรือหลาย URL คั่นด้วย comma (หลายห้องแชท)
    ถ้าใส่ chrome_debug_port (หรือ CHROME_DEBUG_PORT ใน .env) = ใช้ Chrome ที่เปิดอยู่แล้ว ไม่ต้องเปิดใหม่
    for_test: ใช้กับ report_format read-not-replied-today เท่านั้น — เช็คเฉพาะแชทที่แสดง Yesterday
    """
    urls = _parse_urls(url)
    if not urls:
        print("ไม่พบ URL กรุณาระบุ --url หรือ LINE_OA_URL (หลายห้องคั่นด้วย comma ได้)", file=sys.stderr)
        raise SystemExit(1)
    # ใช้ URL แรกสำหรับการเชื่อมต่อ/เปิดหน้าแรก
    first_url = urls[0]
    driver = None
    use_existing = chrome_debug_port is not None and str(chrome_debug_port).strip() != ""

    if use_existing:
        port = str(chrome_debug_port).strip()
        try:
            port_num = int(port)
        except ValueError:
            port_num = 9222
        if not _is_port_in_use(port_num):
            print(f"Port {port} is not in use (no Chrome with remote debugging found).", file=sys.stderr)
            print("  -> Run start_chrome_for_script.bat first, then run this script again.", file=sys.stderr)
            raise SystemExit(1)
        print(f"Port {port} is in use. Connecting to Chrome...", file=sys.stderr)
        try:
            driver = _connect_to_existing_chrome(port)
        except Exception:
            print("Connection failed (not a Chrome instance started by the script?).", file=sys.stderr)
            print("  -> Run start_chrome_for_script.bat, log in to LINE OA, then run this script again.", file=sys.stderr)
            raise
        if len(urls) == 1:
            _switch_to_line_oa_tab(driver, first_url)
        else:
            _ensure_tab_for_url(driver, first_url)
        print("Connected to Chrome (using your existing LINE OA session).", file=sys.stderr)
        if len(urls) > 1:
            print(f"รองรับ {len(urls)} ห้องแชท", file=sys.stderr)
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
        driver.get(first_url)
        try:
            has_chat_list = len(driver.find_elements(By.XPATH, "//div[contains(@class, 'list-group-item-chat')]")) > 0
        except Exception:
            has_chat_list = False
        if not has_chat_list:
            if report_format in ("summary-once", "read-not-replied-today"):
                print("❌ ยังไม่ได้เข้าสู่ระบบ LINE OA และคุณกำลังรันในโหมดอัตโนมัติ (Cron Job) กรุณาเข้าสู่ระบบในเบราว์เซอร์ด้วยตนเองก่อน", file=sys.stderr)
                return  # จบการทำงานทันที ไม่รอ input เพื่อไม่ให้ cron job ค้าง
            print("โปรดล็อกอินเข้าสู่ระบบ LINE OA ในเบราว์เซอร์ที่เปิดขึ้นมา", file=sys.stderr)
            try:
                input("เมื่อล็อกอินเสร็จแล้วและเห็นหน้าแชทแล้ว โปรดกด Enter เพื่อดำเนินการต่อ...")
            except EOFError:
                print("⚠️ พบข้อผิดพลาดในการรับค่า Input (คาดว่ารันในเบื้องหลัง) กรุณาตรวจสอบการล็อกอิน", file=sys.stderr)
                return
        else:
            print("✅ เข้าสู่ระบบเรียบร้อยแล้ว", file=sys.stderr)

    start_time = time.time()
    try:

        if debug:
            debug_page_structure(driver, wait_seconds=5)
        
        # ถ้ารันแบบ One-shot เพื่อรายงานสรุป (สำหรับ cron job) — แยกวันนี้/เมื่อวาน (ไม่เอาเก่ากว่าเมื่อวาน)
        if report_format == "summary-once":
            lines = []
            grand_total = 0
            for i, one_url in enumerate(urls):
                if len(urls) > 1:
                    if use_existing:
                        _ensure_tab_for_url(driver, one_url)
                    else:
                        driver.get(one_url)
                    time.sleep(0.8)
                room = _room_label_from_url(one_url, i)
                current_unread_messages = get_unread_messages(driver, wait_seconds=5, debug=debug)
                unread_today = [m for m in current_unread_messages if _is_time_today(m.get("time") or "")]
                unread_yesterday = [m for m in current_unread_messages if _is_time_yesterday(m.get("time") or "")]
                total_today_yesterday = len(unread_today) + len(unread_yesterday)
                grand_total += total_today_yesterday
                if len(urls) > 1:
                    lines.append(f"【{room}】")
                if total_today_yesterday:
                    if unread_today:
                        lines.append(f"📥 ยังไม่อ่าน วันนี้ [รวม {len(unread_today)} รายการ]")
                        for msg in unread_today:
                            lines.append(f"ชื่อ: **{msg['sender']}** เวลา: **{msg['time']} น.**")
                        lines.append("")
                    if unread_yesterday:
                        lines.append(f"📥 ยังไม่อ่าน เมื่อวาน [รวม {len(unread_yesterday)} รายการ]")
                        for msg in unread_yesterday:
                            lines.append(f"ชื่อ: **{msg['sender']}** เวลา: **{msg['time']}**")
                        lines.append("")
                    if len(urls) > 1:
                        lines.append(f"--- {room}: ยังไม่อ่านรวม {total_today_yesterday} รายการ ---")
                        lines.append("")
                elif len(urls) == 1:
                    lines.append("ไม่พบข้อความที่ยังไม่ได้อ่าน")
            if len(urls) > 1:
                lines.append(f"--- สรุปทุกห้อง: ยังไม่อ่านรวม {grand_total} รายการ (วันนี้+เมื่อวาน) ---")
            elif grand_total == 0 and urls:
                lines.append("ไม่พบข้อความที่ยังไม่ได้อ่าน")
            report_text = "\n".join(lines)
            print(report_text)
            if send_openclaw_target:
                _send_report_to_openclaw_targets(report_text, send_openclaw_target)
            return  # จบการทำงานหลังจากรายงาน

        # รายงานอ่านแล้วแต่ยังไม่ตอบของวันนี้ (one-shot)
        if report_format == "read-not-replied-today":
            if for_test:
                print("[For test] ตรวจเฉพาะแชทที่แสดง Yesterday", file=sys.stderr)
            lines = []
            grand_total = 0
            for i, one_url in enumerate(urls):
                if len(urls) > 1:
                    if use_existing:
                        _ensure_tab_for_url(driver, one_url)
                    else:
                        driver.get(one_url)
                    time.sleep(0.8)
                room = _room_label_from_url(one_url, i)
                read_not_replied_today, read_not_replied_yesterday = get_read_not_replied_today_and_yesterday(driver, wait_seconds=5, debug=debug)
                if for_test:
                    read_not_replied_today = []
                total = len(read_not_replied_today) + len(read_not_replied_yesterday)
                grand_total += total
                if len(urls) > 1:
                    lines.append(f"【{room}】")
                if read_not_replied_today:
                    lines.append(f"📋 อ่านแล้วแต่ยังไม่ตอบ วันนี้ [รวม {len(read_not_replied_today)} รายการ]")
                    for msg in read_not_replied_today:
                        lines.append(f"ชื่อ: **{msg['sender']}** ข้อความ: **{msg['message']}** เวลา: **{msg['time']}**")
                    lines.append("")
                if read_not_replied_yesterday:
                    lines.append(f"📋 อ่านแล้วแต่ยังไม่ตอบ เมื่อวาน [รวม {len(read_not_replied_yesterday)} รายการ]")
                    for msg in read_not_replied_yesterday:
                        lines.append(f"ชื่อ: **{msg['sender']}** ข้อความ: **{msg['message']}** เวลา: **{msg['time']}**")
                    lines.append("")
                if total and len(urls) > 1:
                    lines.append(f"--- {room}: อ่านแล้วแต่ยังไม่ตอบ รวม {total} รายการ ---")
                    lines.append("")
                elif not total and len(urls) == 1:
                    lines.append("ไม่พบรายการที่อ่านแล้วและยังไม่ตอบ (วันนี้และเมื่อวาน)")
                    lines.append("")
                    lines.append("--- สรุป: อ่านแล้วแต่ยังไม่ตอบ 0 รายการ ---")
            if len(urls) > 1:
                lines.append(f"--- สรุปทุกห้อง: อ่านแล้วแต่ยังไม่ตอบ รวม {grand_total} รายการ ---")
            elif len(urls) == 1 and grand_total == 0 and not lines:
                lines.append("ไม่พบรายการที่อ่านแล้วและยังไม่ตอบ (วันนี้และเมื่อวาน)")
                lines.append("")
                lines.append("--- สรุป: อ่านแล้วแต่ยังไม่ตอบ 0 รายการ ---")
            report_text = "\n".join(lines)
            print(report_text)
            if send_openclaw_target:
                _send_report_to_openclaw_targets(report_text, send_openclaw_target)
            return

        # โหมดรันต่อเนื่อง (สำหรับรันด้วยตนเอง)
        print(f"เริ่มตรวจสอบข้อความที่ยังไม่อ่านทุกๆ {check_interval_seconds} วินาที...")
        if len(urls) > 1:
            print(f"จำนวนห้องแชท: {len(urls)}")
        if max_hours:
            print(f"จะหยุดหลังรันครบ {max_hours} ชั่วโมง (แนะนำให้ใช้ scheduler รันใหม่)")
        print("(จะแสดงรายการที่ยังไม่อ่านทุกครั้ง จนกว่าจะเปิดอ่านแล้ว badge จึงหาย)\n")
        while True:
            if max_hours and (time.time() - start_time) >= max_hours * 3600:
                print(f"\nครบ {max_hours} ชั่วโมง แล้ว หยุดทำงาน (ให้ scheduler รันสคริปต์ใหม่)")
                break
            try:
                for i, one_url in enumerate(urls):
                    if len(urls) > 1:
                        if use_existing:
                            _ensure_tab_for_url(driver, one_url)
                        else:
                            driver.get(one_url)
                        time.sleep(0.5)
                    room = _room_label_from_url(one_url, i)
                    current_unread_messages = get_unread_messages(driver, wait_seconds=5, debug=debug)
                    if current_unread_messages:
                        print(f"\n--- 【{room}】 ข้อความที่ยังไม่อ่าน (ปัจจุบัน) ---")
                        for msg in current_unread_messages:
                            print(f"ชื่อ: **{msg['sender']}**")
                            print(f"ข้อความ: **{msg['message']}**")
                            print(f"เวลา: **{msg['time']} น.**")
                            print()
                        print(f"รวม {len(current_unread_messages)} รายการ\n")
                    elif len(urls) == 1:
                        print("ไม่พบข้อความที่ยังไม่อ่าน")
                if len(urls) > 1:
                    print("--- จบทุกห้อง ---\n")
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
    parser.add_argument("--url", default=default_url, help="URL หน้าแชท LINE OA (หลายห้องคั่นด้วย comma ได้)")
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
