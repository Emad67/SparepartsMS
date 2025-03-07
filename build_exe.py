import os
import shutil
import subprocess
import sys
from pathlib import Path

def run_command(command):
    print(f"Running: {command}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    stdout, stderr = process.communicate()
    
    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())
    
    return process.returncode

def main():
    print("Building Spare Parts Management System")
    print("=====================================")
    
    # Clean previous builds
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # Install PyInstaller if not already installed
    run_command(f"{sys.executable} -m pip install pyinstaller")
    
    # Build the executable
    run_command(f"{sys.executable} -m PyInstaller SparePartsMS.spec")
    
    # Create installer package
    installer_dir = Path("installer_package")
    installer_dir.mkdir(exist_ok=True)
    
    # Copy files to installer package
    dist_dir = installer_dir / "dist" / "SparePartsMS"
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    if os.path.exists("dist/SparePartsMS"):
        shutil.copytree("dist/SparePartsMS", str(dist_dir), dirs_exist_ok=True)
    
    # Copy additional files
    shutil.copy("LICENSE", installer_dir)
    shutil.copy("installer.iss", installer_dir)
    
    print("\nBuild completed!")
    print("\nNow you can:")
    print("1. Open installer.iss in Inno Setup Compiler")
    print("2. Click Compile to create the installer")

if __name__ == "__main__":
    main() 