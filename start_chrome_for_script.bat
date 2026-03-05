@echo off
setlocal EnableDelayedExpansion
REM รันครั้งเดียว: อ่าน LINE_OA_PORTS หรือ CHROME_DEBUG_PORT จาก .env แล้วเปิด Chrome ตามจำนวน port
REM ถ้าไม่พบ .env หรือไม่กำหนด port = เปิดแค่ port 9222 (โปรไฟล์เดียว)
REM Usage: start_chrome_for_script.bat
REM        หรือส่งตัวเลข slot อย่างเดียว: start_chrome_for_script.bat 2 (เปิดแค่บัญชีที่ 2)

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%" 2>nul || exit /b 1

REM โหลด LINE_OA_PORTS และ CHROME_DEBUG_PORT จาก .env
set "LINE_OA_PORTS="
set "CHROME_DEBUG_PORT="
if exist ".env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    set "key=%%a"
    set "key=!key: =!"
    if "!key!"=="LINE_OA_PORTS" set "LINE_OA_PORTS=%%b"
    if "!key!"=="CHROME_DEBUG_PORT" set "CHROME_DEBUG_PORT=%%b"
  )
)

REM รายการ port: ใช้ LINE_OA_PORTS ถ้ามี ไม่ก็ CHROME_DEBUG_PORT
set "PORTS_RAW=!LINE_OA_PORTS!"
if "!PORTS_RAW!"=="" set "PORTS_RAW=!CHROME_DEBUG_PORT!"
if "!PORTS_RAW!"=="" set "PORTS_RAW=9222"
REM ลบช่องว่าง และ carriage return ที่อาจมาจาก .env
set "PORTS_RAW=!PORTS_RAW: =!"
if not "!PORTS_RAW:~-1!"=="" if "!PORTS_RAW:~-1!" lss "0" set "PORTS_RAW=!PORTS_RAW:~0,-1!"
if not "!PORTS_RAW:~-1!"=="" if "!PORTS_RAW:~-1!" gtr "9" set "PORTS_RAW=!PORTS_RAW:~0,-1!"

REM ถ้ารันด้วย argument ตัวเลข = เปิดแค่ slot นั้น
if not "%~1"=="" (
  set "SLOT=%~1"
  set /a "PORT=9221+!SLOT!" 2>nul
  if defined PORT set "PORTS_RAW=!PORT!"
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
REM วนตาม port โดยแยกจาก PORTS_RAW ด้วย comma (ทีละตัว)
:port_loop
if "!PORTS_RAW!"=="" goto :port_loop_done
for /f "tokens=1,* delims=," %%a in ("!PORTS_RAW!") do (
  set "CURPORT=%%a"
  set "PORTS_RAW=%%b"
)
set "CURPORT=!CURPORT: =!"
REM เอา CR ออกถ้าตัวสุดท้ายไม่ใช่ตัวเลข
if not "!CURPORT:~-1!"=="" if "!CURPORT:~-1!" lss "0" set "CURPORT=!CURPORT:~0,-1!"
if not "!CURPORT:~-1!"=="" if "!CURPORT:~-1!" gtr "9" set "CURPORT=!CURPORT:~0,-1!"
if not "!PORTS_RAW!"=="" if "!PORTS_RAW:~-1!" lss "0" set "PORTS_RAW=!PORTS_RAW:~0,-1!"
if not "!PORTS_RAW!"=="" if "!PORTS_RAW:~-1!" gtr "9" set "PORTS_RAW=!PORTS_RAW:~0,-1!"
if "!CURPORT!"=="" goto :port_loop

set /a "SLOT=!CURPORT!-9221" 2>nul
if !SLOT! LSS 1 set SLOT=1
if !SLOT! equ 1 (
  set "DEBUG_PROFILE_NAME=chrome_debug_profile"
) else (
  set "DEBUG_PROFILE_NAME=chrome_debug_profile_!SLOT!"
)
set "DEBUG_PROFILE=!SCRIPT_DIR!\!DEBUG_PROFILE_NAME!"

netstat -an | findstr ":!CURPORT!" | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
  echo [Warning] Port !CURPORT! is already in use. Skip.
) else (
  if not exist "!DEBUG_PROFILE!" mkdir "!DEBUG_PROFILE!"
  start "" "!CHROME!" --remote-debugging-port=!CURPORT! --user-data-dir="!DEBUG_PROFILE!"
  echo Chrome started: port !CURPORT!, profile !DEBUG_PROFILE_NAME!
  set /a OPENED+=1
  timeout /t 1 /nobreak >nul 2>&1
)
goto :port_loop
:port_loop_done

if %OPENED% equ 0 (
  echo No Chrome started. All ports may be in use.
  pause
  exit /b 1
)

echo.
echo Started %OPENED% Chrome profile(s). Log in to LINE OA in each window.
echo Then run: python line_oa_unread_messages.py --report-format summary-once
echo (ใช้ LINE_OA_URL และ LINE_OA_PORTS ใน .env ให้สอดคล้องกัน)
echo.
pause
