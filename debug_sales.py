from app import create_app
from models import db, Transaction, FinancialTransaction

app = create_app()

with app.app_context():
    print("=== DEBUGGING SALES VOIDING ISSUE ===\n")
    
    # Check all sales
    print("1. ALL SALES IN DATABASE:")
    all_sales = Transaction.query.filter_by(type='sale').all()
    for sale in all_sales:
        print(f"   Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}, Date: {sale.date}")
    
    print(f"\n   Total sales: {len(all_sales)}")
    
    # Check voided sales
    print("\n2. VOIDED SALES:")
    voided_sales = Transaction.query.filter_by(type='sale', voided=True).all()
    for sale in voided_sales:
        print(f"   Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}")
        print(f"      Status == 'cancelled': {sale.status == 'cancelled'}")
        print(f"      Status != 'cancelled': {sale.status != 'cancelled'}")
    
    print(f"\n   Total voided sales: {len(voided_sales)}")
    
    # Check cancelled sales
    print("\n3. CANCELLED SALES:")
    cancelled_sales = Transaction.query.filter_by(type='sale', status='cancelled').all()
    for sale in cancelled_sales:
        print(f"   Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}")
    
    print(f"\n   Total cancelled sales: {len(cancelled_sales)}")
    
    # Check what the sales list query would return
    print("\n4. WHAT SALES LIST QUERY RETURNS:")
    sales_list_query = Transaction.query.filter_by(type='sale').filter(
        ((Transaction.status == None) | (Transaction.status != 'cancelled')) & (Transaction.voided == False)
    )
    sales_list = sales_list_query.all()
    for sale in sales_list:
        print(f"   Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}")
    
    print(f"\n   Total sales in list: {len(sales_list)}")
    
    # Check financial transactions
    print("\n5. FINANCIAL TRANSACTIONS RELATED TO SALES:")
    sales_financial = FinancialTransaction.query.filter(
        FinancialTransaction.category.in_(['sale', 'sales', 'parts sale', 'parts sales', 'part sales'])
    ).all()
    for ft in sales_financial:
        print(f"   FT ID: {ft.id}, Category: {ft.category}, Amount: {ft.amount}, Reference: {ft.reference_id}, Voided: {ft.voided}")
    
    print(f"\n   Total sales financial transactions: {len(sales_financial)}")
    
    print("\n=== END DEBUGGING ===")