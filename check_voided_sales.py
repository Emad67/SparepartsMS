from app import create_app
from models import db, Transaction

app = create_app()
with app.app_context():
    print("Sales transactions with price 455.00 NKF:")
    sales = Transaction.query.filter_by(type='sale').filter(Transaction.price == 455.00).all()
    for s in sales:
        print(f"ID: {s.id}, Price: {s.price}, Status: {s.status}, Voided: {s.voided}")
    print("\nAll sales transactions:")
    all_sales = Transaction.query.filter_by(type='sale').all()
    for s in all_sales:
        print(f"ID: {s.id}, Price: {s.price}, Status: {s.status}, Voided: {s.voided}") 