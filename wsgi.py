import webbrowser
from threading import Timer
from app import app

if __name__ == "__main__":
    Timer(1, lambda: webbrowser.open_new("http://127.0.0.1:5000/")).start()
    app.run()