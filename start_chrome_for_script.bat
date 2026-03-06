@echo off
setlocal EnableDelayedExpansion
REM รันครั้งเดียว: อ่านพอร์ตจาก .env แล้วเปิด Chrome สำหรับ LINE OA และ Facebook Inbox
REM อ่าน LINE_OA_PORTS / LINE_OA_CHROME_DEBUG_PORT และ FB_CHROME_DEBUG_PORT (รวมเป็นรายการพอร์ตเดียว)
REM Usage: start_chrome_for_script.bat
REM        หรือส่งตัวเลข slot: start_chrome_for_script.bat 2 (เปิดแค่ slot ที่ 2)

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%" 2>nul || exit /b 1

REM โหลด port และ profile สำหรับ LINE และ Facebook จาก .env
set "LINE_OA_PORTS="
set "LINE_OA_CHROME_DEBUG_PORT="
set "FB_CHROME_DEBUG_PORT="
set "FB_CHROME_DEBUG_PROFILE="
set "CHROME_DEBUG_PORT="
if exist ".env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    set "key=%%a"
    set "key=!key: =!"
    if "!key!"=="LINE_OA_PORTS" set "LINE_OA_PORTS=%%b"
    if "!key!"=="LINE_OA_CHROME_DEBUG_PORT" set "LINE_OA_CHROME_DEBUG_PORT=%%b"
    if "!key!"=="FB_CHROME_DEBUG_PORT" set "FB_CHROME_DEBUG_PORT=%%b"
    if "!key!"=="FB_CHROME_DEBUG_PROFILE" set "FB_CHROME_DEBUG_PROFILE=%%b"
    if "!key!"=="CHROME_DEBUG_PORT" set "CHROME_DEBUG_PORT=%%b"
  )
)
REM Facebook ใช้ profile หมายเลขเท่าไร (โฟลเดอร์ chrome_debug_profile_3 ถ้าไม่กำหนด)
set "FB_PROFILE_NUM=!FB_CHROME_DEBUG_PROFILE: =!"
if "!FB_PROFILE_NUM!"=="" set "FB_PROFILE_NUM=3"

REM รายการพอร์ต LINE: ใช้ LINE_OA_PORTS ถ้ามี ไม่ก็ LINE_OA_CHROME_DEBUG_PORT ไม่ก็ CHROME_DEBUG_PORT
set "LINE_PORTS=!LINE_OA_PORTS!"
if "!LINE_PORTS!"=="" set "LINE_PORTS=!LINE_OA_CHROME_DEBUG_PORT!"
if "!LINE_PORTS!"=="" set "LINE_PORTS=!CHROME_DEBUG_PORT!"
if "!LINE_PORTS!"=="" set "LINE_PORTS=9222"
REM ลบช่องว่าง
set "LINE_PORTS=!LINE_PORTS: =!"
set "FB_CHROME_DEBUG_PORT=!FB_CHROME_DEBUG_PORT: =!"

REM ถ้ารันด้วย argument ตัวเลข = เปิดแค่ slot นั้น (โหมดเดิม)
if not "%~1"=="" (
  set "SLOT=%~1"
  set /a "PORT=9221+!SLOT!" 2>nul
  if defined PORT set "LINE_PORTS=!PORT!" & set "FB_CHROME_DEBUG_PORT="
)

REM หา Chrome
set "CHROME="
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if "!CHROME!"=="" (
  echo Chrome not found. Edit the path in this .bat file.
  pause
  exit /b 1
)

set OPENED=0

REM --- เปิด Chrome สำหรับ LINE (profile ตาม slot: 9222=profile, 9223=profile_2 ฯลฯ) ---
set "PORTS_RAW=!LINE_PORTS!"
:line_port_loop
if "!PORTS_RAW!"=="" goto :line_port_done
for /f "tokens=1,* delims=," %%a in ("!PORTS_RAW!") do (set "CURPORT=%%a" & set "PORTS_RAW=%%b")
set "CURPORT=!CURPORT: =!"
if "!CURPORT!"=="" goto :line_port_loop
set /a "SLOT=!CURPORT!-9221" 2>nul
if !SLOT! LSS 1 set SLOT=1
if !SLOT! equ 1 (set "DEBUG_PROFILE_NAME=chrome_debug_profile") else (set "DEBUG_PROFILE_NAME=chrome_debug_profile_!SLOT!")
set "DEBUG_PROFILE=!SCRIPT_DIR!\!DEBUG_PROFILE_NAME!"
netstat -an | findstr ":!CURPORT!" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (echo [Warning] Port !CURPORT! is already in use. Skip.) else (
  if not exist "!DEBUG_PROFILE!" mkdir "!DEBUG_PROFILE!"
  start "" "!CHROME!" --remote-debugging-port=!CURPORT! --user-data-dir="!DEBUG_PROFILE!"
  echo Chrome started [LINE]: port !CURPORT!, profile !DEBUG_PROFILE_NAME!
  set /a OPENED+=1
  timeout /t 1 /nobreak >nul 2>&1
)
goto :line_port_loop
:line_port_done

REM --- เปิด Chrome สำหรับ Facebook (profile ร่วม = แค่พอร์ตแรก; ใช้ profile ตาม FB_CHROME_DEBUG_PROFILE เช่น 3) ---
set "PORTS_RAW=!FB_CHROME_DEBUG_PORT!"
if not "!PORTS_RAW!"=="" (
  for /f "tokens=1,* delims=," %%a in ("!PORTS_RAW!") do set "CURPORT=%%a"
  set "CURPORT=!CURPORT: =!"
  if not "!CURPORT!"=="" (
    if "!FB_PROFILE_NUM!" equ "1" (set "DEBUG_PROFILE_NAME=chrome_debug_profile") else (set "DEBUG_PROFILE_NAME=chrome_debug_profile_!FB_PROFILE_NUM!")
    set "DEBUG_PROFILE=!SCRIPT_DIR!\!DEBUG_PROFILE_NAME!"
    netstat -an | findstr ":!CURPORT!" | findstr "LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (echo [Warning] Port !CURPORT! is already in use. Skip.) else (
      if not exist "!DEBUG_PROFILE!" mkdir "!DEBUG_PROFILE!"
      start "" "!CHROME!" --remote-debugging-port=!CURPORT! --user-data-dir="!DEBUG_PROFILE!"
      echo Chrome started [FB]: port !CURPORT!, profile !DEBUG_PROFILE_NAME!
      set /a OPENED+=1
      timeout /t 1 /nobreak >nul 2>&1
    )
  )
)

if %OPENED% equ 0 (
  echo No Chrome started. All ports may be in use.
  pause
  exit /b 1
)

echo.
echo Started %OPENED% Chrome profile(s).
echo   - ล็อกอิน LINE OA ในหน้าต่างที่ตรงกับพอร์ต LINE (จาก LINE_OA_CHROME_DEBUG_PORT)
echo   - ล็อกอิน Facebook Inbox ในหน้าต่างที่ตรงกับพอร์ต FB (จาก FB_CHROME_DEBUG_PORT)
echo Then run: python line_oa_unread_messages.py หรือ python facebook_unread_messages.py
echo.
pause
