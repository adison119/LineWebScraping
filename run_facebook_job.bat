@echo off
REM รัน Facebook Inbox: สรุปรายการแชท (summary-once) — ค่าเริ่มต้น
REM ใช้ FB_INBOX_URL และ FB_CHROME_DEBUG_PORT จาก .env ถ้ามี
cd /d "%~dp0"
python facebook_unread_messages.py --report-format summary-once %*
