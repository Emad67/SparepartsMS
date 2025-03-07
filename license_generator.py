#!/usr/bin/env python3
import hashlib
import platform
import uuid
import os
import sys
from datetime import datetime

def get_hardware_id():
    """Generate a unique hardware ID for the current machine"""
    system_info = platform.uname()
    mac = uuid.getnode()
    return hashlib.sha256(f"{system_info.node}{mac}".encode()).hexdigest()

def generate_license():
    """Generate a license file for the current machine"""
    hardware_id = get_hardware_id()
    
    try:
        with open('.license', 'w') as f:
            f.write(hardware_id)
        print("License generated successfully!")
        print("Hardware ID:", hardware_id)
        print("\nThis license is valid only for this machine.")
        print("To generate a license for another machine, run this script on that machine.")
    except Exception as e:
        print("Error generating license:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    print("Spare Parts Management System - License Generator")
    print("Copyright © 2025 Aman Kflom and Nesredin Abdelrahim")
    print("=" * 50)
    
    if not os.path.exists('.license'):
        response = input("Generate license for this machine? (y/n): ")
        if response.lower() == 'y':
            generate_license()
        else:
            print("License generation cancelled.")
    else:
        print("A license file already exists.")
        response = input("Do you want to regenerate the license? (y/n): ")
        if response.lower() == 'y':
            generate_license()
        else:
            print("License generation cancelled.") 