@echo off
echo Building Spare Parts Management System
echo ====================================
echo.

REM Create a clean build environment
rmdir /S /Q build_env 2>nul
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul

REM Create and activate virtual environment
python -m venv build_env
call build_env\Scripts\activate.bat

REM Install requirements
pip install -r requirements.txt
pip install pyinstaller

REM Create the executable
python -m PyInstaller SparePartsMS.spec

REM Create the installer package
mkdir installer_package 2>nul
xcopy /E /I /Y dist\SparePartsMS installer_package\dist\SparePartsMS
copy LICENSE installer_package\
copy installer.iss installer_package\

echo.
echo Build completed!
echo.
echo Now you can:
echo 1. Open installer.iss in Inno Setup Compiler
echo 2. Click Compile to create the installer
echo.
pause 