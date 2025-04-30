@echo off
REM Activate your virtual environment (adjust path if needed)
call "%~dp0sparepart\Scripts\activate.bat"

REM Change directory to the project folder (where this script is)
cd /d "%~dp0"

REM Run your Flask app using wsgi.py
python wsgi.py

pause