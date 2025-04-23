from app import create_app
from models import db, Transaction

app = create_app()
with app.app_context():
    # Update all transactions that don't have a status
    transactions = Transaction.query.filter(Transaction.status == None).all()
    for t in transactions:
        t.status = 'active'
        db.session.add(t)
    
    db.session.commit()
    print(f"Updated {len(transactions)} transactions to have 'active' status") 