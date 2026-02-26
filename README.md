# LineWebScraping

โปรเจกต์สำหรับดึงข้อมูลจาก LINE Official Account (LINE OA) ผ่านเบราว์เซอร์ Chrome ด้วย Selenium มีสองโหมดหลัก:

1. **ข้อความที่ยังไม่อ่าน** — รายงานแชทที่มี badge ยังไม่อ่าน (รันครั้งเดียวหรือตามเวลา เช่น ทุก 1 ชม.)
2. **อ่านแล้วแต่ยังไม่ตอบของวันนี้** — รายงานแชทที่ลูกค้าส่งมาแล้วเราอ่านแล้วแต่ยังไม่ตอบ (เหมาะรันครั้งเดียวหลังเลิกงาน เช่น 17:35)

รองรับการส่งผลไป OpenClaw (ถ้ากำหนด `LINE_OA_OPENCLAW_TARGET` ใน `.env`)

---

## ความต้องการของระบบ

- **Python 3** (ใช้กับ Selenium + webdriver-manager)
- **Google Chrome** (ให้สคริปต์เปิดหรือเชื่อมต่อที่ port 9222)
- ไฟล์ **`.env`** สำหรับ URL และค่าต่างๆ (ดู `.env.example`)

---

## การติดตั้ง

```bash
# โคลนโปรเจกต์แล้วเข้าโฟลเดอร์
cd LineWebScraping

# ติดตั้ง dependencies
pip install -r requirements.txt

# สร้างไฟล์ config จากตัวอย่าง แล้วแก้ไขค่า
# Windows: copy .env.example .env
# Mac/Linux:
cp .env.example .env
```

แก้ไข `.env` ให้ครบ โดยเฉพาะ:

| ตัวแปร | ความหมาย |
|--------|----------|
| `LINE_OA_URL` | URL หน้าแชท LINE OA (เช่น https://chat.line.biz/...) |
| `LINE_OA_INTERVAL` | ช่วงตรวจสอบ (วินาที) เมื่อรันโหมดต่อเนื่อง — ค่าเริ่มต้น 30 |
| `CHROME_DEBUG_PORT` | พอร์ต Chrome สำหรับสคริปต์ — ค่าเริ่มต้น 9222 |
| `LINE_OA_OPENCLAW_TARGET` | (ถ้าต้องการ) ส่งผลรายงานไป OpenClaw ที่ target นี้ เช่น `webchat` |

ชื่อที่ถือว่าเป็น "ของเรา" ในแชท (สำหรับโหมดอ่านแล้วแต่ยังไม่ตอบ) ตั้งใน `line_oa_unread_messages.py` ที่ตัวแปร **`OUR_CHAT_HEADER_NAMES`** (เป็น list ของ string).

---

## การใช้งาน

### 1. เปิด Chrome สำหรับสคริปต์ (ทำก่อนรัน Python)

**Windows**

```cmd
start_chrome_for_script.bat
```

จากนั้นล็อกอิน LINE OA ใน Chrome ที่เปิดขึ้นมา แล้วค่อยรันสคริปต์ด้านล่าง

**Mac/Linux**

```bash
./start_chrome_for_script.sh
```

(ถ้าใช้ cron สคริปต์ `run_line_oa_job.sh` / `run_read_not_replied_daily.sh` จะเช็คพอร์ต 9222 แล้วรัน Chrome ให้เองถ้ายังไม่เปิด)

---

### 2. รันด้วยมือ

**รายงานข้อความที่ยังไม่อ่าน (รันครั้งเดียว แล้วจบ)**

```bash
python line_oa_unread_messages.py --url "https://chat.line.biz/..." --connect-chrome 9222 --report-format summary-once --send-openclaw-target webchat
```

ถ้าตั้ง `LINE_OA_URL` และ `CHROME_DEBUG_PORT` ใน `.env` แล้ว สามารถย่อเป็น:

```bash
python line_oa_unread_messages.py --connect-chrome 9222 --report-format summary-once --send-openclaw-target webchat
```

**รายงานอ่านแล้วแต่ยังไม่ตอบของวันนี้ (รันครั้งเดียว)**

```bash
python line_oa_read_not_replied_once.py --connect-chrome 9222 --send-openclaw-target webchat
```

หรือใช้ค่าจาก `.env` โดยไม่ต้องส่งอาร์กิวเมนต์ (ต้องมี `LINE_OA_URL`).

**โหมดอื่นๆ ของ line_oa_unread_messages.py**

- `--report-format full` — แสดงข้อความเต็ม รันต่อเนื่อง (วนลูป)
- `--report-format read-not-replied-today` — เหมือน `line_oa_read_not_replied_once.py`
- `--debug` — พิมพ์ข้อมูล HTML/selector สำหรับแก้ selector
- `--max-hours N` — หยุดหลังรันครบ N ชั่วโมง (ใช้กับ scheduler)

---

### 3. รันตามเวลา (Cron / Task Scheduler)

ตัวอย่างตั้งเวลา:

| งาน | เวลา | สคริปต์ |
|-----|------|--------|
| ข้อความที่ยังไม่อ่าน | ทุก 1 ชม. 8:30–17:30 | `run_line_oa_job.sh` |
| อ่านแล้วแต่ยังไม่ตอบของวันนี้ | ทุกวัน 17:35 ครั้งเดียว | `run_read_not_replied_daily.sh` |

**Mac/Linux (cron)**

1. สร้างโฟลเดอร์ log:  
   `mkdir -p "$HOME/.openclaw/workspace/LineWebScraping/logs"`
2. เปิด crontab:  
   `crontab -e`
3. คัดลอกจาก `crontab.example` แล้วแก้ path `WORKSPACE` ให้ตรงกับเครื่องคุณ

**ถ้า Cron รันแล้ว OpenClaw ไม่ส่งไป LINE** — อ่าน [CRON_OPENCLAW.md](CRON_OPENCLAW.md) (ตั้ง HOME/PATH ใน crontab และให้ OpenClaw Gateway รันอยู่)

**Windows**

ใช้ Task Scheduler ตั้งเวลาให้รัน `start_chrome_for_script.bat` (ถ้าต้องการให้ Chrome พร้อม) แล้วตั้ง task แยกให้รัน Python เช่น:

- งานรายชั่วโมง: เรียก `line_oa_unread_messages.py` ด้วย `--report-format summary-once` ที่ 8:30, 9:30, …, 17:30
- งานรายวัน: เรียก `line_oa_read_not_replied_once.py` ที่ 17:35

หรือใช้ WSL แล้วใช้ cron ตาม `crontab.example` ก็ได้

---

## โครงสร้างไฟล์หลัก

| ไฟล์ | ความหมาย |
|------|----------|
| `line_oa_unread_messages.py` | สคริปต์หลัก: ดึงข้อความยังไม่อ่าน / อ่านแล้วยังไม่ตอบ รองรับหลายโหมด |
| `line_oa_read_not_replied_once.py` | เรียกโหมด "อ่านแล้วแต่ยังไม่ตอบของวันนี้" รันครั้งเดียว (สำหรับ cron) |
| `run_line_oa_job.sh` | Wrapper: เปิด Chrome ถ้ายังไม่มี แล้วรันรายงานยังไม่อ่าน (summary-once) |
| `run_read_not_replied_daily.sh` | Wrapper: เปิด Chrome ถ้ายังไม่มี แล้วรันอ่านแล้วยังไม่ตอบรายวัน |
| `start_chrome_for_script.bat` / `.sh` | เปิด Chrome ที่ port 9222 สำหรับให้สคริปต์เชื่อมต่อ |
| `crontab.example` | ตัวอย่าง crontab สำหรับรันทั้งสองงานตามเวลา |
| `.env.example` | ตัวอย่าง config — copy เป็น `.env` แล้วแก้ค่า (อย่า commit `.env`) |
| `requirements.txt` | Python dependencies (selenium, webdriver-manager) |

---

## แก้ปัญหา

- **Selector ไม่ตรงกับหน้าเว็บ** — รันด้วย `--debug` แล้วดู HTML/class ที่พิมพ์ออกมา จากนั้นแก้ `CONVERSATION_SELECTORS` / XPath ใน `line_oa_unread_messages.py`
- **Chrome ไม่เจอหรือ port ถูกใช้** — ตรวจ path Chrome ใน `start_chrome_for_script.bat` หรือ `.sh` และตรวจว่าไม่มีโปรแกรมอื่นใช้พอร์ต 9222
- **ล็อกอิน LINE OA** — ต้องล็อกอินใน Chrome ที่สคริปต์ใช้ (ตัวที่เปิดด้วย `start_chrome_for_script`) ครั้งแรก หลังจากนั้น profile จะถูกจำ

---

## หมายเหตุ

- อย่า commit ไฟล์ `.env` (มี URL และค่าลับ) ใช้เฉพาะ `.env.example` เป็นตัวอย่างใน repo
- โฟลเดอร์ profile Chrome (เช่น `chrome_profile_line_oa`) ถูกสร้างในโฟลเดอร์โปรเจกต์ เพื่อเก็บ session ล็อกอิน
