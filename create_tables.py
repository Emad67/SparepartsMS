import logging
import traceback
from app import create_app
from models import db

logging.basicConfig(level=logging.DEBUG)
app = create_app()
app.app_context().push()

try:
    print("Creating tables...")
    db.create_all()
    print("Tables created.")
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
