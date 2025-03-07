@echo off
echo Creating Spare Parts Management System Installer Package
echo ====================================================
echo.

REM Create installer package directory
mkdir installer_package 2>nul
cd installer_package

REM Copy necessary files
echo Copying files...
xcopy /E /I /Y ..\templates templates
xcopy /E /I /Y ..\static static
xcopy /E /I /Y ..\migrations migrations
copy ..\*.py .
copy ..\*.txt .
copy ..\*.spec .
copy ..\*.bat .
copy ..\*.iss .
copy ..\LICENSE .

REM Create dist and build directories
mkdir dist 2>nul
mkdir build 2>nul

echo.
echo Installer package created successfully in the installer_package directory.
echo.
echo To create the installer:
echo 1. Copy the installer_package directory to the target machine
echo 2. Run install.bat to install using the batch installer
echo   OR
echo 3. Use Inno Setup to compile installer.iss for a professional installer
echo.
pause