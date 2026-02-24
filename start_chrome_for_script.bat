@echo off
set PORT=9222
netstat -an | findstr ":9222" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
  echo [Warning] Port %PORT% is already in use.
  echo   - If you already started Chrome for the script, do not run this .bat again.
  echo   - To start a new Chrome, close the one using this port first, or change PORT in this .bat
  pause
  exit /b 1
)
echo Starting Chrome for LINE OA script...
echo Log in to LINE OA in this Chrome, then run: python line_oa_unread_messages.py
echo.
set CHROME=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
if "%CHROME%"=="" (
  echo Chrome not found. Edit the path in this .bat file.
  pause
  exit /b 1
)
REM Use a separate profile so this is a NEW Chrome process that really listens on PORT.
REM If we don't, an already-running Chrome just opens a new window and ignores the port.
set DEBUG_PROFILE=%~dp0chrome_debug_profile
if not exist "%DEBUG_PROFILE%" mkdir "%DEBUG_PROFILE%"
start "" "%CHROME%" --remote-debugging-port=%PORT% --user-data-dir="%DEBUG_PROFILE%"
echo Chrome started on port %PORT% (profile: chrome_debug_profile) - must match CHROME_DEBUG_PORT in .env
echo Log in to LINE OA, then run the Python script.
echo.
pause
