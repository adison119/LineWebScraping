# ให้ Cron ส่งข้อความผ่าน OpenClaw ไป LINE ได้

เมื่อรันจาก **crontab** สคริปต์ทำงานแต่ OpenClaw ไม่ส่งไป LINE ส่วนตอนรันด้วยมือส่งได้ — มักเป็นเพราะ **สภาพแวดล้อม (environment)** ของ cron ไม่เหมือนตอนเปิดเทอร์มินัล และ/หรือ **OpenClaw Gateway ไม่ได้รันอยู่** ตอนที่ cron ทำงาน

---

## 1. ตั้งค่า environment ใน crontab

Cron รันด้วย environment น้อยมาก (PATH สั้น, บางระบบ HOME อาจไม่ตรง) ทำให้คำสั่ง `openclaw` หา config หรือเชื่อมต่อ Gateway ไม่ได้

**ทำแบบนี้:**

1. เปิดเทอร์มินัล (ที่รันแล้วส่ง LINE ได้) แล้วรัน:
   ```bash
   echo $HOME
   echo $PATH
   ```
2. เปิด crontab: `crontab -e`
3. **ใส่บรรทัดด้านบนของ crontab** (ก่อนบรรทัด schedule) ให้ตรงกับเครื่องคุณ:

   ```bash
   SHELL=/bin/bash
   HOME=/Users/ชื่อคุณ          # ใช้ค่าจาก echo $HOME
   PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
   ```

   แก้ `HOME=` ให้เป็น path จริงที่คุณได้จาก `echo $HOME` (เช่น `/Users/kira`)

ถ้าไม่ตั้ง `HOME` และ `PATH` ใน crontab, ตอน cron รันคำสั่ง `openclaw` อาจใช้ config คนละที่หรือหา Gateway ไม่เจอ จึงไม่ส่งไป LINE

---

## 2. ให้ OpenClaw Gateway รันอยู่ตอนที่ cron ทำงาน

`openclaw message send` จะส่งข้อความไปที่ **OpenClaw Gateway** แล้ว Gateway ค่อยส่งออกไป LINE  
ถ้า Gateway ไม่ได้รันอยู่ตอนที่ cron ทำงาน การส่งจะไม่เกิดขึ้น

**ทางเลือก:**

### 2.1 รัน Gateway เป็น background ตลอด (แนะนำ)

- เปิดเทอร์มินัลแล้วรัน Gateway (ตามวิธีที่คุณใช้อยู่ เช่น `openclaw gateway` หรือ `openclaw start`) **แล้วไม่ปิดเทอร์มินัล** หรือ
- รัน Gateway เป็น **service** เพื่อให้รันตลอดแม้ปิดเทอร์มินัล

**ตัวอย่างบน macOS (launchd):**

1. สร้างไฟล์ `~/Library/LaunchAgents/ai.openclaw.gateway.plist` (หรือชื่ออื่น) โดยแก้ `YOUR_USERNAME` และ path ให้ตรงเครื่อง:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>ai.openclaw.gateway</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/openclaw</string>
    <string>gateway</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/openclaw-gateway.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/openclaw-gateway.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>/Users/YOUR_USERNAME</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
```

2. โหลดและสตาร์ท:
   ```bash
   launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
   ```
3. ตรวจว่า Gateway รัน: ดูที่ `openclaw` docs ว่ามีคำสั่ง status หรือดูที่ log ด้านบน

เมื่อ Gateway รันแบบนี้ ตอน cron ทำงานคำสั่ง `openclaw message send` จะเชื่อมต่อ Gateway ได้และส่งไป LINE ได้ (ถ้าตั้ง target ถูกต้อง)

### 2.2 ไม่รัน Gateway เป็น service

ถ้าไม่ตั้ง Gateway ให้รันตลอด cron จะรันสคริปต์ได้ แต่ตอนที่ cron เรียก `openclaw message send` จะไม่มี process Gateway รออยู่ จึงไม่ส่งไป LINE

---

## 3. ตรวจสอบว่าไม่ส่งเพราะอะไร

ดู log ของ job ที่ cron รัน (path ตามที่ตั้งใน crontab เช่น `logs/unread.log`):

```bash
tail -100 ~/.openclaw/workspace/LineWebScraping/logs/unread.log
```

ถ้ามีบรรทัดแบบ:

- `ส่ง openclaw ไม่สำเร็จ` หรือ `ไม่พบคำสั่ง openclaw` → แก้ PATH / HOME ใน crontab และให้สคริปต์หา `openclaw` ได้ (ตามที่ตั้งในโปรเจกต์)
- ข้อความ error จาก OpenClaw เกี่ยวกับ connection / gateway → แก้ให้ Gateway รันอยู่และใช้ HOME/PATH เดียวกับตอนรันด้วยมือ

---

## สรุปสั้นๆ

| สิ่งที่ต้องทำ | เพื่ออะไร |
|---------------|-----------|
| ตั้ง `HOME` และ `PATH` ใน crontab | ให้คำสั่ง `openclaw` หา config และเชื่อมต่อ Gateway ได้เหมือนตอนรันด้วยมือ |
| ให้ OpenClaw Gateway รันอยู่ตลอด (service / launchd) | ตอน cron รัน `openclaw message send` จะมี Gateway รอรับและส่งไป LINE ได้ |
| ตั้ง `LINE_OA_OPENCLAW_TARGET` ใน `.env` | ให้สคริปต์รู้ว่าจะส่งไป target ไหน (เช่น webchat ที่ผูกกับ LINE) |

ถ้าทั้งสามข้อครบ cron จะส่งข้อความผ่าน OpenClaw ไป LINE ได้เหมือนตอนรันด้วยมือ
