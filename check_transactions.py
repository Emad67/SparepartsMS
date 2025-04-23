from app import create_app
from models import db, Transaction

app = create_app()
with app.app_context():
    # Get all transactions
    all_transactions = Transaction.query.all()
    print("\nAll transactions:")
    for t in all_transactions:
        print(f"ID: {t.id}, Type: {t.type}, Date: {t.date}, Status: {getattr(t, 'status', 'N/A')}")

    # Get sales transactions
    sales = Transaction.query.filter_by(type='sale').all()
    print("\nSales transactions:")
    for s in sales:
        print(f"ID: {s.id}, Date: {s.date}, Status: {getattr(s, 'status', 'N/A')}")

    # Get sales transactions excluding cancelled
    active_sales = Transaction.query.filter_by(type='sale').filter(Transaction.status != 'cancelled').all()
    print("\nActive sales transactions:")
    for s in active_sales:
        print(f"ID: {s.id}, Date: {s.date}, Status: {getattr(s, 'status', 'N/A')}") 