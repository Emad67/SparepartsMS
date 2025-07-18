from app import create_app
from models import db, Transaction, FinancialTransaction

app = create_app()

with app.app_context():
    print("=== DEBUGGING VOIDING ISSUE ===\n")
    
    # Check all financial transactions
    print("1. ALL FINANCIAL TRANSACTIONS:")
    all_financial = FinancialTransaction.query.all()
    for ft in all_financial:
        print(f"   FT ID: {ft.id}, Category: '{ft.category}', Type: {ft.type}, Amount: {ft.amount}, Reference: {ft.reference_id}, Voided: {ft.voided}")
    
    print(f"\n   Total financial transactions: {len(all_financial)}")
    
    # Check sales-related financial transactions
    print("\n2. SALES-RELATED FINANCIAL TRANSACTIONS:")
    sales_categories = ['sale', 'sales', 'parts sale', 'parts sales', 'part sales', 'Sales']
    sales_financial = FinancialTransaction.query.filter(
        FinancialTransaction.category.in_(sales_categories)
    ).all()
    
    for ft in sales_financial:
        print(f"   FT ID: {ft.id}, Category: '{ft.category}', Type: {ft.type}, Amount: {ft.amount}, Reference: {ft.reference_id}, Voided: {ft.voided}")
        
        # Check if the referenced sale exists
        if ft.reference_id:
            try:
                sale_id = int(ft.reference_id)
                sale = Transaction.query.get(sale_id)
                if sale:
                    print(f"      -> Referenced Sale ID: {sale.id}, Status: {sale.status}, Voided: {sale.voided}")
                else:
                    print(f"      -> Referenced Sale ID {sale_id} NOT FOUND")
            except ValueError:
                print(f"      -> Invalid reference ID: {ft.reference_id}")
    
    print(f"\n   Total sales financial transactions: {len(sales_financial)}")
    
    # Check voided financial transactions
    print("\n3. VOIDED FINANCIAL TRANSACTIONS:")
    voided_financial = FinancialTransaction.query.filter_by(voided=True).all()
    for ft in voided_financial:
        print(f"   FT ID: {ft.id}, Category: '{ft.category}', Type: {ft.type}, Amount: {ft.amount}, Reference: {ft.reference_id}")
    
    print(f"\n   Total voided financial transactions: {len(voided_financial)}")
    
    # Test the category matching logic
    print("\n4. TESTING CATEGORY MATCHING:")
    for ft in all_financial:
        category_lower = ft.category.strip().lower() if ft.category else ''
        matches = category_lower in ['sale', 'sales', 'parts sale', 'parts sales', 'part sales']
        print(f"   FT ID: {ft.id}, Category: '{ft.category}' -> Lower: '{category_lower}' -> Matches: {matches}")
    
    print("\n=== END DEBUGGING ===") 