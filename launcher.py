import os
import sys
import subprocess
import webbrowser
import time
from threading import Thread

def run_flask():
    from app import app
    app.run(host='127.0.0.1', port=5000)

def main():
    print("Spare Parts Management System")
    print("Copyright © 2025 Aman Kflom and Nesredin Abdelrahim")
    print("=" * 50)

    # Create necessary directories
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('backups', exist_ok=True)

    # Start Flask application in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Wait for the server to start
    time.sleep(2)

    # Open web browser
    print("Starting application...")
    webbrowser.open('http://127.0.0.1:5000')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == '__main__':
    main() 