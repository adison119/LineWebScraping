# -*- coding: utf-8 -*-
"""
LINE OA - ดึงข้อความที่ยังไม่อ่าน (แก้ selector ให้ยืดหยุ่น + โหมด debug)
ถ้า selector ยังไม่ตรงกับหน้าเว็บ ให้รันด้วย --debug ก่อน แล้วดู HTML/class ที่พิมพ์ออกมา
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import argparse

# รอสูงสุด (วินาที)
DEFAULT_WAIT = 15

# รายการ selector ที่จะลองตามลำดับ (LINE OA ใช้ list-group-item-chat, h6, div.text-muted.small, div.datetime)
# แถวแรก = รายการแชท, ตามด้วย ชื่อ, ข้อความล่าสุด, เวลา
CONVERSATION_SELECTORS = [
    # รูปแบบจริงของ LINE OA (จาก DOM หน้า chat.line.biz)
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

UNREAD_CLASS_PATTERNS = ["unread", "has-new", "new-message", "selected", "active"]

# LINE OA: แถวที่ยังไม่อ่านจะมี span.badge.badge-pin.badge-primary หรือ span ตัวเลขเช่น (3), (7) ข้างชื่อ
UNREAD_BADGE_XPATH = ".//span[contains(@class, 'badge-pin')]"
# span ตัวเลข unread ข้าง h6 อยู่ใน div.d-flex.align-items-center.mb-1 เป็น sibling ของ h6
UNREAD_COUNT_SPAN_XPATH = ".//div[contains(@class, 'align-items-center') and contains(@class, 'mb-1')]//span[starts-with(normalize-space(), '(') and contains(normalize-space(), ')')]"

# ถ้า True จะนับเฉพาะรายการที่มี badge/ตัวเลข unread; ถ้า False จะดึงทุกรายการ
STRICT_UNREAD_ONLY = True


def is_unread_element(element):
    """เช็คว่าแถวแชทนี้ยังไม่อ่านหรือไม่ (class ตัวเอง หรือ LINE OA: badge-pin / ตัวเลขในวงเล็บ)"""
    try:
        cls = (element.get_attribute("class") or "").lower()
        for pattern in UNREAD_CLASS_PATTERNS:
            if pattern in cls:
                return True
        aria = (element.get_attribute("aria-label") or "").lower()
        if "unread" in aria or "new" in aria:
            return True
        # LINE OA: มีจุดสีน้ำเงิน (badge-pin) = ยังไม่อ่าน
        try:
            if element.find_elements(By.XPATH, UNREAD_BADGE_XPATH):
                return True
        except Exception:
            pass
        # LINE OA: มีตัวเลข unread ในวงเล็บเช่น (3), (7) ข้างชื่อ (ต้องเป็นตัวเลขเท่านั้น ไม่นับ (N)/(M)/ (B))
        try:
            for span in element.find_elements(By.XPATH, UNREAD_COUNT_SPAN_XPATH):
                text = (span.text or "").strip()
                if len(text) >= 3 and text[0] == "(" and text[-1] == ")":
                    mid = text[1:-1].strip()
                    if mid.isdigit():
                        return True
        except Exception:
            pass
    except Exception:
        pass
    return False


def safe_find_text(parent, xpath, default=""):
    """หา element เดียวแล้วเอา .text ถ้าไม่เจอคืน default"""
    try:
        el = parent.find_element(By.XPATH, xpath)
        return (el.text or "").strip() if el else default
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


def scrape_line_oa_unread_messages_continuous(url, check_interval_seconds=60, debug=False):
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()

    try:
        driver.get(url)
        print("โปรดล็อกอินเข้าสู่ระบบ LINE OA ในเบราว์เซอร์ที่เปิดขึ้นมา")
        input("เมื่อล็อกอินเสร็จแล้วและเห็นหน้าแชทแล้ว โปรดกด Enter เพื่อดำเนินการต่อ...")

        if debug:
            debug_page_structure(driver, wait_seconds=5)

        notified_messages = set()

        print(f"เริ่มตรวจสอบข้อความที่ยังไม่อ่านทุกๆ {check_interval_seconds} วินาที...")
        while True:
            current_unread_messages = get_unread_messages(driver, wait_seconds=10, debug=debug)

            new_unread_found = False
            for msg in current_unread_messages:
                msg_id = f"{msg['sender']}-{msg['message']}-{msg['time']}"
                if msg_id not in notified_messages:
                    if not new_unread_found:
                        print("\n--- พบข้อความที่ยังไม่อ่านใหม่! ---")
                        new_unread_found = True
                    print(f"ชื่อ: {msg['sender']}, ข้อความ: {msg['message']}, เวลา: {msg['time']}")
                    notified_messages.add(msg_id)

            if not new_unread_found and current_unread_messages:
                print("ยังไม่พบข้อความที่ยังไม่อ่านใหม่ แต่ยังมีข้อความที่ยังไม่อ่านอยู่ (แจ้งเตือนไปแล้ว)")
            elif not current_unread_messages:
                print("ไม่พบข้อความที่ยังไม่อ่าน (หรือ selector ยังไม่ตรงกับหน้าเว็บ - ลองรันด้วย --debug)")

            print(f"รอ {check_interval_seconds} วินาที ก่อนตรวจสอบอีกครั้ง...")
            time.sleep(check_interval_seconds)

    except KeyboardInterrupt:
        print("\nหยุดการทำงานด้วยตนเอง")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE OA - ตรวจสอบข้อความที่ยังไม่อ่าน")
    parser.add_argument("--url", default="https://chat.line.biz/Ua891055e09d7e52c08c29828d0f662f7", help="URL หน้าแชท LINE OA")
    parser.add_argument("--interval", type=int, default=30, help="ระยะห่างในการตรวจสอบ (วินาที)")
    parser.add_argument("--debug", action="store_true", help="เปิดโหมด debug เพื่อดู class/โครงสร้างในหน้า")
    args = parser.parse_args()

    scrape_line_oa_unread_messages_continuous(
        args.url,
        check_interval_seconds=args.interval,
        debug=args.debug,
    )
