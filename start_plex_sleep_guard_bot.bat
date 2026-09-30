@echo off
setlocal
for %%I in ("%~dp0.") do set "PROJECT_DIR=%%~fI"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python environment not found: "%PYTHON_EXE%"
    echo Create it with: py -3.12 -m venv .venv
    echo Then install the project with: .\.venv\Scripts\python.exe -m pip install -e .
    exit /b 1
)

set "RUN_DIR=%PROJECT_DIR%\run"
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" >nul 2>&1
if exist "%RUN_DIR%\stop.request" del /q "%RUN_DIR%\stop.request" >nul 2>&1
> "%RUN_DIR%\restart.request" echo restart
set "PLEX_SLEEP_GUARD_PROJECT_DIR=%PROJECT_DIR%"

powershell -NoProfile -Command "$project = $env:PLEX_SLEEP_GUARD_PROJECT_DIR; $supervisor = Join-Path $project 'supervise_plex_sleep_guard_bot.ps1'; $q = [char]34; $arguments = '-NoProfile -ExecutionPolicy Bypass -File ' + $q + $supervisor + $q + ' -ProjectDir ' + $q + $project + $q; Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WorkingDirectory $project -WindowStyle Hidden" >nul 2>&1
if errorlevel 1 (
    echo Could not start the bot supervisor.
    exit /b 1
)

echo Plex Sleep Guard Bot start or restart requested.
exit /b 0
