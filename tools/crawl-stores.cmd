@echo off
rem Crawl every store that is due (weekly by default). Meant for Windows Task Scheduler, see
rem docs\crawl-stores-task-scheduler.md. Safe to run every day: it exits in seconds when nothing is due.
rem Output is appended to backend\data\logs\crawl-stores.log; the exit code is passed through
rem (0 fine or nothing due, 1 a store failed, 2 a crawl needs a look).
setlocal
cd /d "%~dp0..\backend" || exit /b 1
if not exist "data\logs" mkdir "data\logs"
echo. >> "data\logs\crawl-stores.log"
echo ===== %date% %time% crawl-stores %* ===== >> "data\logs\crawl-stores.log"
".venv\Scripts\python.exe" -m app.cli crawl-stores %* >> "data\logs\crawl-stores.log" 2>&1
exit /b %ERRORLEVEL%
