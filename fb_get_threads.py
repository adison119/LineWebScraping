# -*- coding: utf-8 -*-
"""
ดึงรายการแชท Facebook Inbox — 1 ฟังก์ชัน: get_facebook_threads(driver, ...)
"""
import re
import sys
import time
from calendar import monthrange
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DEFAULT_WAIT = 15
WITHIN_DAYS_DEFAULT = 3

# Facebook Inbox: แถวแชท = div._at41._8gcz ที่มี span[data-surface*="bizweb:INBOX/thread_row"]
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
UNREAD_MARKER_CLASS = "_284c"
READ_MARKER_CLASS = "_2tms"
REPLIED_PREFIX = "คุณ:"
SYSTEM_PREVIEW_PREFIXES = ["ตั้งระยะข้อมูลลูกค้า"]
THAI_DAY_ABBREVS = {"จ.": 0, "อ.": 1, "พ.": 2, "พฤ.": 3, "ศ.": 4, "ส.": 5, "อา.": 6}
THAI_DAY_FULL_NAMES = {"วันจันทร์": 0, "วันอังคาร": 1, "วันพุธ": 2, "วันพฤหัสบดี": 3, "วันศุกร์": 4, "วันเสาร์": 5, "วันอาทิตย์": 6}


def _allowed_weekdays_for_days_back(within_days):
    now = datetime.now()
    allowed = set()
    for i in range(within_days):
        d = now - timedelta(days=i)
        allowed.add(d.weekday())
    return allowed


def _is_time_within_week(time_text, within_days=WITHIN_DAYS_DEFAULT):
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
    for day_name, weekday in THAI_DAY_FULL_NAMES.items():
        if day_name in s:
            return weekday in allowed_weekdays
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
            return False
    return True


def _is_time_today(time_text):
    if not (time_text or "").strip():
        return False
    return "วันนี้" in (time_text or "").strip()


def _scroll_inbox_to_top(driver, wait_seconds=DEFAULT_WAIT):
    try:
        wait = WebDriverWait(driver, wait_seconds)
        for conv_xpath, _n, _p, _t in CONVERSATION_SELECTORS:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
                rows = driver.find_elements(By.XPATH, conv_xpath)
                if not rows:
                    continue
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
                if scrollable:
                    driver.execute_script("arguments[0].scrollTop = 0;", scrollable)
                    time.sleep(0.5)
                return
            except Exception:
                continue
    except Exception:
        pass


def _scroll_through_rows_one_by_one(driver, rows, scroll_pause=0.25):
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
                row_height = driver.execute_script("return arguments[0].offsetHeight || 100;", row)
                driver.execute_script(
                    "var s = arguments[0]; s.scrollTop = s.scrollTop + arguments[1];",
                    scrollable, row_height,
                )
                time.sleep(scroll_pause)
            except Exception:
                continue
    except Exception:
        pass


def _is_system_preview(preview_text):
    if not (preview_text or "").strip():
        return False
    s = (preview_text or "").strip()
    for prefix in SYSTEM_PREVIEW_PREFIXES:
        if prefix and s.startswith(prefix):
            return True
    return False


def is_counted_as_read(preview_text):
    return is_replied_by_us(preview_text) or _is_system_preview(preview_text)


def is_unread_element(element):
    try:
        cls = (element.get_attribute("class") or "")
        return UNREAD_MARKER_CLASS in cls
    except Exception:
        return False


def is_read_element(element):
    """แถวที่อ่านแล้ว = ไม่มี _284c และมี _2tms (ข้อความสีจาง); ใช้กรองโหมด อ่านแล้วแต่ยังไม่ตอบ"""
    try:
        cls = (element.get_attribute("class") or "")
        return UNREAD_MARKER_CLASS not in cls and READ_MARKER_CLASS in cls
    except Exception:
        return False


def is_replied_by_us(preview_text):
    if not (preview_text or "").strip():
        return False
    return (preview_text or "").strip().startswith(REPLIED_PREFIX)


def safe_find_text(parent, xpath, default=""):
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


# ฟอร์มวันที่ใน FB Inbox = วันที่แสดงทางขวาของแต่ละแถวแบบ วว/ดด/ปป (เช่น 23/12/25, 22/12/25)
# รูปแบบตัวเลข: 1-2 หลัก/1-2 หลัก/2-4 หลัก
DATE_DISPLAY_PATTERN = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")
# หรือ input ที่มี placeholder วว/ดด/ปป (กรณีมีฟอร์มกรอกวันที่)
DATE_FORM_INPUT_XPATH = (
    ".//input[contains(@placeholder, 'วว') or contains(@placeholder, 'ดด') or contains(@placeholder, 'ปป')]"
    " | .//*[@placeholder and (contains(@placeholder, 'วว') or contains(@placeholder, 'ดด') or contains(@placeholder, 'ปป'))]"
)


def _get_scrollable_from_first_row(driver):
    """หาตัว scrollable (parent ที่มี scrollHeight > clientHeight) จากแถวแชทแถวแรก"""
    for conv_xpath, _n, _p, _t in CONVERSATION_SELECTORS:
        try:
            rows = driver.find_elements(By.XPATH, conv_xpath)
            if not rows:
                continue
            scrollable = driver.execute_script("""
                var el = arguments[0];
                var p = el.parentElement;
                while (p) {
                    if (p.scrollHeight > p.clientHeight && p.scrollHeight > 200) return p;
                    p = p.parentElement;
                }
                return null;
            """, rows[0])
            if scrollable:
                return scrollable
        except Exception:
            continue
    return None


def _scrollable_has_date_form(driver, scrollable):
    """
    เช็คว่าใน scrollable มีฟอร์มวันที่ (วว/ดด/ปป) โผล่แล้วหรือยัง:
    - วันที่แสดงแบบ DD/MM/YY (เช่น 23/12/25 ทางขวาของแถวแชท), หรือ
    - input ที่มี placeholder วว/ดด/ปป
    """
    try:
        text = driver.execute_script("return arguments[0].innerText || '';", scrollable)
        if DATE_DISPLAY_PATTERN.search(text):
            return True
        elts = scrollable.find_elements(By.XPATH, DATE_FORM_INPUT_XPATH)
        return len(elts) > 0
    except Exception:
        return False


def scroll_down_until_date_then_back_to_top(driver, max_scrolls=150, scroll_step=400,
                                            wait_seconds=DEFAULT_WAIT, debug=False):
    """
    เลื่อนลงไปข้างล่างจนเจอฟอร์มวันที่ (วว/ดด/ปป) แล้วเลื่อนกลับขึ้นบนสุด
    เรียกก่อนเริ่มการตรวจสอบ (โหมดอ่านแล้วแต่ยังไม่ตอบ) เพื่อให้ FB โหลดรายการครบ
    """
    ready, _ = wait_for_inbox_ready(driver, wait_seconds=wait_seconds, debug=debug)
    if not ready:
        return
    scrollable = _get_scrollable_from_first_row(driver)
    if not scrollable:
        if debug:
            print("[DEBUG] ไม่พบ container สำหรับเลื่อน — ข้ามขั้นเลื่อนจนเจอฟอร์มวันที่", file=sys.stderr)
        return
    try:
        for i in range(max_scrolls):
            if _scrollable_has_date_form(driver, scrollable):
                if debug:
                    print(f"[DEBUG] เจอฟอร์มวันที่ (วว/ดด/ปป) หลังเลื่อน {i + 1} รอบ — กลับขึ้นบนสุด", file=sys.stderr)
                break
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollTop + arguments[1];",
                scrollable, scroll_step,
            )
            time.sleep(0.2)
        driver.execute_script("arguments[0].scrollTop = 0;", scrollable)
        time.sleep(0.5)
    except Exception as e:
        if debug:
            print(f"[DEBUG] scroll_down_until_date_then_back_to_top: {e}", file=sys.stderr)


def wait_for_inbox_ready(driver, wait_seconds=DEFAULT_WAIT, debug=False):
    """
    รอจนหน้ารายการแชทโหลดเสร็จ (มี element แถวแชทอย่างน้อย 1 ตัว)
    คืน (True, จำนวนแถวที่เจอ) หรือ (False, 0) ถ้ารอเกิน wait_seconds
    """
    wait = WebDriverWait(driver, wait_seconds)
    for conv_xpath, _n, _p, _t in CONVERSATION_SELECTORS:
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, conv_xpath)))
            rows = driver.find_elements(By.XPATH, conv_xpath)
            n = len(rows) if rows else 0
            if debug:
                print(f"[DEBUG] หน้ารายการแชทโหลดแล้ว — เจอ {n} แถว (selector ใช้ได้)", file=sys.stderr)
            return True, n
        except Exception:
            continue
    if debug:
        print(f"[DEBUG] รอ {wait_seconds} วินาทีแล้วยังไม่พบแถวแชท — ตรวจว่าแท็บปัจจุบันเป็นหน้า FB Inbox และโหลดครบ", file=sys.stderr)
    return False, 0


def get_facebook_threads(driver, unread_only=False, read_not_replied_only=False, within_week=True,
                        within_days=WITHIN_DAYS_DEFAULT, within_today_only=False,
                        scroll_to_load_week=False, scroll_pause=0.5, max_scroll_rounds=25,
                        wait_seconds=DEFAULT_WAIT, debug=False, scroll_boundary_days=None):
    """
    ดึงรายการแชทจาก Facebook Inbox
    unread_only=True: เฉพาะแถวที่มี _284c (ยังไม่อ่าน)
    read_not_replied_only=True: เฉพาะแถวที่อ่านแล้วแต่ยังไม่ตอบ
    """
    result = []
    seen_keys = set()
    try:
        ready, _ = wait_for_inbox_ready(driver, wait_seconds=wait_seconds, debug=debug)
        if not ready:
            return result

        effective_max_rounds = (max_scroll_rounds * 2 if read_not_replied_only and scroll_to_load_week else max_scroll_rounds) if scroll_to_load_week else 1
        for _round in range(effective_max_rounds if scroll_to_load_week else 1):
            time_texts_in_batch = []
            for conv_xpath, name_xpath, preview_xpath, time_xpath in CONVERSATION_SELECTORS:
                try:
                    rows = driver.find_elements(By.XPATH, conv_xpath)
                except Exception:
                    rows = []
                if not rows:
                    continue

                read_marker_used = any(UNREAD_MARKER_CLASS in (r.get_attribute("class") or "") for r in rows)
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
                            if is_unread_element(row):
                                if debug:
                                    print(f"[DEBUG อ่านแล้วแต่ยังไม่ตอบ] ข้าม (ยังไม่อ่าน _284c ตัวหนา): sender={name_text!r}, preview={(preview_text or '')[:40]!r}...", file=sys.stderr)
                                continue
                            if is_counted_as_read(preview_text):
                                if debug:
                                    print(f"[DEBUG อ่านแล้วแต่ยังไม่ตอบ] ข้าม (เราตอบแล้ว/ข้อความระบบ): sender={name_text!r}, preview={(preview_text or '')[:40]!r}...", file=sys.stderr)
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
                            if read_not_replied_only:
                                print(f"[DEBUG อ่านแล้วแต่ยังไม่ตอบ] นำเข้า: sender={item['sender']!r}, preview={item['message'][:50]!r}..., time={item['time']!r}", file=sys.stderr)
                            else:
                                print(f"[DEBUG] sender={item['sender']!r}, preview={item['message'][:50]!r}...", file=sys.stderr)
                    except Exception as e:
                        if debug:
                            print(f"[DEBUG] skip row: {e}", file=sys.stderr)
                        continue

                if result:
                    break
            if not result and _round == 0 and not (read_not_replied_only and scroll_to_load_week):
                break
            if scroll_to_load_week:
                if not time_texts_in_batch:
                    break
                boundary_days = scroll_boundary_days if scroll_boundary_days is not None else within_days
                has_passed_boundary = any(
                    (t or "").strip() and not _is_time_within_week(t, within_days=boundary_days)
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


def scroll_inbox_to_top(driver, wait_seconds=DEFAULT_WAIT):
    """เลื่อนรายการ Inbox กลับขึ้นบนสุด — ใช้จาก orchestrator ก่อน get_threads รอบที่ 2"""
    _scroll_inbox_to_top(driver, wait_seconds)


def debug_page_structure(driver, wait_seconds=DEFAULT_WAIT):
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
