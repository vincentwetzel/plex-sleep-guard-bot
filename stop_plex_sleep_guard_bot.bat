@echo off
setlocal
for %%I in ("%~dp0.") do set "PROJECT_DIR=%%~fI"
set "RUN_DIR=%PROJECT_DIR%\run"
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" >nul 2>&1
> "%RUN_DIR%\stop.request" echo stop

echo Plex Sleep Guard Bot stop requested.
echo The bot will clear its power request and exit through its shutdown cleanup.
exit /b 0
