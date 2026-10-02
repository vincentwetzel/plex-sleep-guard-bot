@echo off
setlocal
for %%I in ("%~dp0.") do set "PROJECT_DIR=%%~fI"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE="
    for /f "delims=" %%I in ('where.exe python.exe 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
)

if not defined PYTHON_EXE (
    echo Python was not found in .venv or on PATH.
    echo Install Python 3.12 or later, or create .venv with: py -3.12 -m venv .venv
    exit /b 1
)

"%PYTHON_EXE%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 or later is required. Found interpreter: "%PYTHON_EXE%"
    exit /b 1
)

if not exist "%PROJECT_DIR%\src\plex_sleep_guard_bot\__main__.py" (
    echo Bot entry point not found under: "%PROJECT_DIR%\src\plex_sleep_guard_bot"
    exit /b 1
)

"%PYTHON_EXE%" -c "import aiohttp, discord, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Required Python libraries are missing for: "%PYTHON_EXE%"
    echo Install them with: "%PYTHON_EXE%" -m pip install discord.py aiohttp python-dotenv
    exit /b 1
)

set "RUN_DIR=%PROJECT_DIR%\run"
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" >nul 2>&1
if exist "%RUN_DIR%\stop.request" del /q "%RUN_DIR%\stop.request" >nul 2>&1
> "%RUN_DIR%\restart.request" echo restart
set "PLEX_SLEEP_GUARD_PROJECT_DIR=%PROJECT_DIR%"
set "PLEX_SLEEP_GUARD_PYTHON_EXE=%PYTHON_EXE%"

powershell -NoProfile -Command "$project = $env:PLEX_SLEEP_GUARD_PROJECT_DIR; $supervisor = Join-Path $project 'supervise_plex_sleep_guard_bot.ps1'; $q = [char]34; $arguments = '-NoProfile -ExecutionPolicy Bypass -File ' + $q + $supervisor + $q + ' -ProjectDir ' + $q + $project + $q; Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WorkingDirectory $project -WindowStyle Hidden" >nul 2>&1
if errorlevel 1 (
    echo Could not start the bot supervisor.
    exit /b 1
)

echo Plex Sleep Guard Bot start or restart requested.
exit /b 0
