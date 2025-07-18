from app import create_app
from models import db, Transaction

app = create_app()

with app.app_context():
    print("=== CHECKING SALES LIST ===\n")
    
    # Get all sales transactions
    all_sales = Transaction.query.filter_by(type='sale').all()
    print(f"1. ALL SALES TRANSACTIONS (Total: {len(all_sales)}):")
    for sale in all_sales:
        print(f"   Sale ID: {sale.id}, Date: {sale.date}, Status: {sale.status}, Voided: {sale.voided}, Amount: {sale.price * sale.quantity}")
    
    # Get sales that should appear in the list (not cancelled, not voided)
    active_sales = Transaction.query.filter_by(type='sale').filter(
        ((Transaction.status == None) | (Transaction.status != 'cancelled')) & (Transaction.voided == False)
    ).all()
    
    print(f"\n2. SALES THAT SHOULD APPEAR IN LIST (Total: {len(active_sales)}):")
    for sale in active_sales:
        print(f"   Sale ID: {sale.id}, Date: {sale.date}, Status: {sale.status}, Voided: {sale.voided}, Amount: {sale.price * sale.quantity}")
    
    # Check for sales that are voided but still have null status
    problematic_sales = Transaction.query.filter_by(type='sale').filter(
        (Transaction.status == None) & (Transaction.voided == True)
    ).all()
    
    print(f"\n3. PROBLEMATIC SALES - VOIDED BUT NULL STATUS (Total: {len(problematic_sales)}):")
    for sale in problematic_sales:
        print(f"   Sale ID: {sale.id}, Date: {sale.date}, Status: {sale.status}, Voided: {sale.voided}, Amount: {sale.price * sale.quantity}")
    
    # Check for sales that have cancelled status but are not voided
    cancelled_not_voided = Transaction.query.filter_by(type='sale').filter(
        (Transaction.status == 'cancelled') & (Transaction.voided == False)
    ).all()
    
    print(f"\n4. CANCELLED BUT NOT VOIDED (Total: {len(cancelled_not_voided)}):")
    for sale in cancelled_not_voided:
        print(f"   Sale ID: {sale.id}, Date: {sale.date}, Status: {sale.status}, Voided: {sale.voided}, Amount: {sale.price * sale.quantity}")
    
    print("\n=== END CHECKING ===") 