@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate
python backend\app.py
pause
