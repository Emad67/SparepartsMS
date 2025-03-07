@echo off
echo Spare Parts Management System Installer
echo Copyright (c) 2025 Aman Kflom and Nesredin Abdelrahim
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Create and activate virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller

REM Generate license
echo Generating license...
python license_generator.py

REM Create executable
echo Creating executable...
pyinstaller SparePartsMS.spec

REM Create desktop shortcut
echo Creating desktop shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Spare Parts MS.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%CD%\dist\SparePartsMS\SparePartsMS.exe" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%CD%\dist\SparePartsMS" >> CreateShortcut.vbs
echo oLink.Description = "Spare Parts Management System" >> CreateShortcut.vbs
echo oLink.IconLocation = "%CD%\static\favicon.ico" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo Installation completed successfully!
echo You can now run the application from the desktop shortcut.
echo.
pause 