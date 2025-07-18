from app import create_app
from models import db, Transaction

app = create_app()

with app.app_context():
    print("=== FIXING VOIDED SALES STATUS ===\n")
    
    # Find sales that are voided but don't have status='cancelled' (including NULL status)
    problematic_sales = Transaction.query.filter_by(type='sale', voided=True).filter(
        (Transaction.status != 'cancelled') | (Transaction.status == None)
    ).all()
    
    print(f"Found {len(problematic_sales)} sales that are voided but don't have status='cancelled':")
    
    for sale in problematic_sales:
        print(f"   Sale ID: {sale.id}, Current Status: {sale.status}, Voided: {sale.voided}")
        # Fix the status
        sale.status = 'cancelled'
        print(f"   -> Fixed: Status set to 'cancelled'")
    
    if problematic_sales:
        db.session.commit()
        print(f"\nFixed {len(problematic_sales)} sales.")
    else:
        print("\nNo problematic sales found.")
    
    # Verify the fix
    print("\n=== VERIFICATION ===")
    voided_sales = Transaction.query.filter_by(type='sale', voided=True).all()
    print(f"All voided sales ({len(voided_sales)}):")
    for sale in voided_sales:
        print(f"   Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}")
    
    # Check what the sales list query returns now
    sales_list = Transaction.query.filter_by(type='sale').filter(
        ((Transaction.status == None) | (Transaction.status != 'cancelled')) & (Transaction.voided == False)
    ).all()
    print(f"\nSales list now returns {len(sales_list)} sales (should exclude voided ones)")
    
    print("\n=== FIX COMPLETE ===")