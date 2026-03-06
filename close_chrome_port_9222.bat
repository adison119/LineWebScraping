@echo off
REM ปิด Chrome ที่ใช้ port 9222 (สำหรับ LINE OA)
REM เรียกเมื่อไหร่ก็ได้ หรือให้ cron/OpenClaw ตั้งเวลาเรียก เช่น 19:00
cd /d "%~dp0"
python close_chrome_port_9222.py
