# LineWebScraping

โปรเจกต์สำหรับดึงข้อมูลจาก **LINE Official Account (LINE OA)** และ **Facebook Inbox (Business Suite)** ผ่านเบราว์เซอร์ Chrome ด้วย Selenium

### แพลตฟอร์มที่รองรับ

| แพลตฟอร์ม | โหมด | คำอธิบาย |
|-----------|------|----------|
| LINE OA | ยังไม่อ่าน | รายงานแชทที่มี badge ยังไม่อ่าน |
| LINE OA | อ่านแล้วแต่ยังไม่ตอบ | แชทที่ลูกค้าส่งมาแล้วเราอ่านแล้วแต่ยังไม่ตอบ |
| Facebook Inbox | ยังไม่อ่าน | รายงานแชท Facebook ที่ยังไม่อ่าน |
| Facebook Inbox | อ่านแล้วแต่ยังไม่ตอบ | แชท Facebook ที่อ่านแล้วแต่ยังไม่ตอบ |

รองรับการส่งผลไป OpenClaw (ถ้ากำหนด `LINE_OA_OPENCLAW_TARGET` ใน `.env`)

---

## ความต้องการของระบบ

- **Python 3** (ใช้กับ Selenium + webdriver-manager)
- **Google Chrome** (ให้สคริปต์เปิดหรือเชื่อมต่อที่ port 9222; หลายบัญชีใช้หลาย port ได้)
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
| `LINE_OA_URL` | URL หน้าแชท LINE OA (หนึ่ง URL หรือหลายห้องคั่นด้วย comma เช่น `https://chat.line.biz/xxx,https://chat.line.biz/yyy`) |
| `LINE_OA_PORTS` | (หลายบัญชี) รายการ port คั่น comma สอดคล้องกับ URL — **ลิงก์แรกใช้ port แรก**, ลิงก์ที่สองใช้ port ที่สอง (เช่น `9222,9223`) |
| `LINE_OA_INTERVAL` | ช่วงตรวจสอบ (วินาที) เมื่อรันโหมดต่อเนื่อง — ค่าเริ่มต้น 30 |
| `LINE_OA_CHROME_DEBUG_PORT` | พอร์ต Chrome สำหรับ LINE OA (หนึ่งหรือหลาย port คั่น comma เช่น `9222,9223`) — ถ้าไม่ตั้ง จะใช้ `CHROME_DEBUG_PORT` |
| `FB_CHROME_DEBUG_PORT` | พอร์ต Chrome สำหรับ Facebook Inbox (หนึ่งหรือหลาย port คั่น comma เช่น `9224,9225`) — ถ้าไม่ตั้ง จะใช้ `CHROME_DEBUG_PORT` |
| `CHROME_DEBUG_PORT` | ค่า fallback เมื่อไม่ตั้ง `LINE_OA_CHROME_DEBUG_PORT` / `FB_CHROME_DEBUG_PORT` — ค่าเริ่มต้น 9222 |
| `LINE_OA_OPENCLAW_TARGET` | (ถ้าต้องการ) ส่งผลรายงานไป OpenClaw ที่ target นี้ เช่น `webchat` |
| `FB_INBOX_URL` | URL ของ Facebook Inbox (หลายลิงก์คั่นด้วย comma) |
| `FB_CHROME_DEBUG_PORT` | พอร์ต Chrome สำหรับ Facebook Inbox เช่น `9224` |
| `FB_CHROME_DEBUG_PROFILE` | หมายเลข profile Chrome สำหรับ Facebook เช่น `3` |

ชื่อที่ถือว่าเป็น "ของเรา" ในแชท (สำหรับโหมดอ่านแล้วแต่ยังไม่ตอบ) ตั้งใน `line_oa_unread_messages.py` ที่ตัวแปร **`OUR_CHAT_HEADER_NAMES`** (เป็น list ของ string).

---

## การใช้งาน

### 1. เปิด Chrome สำหรับสคริปต์ (ทำก่อนรัน Python)

**รันครั้งเดียว เปิดตาม .env (แนะนำหลายบัญชี)**

สคริปต์จะอ่าน **LINE_OA_PORTS** หรือ **LINE_OA_CHROME_DEBUG_PORT** จาก `.env` แล้วเปิด Chrome สำหรับ LINE OA ตามจำนวน port ที่กำหนด (ลิงก์แรกใช้ port แรก ฯลฯ)  
สำหรับ Facebook ใช้ **FB_CHROME_DEBUG_PORT** ใน `.env` — เปิด Chrome แยก (หรือใช้พอร์ตคนละชุดกับ LINE)

| บัญชี | Port | โปรไฟล์โฟลเดอร์ |
|-------|------|------------------|
| ที่ 1 | 9222 | `chrome_debug_profile` |
| ที่ 2 | 9223 | `chrome_debug_profile_2` |
| ที่ 3 | 9224 | `chrome_debug_profile_3` |

**ใน `.env` ตั้งเช่น (LINE 2 บัญชี, Facebook 2 บัญชี แยกพอร์ตกัน)**
```env
LINE_OA_CHROME_DEBUG_PORT=9222,9223
# หรือใช้ LINE_OA_PORTS=9222,9223 เมื่อต้องการแยกรายการ port กับ URL
FB_CHROME_DEBUG_PORT=9224,9225
```
หรือถ้าใช้พอร์ตร่วมกันแบบเดิม: `CHROME_DEBUG_PORT=9222`

**Windows**
```cmd
start_chrome_for_script.bat
```

**Mac/Linux**
```bash
./start_chrome_for_script.sh
```

จะเปิด Chrome 2 ตัว (port 9222 และ 9223) ให้ จากนั้นล็อกอิน LINE OA ในแต่ละหน้าต่าง แล้วรัน `python line_oa_unread_messages.py --report-format summary-once` (ใช้ค่า LINE_OA_URL / LINE_OA_PORTS จาก .env)

**เปิดแค่บัญชีเดียวหรือเปิดแค่ slot ที่ต้องการ**

- ไม่มี `.env` หรือมีแค่ `LINE_OA_CHROME_DEBUG_PORT=9222` (หรือ `CHROME_DEBUG_PORT=9222`) = เปิดแค่ 1 ตัว (port 9222)
- ส่ง argument ตัวเลข = เปิดแค่ slot นั้น: `start_chrome_for_script.bat 2` หรือ `./start_chrome_for_script.sh 2` → เปิดแค่ port 9223

**กำหนดลิงก์กับ port คู่กัน (ลิงก์แรก–port แรก):** ใส่ `LINE_OA_URL=url1,url2` และ `LINE_OA_PORTS=9222,9223` ใน `.env` (หรือ `--url` กับ `--ports`) สคริปต์ Python จะเปิด url1 ใน Chrome ที่ port 9222 และ url2 ใน port 9223 ให้อัตโนมัติ (โหมด summary-once / read-not-replied-today เท่านั้น)

(ถ้าใช้ cron สคริปต์ `run_line_oa_job.sh` / `run_read_not_replied_daily.sh` จะเช็คพอร์ตจาก `LINE_OA_CHROME_DEBUG_PORT` แล้วรัน Chrome ให้เองถ้ายังไม่เปิด)

---

### 2. รันด้วยมือ

**รายงานข้อความที่ยังไม่อ่าน (รันครั้งเดียว แล้วจบ)**

```bash
python line_oa_unread_messages.py --url "https://chat.line.biz/..." --connect-chrome 9222 --report-format summary-once --send-openclaw-target webchat
```

**หลายห้องแชท** — ใส่หลาย URL คั่นด้วย comma ใน `--url` หรือใน `LINE_OA_URL`:

```bash
python line_oa_unread_messages.py --url "https://chat.line.biz/xxx,https://chat.line.biz/yyy" --connect-chrome 9222 --report-format summary-once
```

ถ้าตั้ง `LINE_OA_URL` และ `LINE_OA_CHROME_DEBUG_PORT` ใน `.env` แล้ว สามารถย่อเป็น:

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

## Facebook Inbox

### ตั้งค่า `.env`

```env
FB_INBOX_URL=https://business.facebook.com/latest/inbox/all?page_id=...,https://business.facebook.com/latest/inbox/all?page_id=...
FB_CHROME_DEBUG_PORT=9224
FB_CHROME_DEBUG_PROFILE=3
```

- `FB_INBOX_URL` — ลิงก์หน้า Inbox ของ Facebook Business Suite (รองรับหลายลิงก์คั่นด้วย comma)
- `FB_CHROME_DEBUG_PORT` — พอร์ต Chrome ที่เปิดสำหรับ Facebook (แยกจาก LINE OA)

### รันด้วยมือ

**ข้อความที่ยังไม่อ่าน**

```bash
python facebook_unread_messages.py --debug
```

**อ่านแล้วแต่ยังไม่ตอบ**

```bash
python facebook_read_not_replied.py --debug
```

### รันด้วย Shell Script

```bash
# ยังไม่อ่าน
./run_facebook_job.sh

# อ่านแล้วแต่ยังไม่ตอบ
./run_facebook_read_not_replied_job.sh
```

ทั้ง 2 สคริปต์รับ argument เพิ่มเติมได้ เช่น `--debug`, `--today-only`, `--within-days 5`, `--no-scroll`

### วิธีการทำงาน

สคริปต์ Facebook ทำงานดังนี้:

1. **เชื่อมต่อ Chrome** ที่เปิดอยู่ผ่าน debug port (`FB_CHROME_DEBUG_PORT`)
2. **สร้างแท็บใหม่** สำหรับแต่ละลิงก์ใน `FB_INBOX_URL`
3. **เลื่อนลง** จนเจอฟอร์มวันที่ (วว/ดด/ปป) เพื่อให้ FB โหลดรายการแชททั้งหมด
4. **เลื่อนกลับขึ้นบนสุด** แล้ว **ตรวจสอบ 2 ครั้ง** เพื่อความถูกต้อง (deduplicate)
5. **ปิดแท็บ** แล้วทำลิงก์ถัดไป
6. **รวมผลทุกลิงก์** แล้วสร้างรายงาน

### ตัวอย่างผลลัพธ์

```
📋 Facebook Inbox: อ่านแล้วแต่ยังไม่ตอบ (ทั้งสัปดาห์)
ลิงก์ที่ 1/2:
  ชื่อ: **Supanee Rungsirat** ข้อความ: **ร้านอยู่ที่ไหน** เวลา: **วันพฤหัสบดี พฤ.**
  ชื่อ: **วรวิทย์ คลังแสง** ข้อความ: **ขอเรทราคา - ขั้นต่ำ** เวลา: **วันพฤหัสบดี พฤ.**
ลิงก์ที่ 2/2:
  ชื่อ: **อดิศร เวฬุวนารักษ์** ข้อความ: **ทดสอบแชทนี้ไม่ต้องอ่าน** เวลา: **วันพฤหัสบดี พฤ.**
--- รวม 3 รายการ ---
```

---

## โครงสร้างไฟล์หลัก

### LINE OA

| ไฟล์ | ความหมาย |
|------|----------|
| `line_oa_unread_messages.py` | สคริปต์หลัก: ดึงข้อความยังไม่อ่าน / อ่านแล้วยังไม่ตอบ รองรับหลายโหมด |
| `line_oa_read_not_replied_once.py` | เรียกโหมด "อ่านแล้วแต่ยังไม่ตอบของวันนี้" รันครั้งเดียว (สำหรับ cron) |
| `run_line_oa_job.sh` | Wrapper: เปิด Chrome ถ้ายังไม่มี แล้วรันรายงานยังไม่อ่าน |
| `run_read_not_replied_daily.sh` | Wrapper: เปิด Chrome ถ้ายังไม่มี แล้วรันอ่านแล้วยังไม่ตอบรายวัน |

### Facebook Inbox

| ไฟล์ | ความหมาย |
|------|----------|
| `facebook_unread_messages.py` | Orchestrator: เชื่อม Chrome → สร้างแท็บ → สแกนแต่ละลิงก์ → รายงาน |
| `facebook_read_not_replied.py` | รันโหมด "อ่านแล้วแต่ยังไม่ตอบ" โดยตรง |
| `fb_connect_chrome.py` | เชื่อมต่อ Chrome ผ่าน debug port |
| `fb_open_tab.py` | สร้างแท็บใหม่ / ปิดแท็บ |
| `fb_scroll_load.py` | เลื่อนลงจนเจอ วว/ดด/ปป → เลื่อนขึ้น → ตรวจ 2 ครั้ง → dedup |
| `fb_get_threads.py` | ดึงรายการแชทจากหน้า Inbox |
| `fb_report.py` | สร้างรายงานจัดกลุ่มตามลิงก์ |
| `fb_openclaw.py` | ส่งรายงานไป OpenClaw |
| `run_facebook_job.sh` | Wrapper: รันรายงานยังไม่อ่าน |
| `run_facebook_read_not_replied_job.sh` | Wrapper: รันรายงานอ่านแล้วแต่ยังไม่ตอบ |

### ไฟล์ทั่วไป

| ไฟล์ | ความหมาย |
|------|----------|
| `start_chrome_for_script.bat` / `.sh` | เปิด Chrome ที่ debug port สำหรับให้สคริปต์เชื่อมต่อ |
| `close_chrome_port_9222.py` / `.bat` / `.sh` | ปิด Chrome ที่ใช้ port ที่กำหนด |
| `crontab.example` | ตัวอย่าง crontab สำหรับรันตามเวลา |
| `.env.example` | ตัวอย่าง config — copy เป็น `.env` แล้วแก้ค่า (อย่า commit `.env`) |
| `requirements.txt` | Python dependencies (selenium, webdriver-manager) |

---

## แก้ปัญหา

- **Selector ไม่ตรงกับหน้าเว็บ** — รันด้วย `--debug` แล้วดู HTML/class ที่พิมพ์ออกมา จากนั้นแก้ `CONVERSATION_SELECTORS` / XPath ใน `line_oa_unread_messages.py`
- **Chrome ไม่เจอหรือ port ถูกใช้** — ตรวจ path Chrome ใน `start_chrome_for_script.bat` หรือ `.sh` และตรวจว่าไม่มีโปรแกรมอื่นใช้พอร์ตนั้น (9222, 9223, …)
- **หลายบัญชี LINE** — เปิด Chrome แยกตัวต่อบัญชี (ใช้ argument ตัวเลขใน start_chrome เช่น `start_chrome_for_script.bat 2`) แล้วรันสคริปต์ด้วย `--connect-chrome <port>` ให้ตรงกับแต่ละบัญชี
- **ล็อกอิน LINE OA** — ต้องล็อกอินใน Chrome ที่สคริปต์ใช้ (ตัวที่เปิดด้วย `start_chrome_for_script`) ครั้งแรก หลังจากนั้น profile จะถูกจำ

---

## หมายเหตุ

- อย่า commit ไฟล์ `.env` (มี URL และค่าลับ) ใช้เฉพาะ `.env.example` เป็นตัวอย่างใน repo
- โฟลเดอร์ profile Chrome (เช่น `chrome_profile_line_oa`) ถูกสร้างในโฟลเดอร์โปรเจกต์ เพื่อเก็บ session ล็อกอิน
