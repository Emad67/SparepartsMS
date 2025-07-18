from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== FIXING VOIDED SALES WITH DIRECT SQL ===\n")
    
    # Use direct SQL to update all voided sales
    try:
        # Update all voided sales to have status='cancelled'
        result = db.session.execute(
            text("UPDATE transaction SET status = 'cancelled' WHERE type = 'sale' AND voided = 1")
        )
        db.session.commit()
        
        print(f"Updated {result.rowcount} sales")
        
        # Verify the fix
        print("\n=== VERIFICATION ===")
        voided_sales = db.session.execute(
            text("SELECT id, status, voided FROM transaction WHERE type = 'sale' AND voided = 1")
        ).fetchall()
        
        print(f"All voided sales ({len(voided_sales)}):")
        for sale in voided_sales:
            print(f"   Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}")
        
        # Check what the sales list query returns now
        sales_list = db.session.execute(
            text("""SELECT id, status, voided FROM transaction 
               WHERE type = 'sale' 
               AND ((status IS NULL OR status != 'cancelled') AND voided = 0)""")
        ).fetchall()
        
        print(f"\nSales list now returns {len(sales_list)} sales (should exclude voided ones)")
        
        print("\n=== FIX COMPLETE ===")
        
    except Exception as e:
        print(f"Error: {e}")
        db.session.rollback()