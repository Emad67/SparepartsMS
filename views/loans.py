from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Loan, Customer, Part, BinCard, WarehouseStock, Warehouse, Transaction, FinancialTransaction, ExchangeRate, LoanPayment
from datetime import datetime, timedelta
from sqlalchemy import and_
from utils.date_utils import parse_date_range, format_date
from utils.template_filters import format_price_nkf
from utils.currency import get_usd_amount
import pytz

nairobi_tz = pytz.timezone('Africa/Nairobi')
now_asmara = datetime.now(nairobi_tz)

loans = Blueprint('loans', __name__)

@loans.route('/loans')
@login_required
def list_loans():
    # Get filter parameters
    customer_id = request.args.get('customer_id', type=int)
    due_date_start = request.args.get('due_date_start')
    due_date_end = request.args.get('due_date_end')
    
    # Base query
    query = Loan.query.join(Part).join(Customer)
    
    # Apply filters
    if customer_id:
        query = query.filter(Loan.customer_id == customer_id)
    
    # Parse date range
    if due_date_start or due_date_end:
        start_datetime, end_datetime = parse_date_range(due_date_start, due_date_end)
        query = query.filter(
            Loan.due_date >= start_datetime,
            Loan.due_date <= end_datetime
        )
    
    # Get all customers for the filter dropdown
    customers = Customer.query.order_by(Customer.name).all()
    
    # Get all active warehouses for the sale conversion modal
    warehouses = Warehouse.query.order_by(Warehouse.name).all()
    
    # Execute query and order by loan date
    loans = query.order_by(Loan.loan_date.desc()).all()
    
    return render_template('loans/list.html', 
                         loans=loans,
                         customers=customers,
                         warehouses=warehouses,
                         selected_customer_id=customer_id,
                         due_date_start=format_date(start_datetime) if due_date_start else None,
                         due_date_end=format_date(end_datetime) if due_date_end else None)

@loans.route('/loans/add', methods=['GET', 'POST'])
@login_required
def add_loan():
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        part_id = request.form.get('part_id')
        quantity = int(request.form.get('quantity'))
        days = int(request.form.get('days', 30))
        price = request.form.get('price', type=float)
        selling_price = request.form.get('selling_price', type=float)
        warehouse_id = request.form.get('warehouse_id', type=int)
        warehouse = Warehouse.query.get_or_404(warehouse_id)
        
        
        # Check if enough total stock is available
        part = Part.query.get_or_404(part_id)
        if part.stock_level < quantity:
            flash('Not enough stock available', 'error')
            return redirect(url_for('loans.add_loan'))
        
        loan = Loan(
            customer_id=customer_id,
            part_id=part_id,
            quantity=quantity,
            loan_date=datetime.now(pytz.timezone('Africa/Nairobi')),
            due_date=datetime.now(pytz.timezone('Africa/Nairobi')) + timedelta(days=days),
            status='active',
            price=price,
            selling_price=selling_price
        )
        
        # Add loan to get its ID
        db.session.add(loan)
        db.session.flush()
        
        # Update part's total stock level
        part.stock_level -= quantity
        # Get the warehouse
        warehouse = Warehouse.query.get_or_404(warehouse_id)

        # Update the stock level in the warehouse
        warehouse_stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_id,
            part_id=part_id
        ).first()

        if not warehouse_stock:
            flash('No stock record for this part in the selected warehouse. Please check your selection or add stock to this warehouse.', 'error')
            return redirect(url_for('loans.add_loan'))
        if warehouse_stock.quantity < quantity:
            flash('Insufficient stock in the selected warehouse. Please adjust the quantity or choose another warehouse.', 'error')
            return redirect(url_for('loans.add_loan'))
    
    
        warehouse_stock.quantity -= quantity
        
        # Create bincard entry for the loan
        bincard = BinCard(
            part_id=part_id,
            transaction_type='out',
            quantity=quantity,
            reference_type='loan',
            reference_id=loan.id,
            balance=part.stock_level,
            user_id=current_user.id,
            notes=f'Loan to {loan.customer.name} for {days} days from {warehouse.name}'
        )
        
        db.session.add(bincard)
        db.session.commit()
        flash('Loan created successfully')
        return redirect(url_for('loans.list_loans'))
        
    customers = Customer.query.all()
    parts = Part.query.filter(Part.stock_level > 0).all()
    warehouses = Warehouse.query.order_by(Warehouse.name).all()
    default_warehouse_id = None
    if warehouses:
        default_warehouse_id = min(warehouses, key=lambda w: w.id).id
    return render_template('loans/add.html', customers=customers, parts=parts, warehouses=warehouses, default_warehouse_id=default_warehouse_id)

@loans.route('/loans/<int:id>/return', methods=['POST'])
@login_required
def return_loan(id):
    loan = Loan.query.get_or_404(id)
    if loan.status != 'active':
        flash('This loan is already returned or expired')
        return redirect(url_for('loans.list_loans'))
        
    loan.status = 'returned'
    loan.returned_date = datetime.now(pytz.timezone('Africa/Nairobi'))
    
    # Return stock to the warehouse it was taken from
    # Find the most recent bincard entry for this loan to get the warehouse info
    bincard = BinCard.query.filter_by(
        reference_type='loan',
        reference_id=loan.id
    ).first()
    
    if bincard:
        # Extract warehouse name from the notes
        import re
        warehouse_match = re.search(r'from (.+)$', bincard.notes)
        if warehouse_match:
            warehouse_name = warehouse_match.group(1)
            warehouse = Warehouse.query.filter_by(name=warehouse_name).first()
            if warehouse:
                warehouse_stock = WarehouseStock.query.filter_by(
                    warehouse_id=warehouse.id,
                    part_id=loan.part_id
                ).first()
                
                if warehouse_stock:
                    warehouse_stock.quantity += loan.quantity
                else:
                    warehouse_stock = WarehouseStock(
                        warehouse_id=warehouse.id,
                        part_id=loan.part_id,
                        quantity=loan.quantity
                    )
                    db.session.add(warehouse_stock)
    
    # Update total stock level
    part = Part.query.get(loan.part_id)
    part.stock_level += loan.quantity
    
    db.session.commit()
    flash('Loan marked as returned')
    return redirect(url_for('loans.list_loans'))

@loans.route('/loans/<int:id>/convert-to-sale', methods=['POST'])
@login_required
def convert_to_sale(id):
    """Convert a loan to a sale"""
    try:
        data = request.json
        if not data or 'price' not in data or 'warehouse_id' not in data:
            return jsonify({'error': 'Price and warehouse are required'}), 400
            
        price_nkf = float(data['price']) # Price in NKF
        warehouse_id = int(data['warehouse_id'])
        loan = Loan.query.get_or_404(id)
        
        if loan.status != 'active':
            return jsonify({'error': 'This loan is not active'}), 400
            
        # Convert NKF to USD using the utility function
       # try:
       #     price_usd = get_usd_amount(price_nkf)
       # except ValueError as e:
       #     return jsonify({'error': str(e)}), 400
        
        # Create sale transaction
        sale = Transaction(
            part_id=loan.part_id,
            type='sale',
            quantity=loan.quantity,
            price=price_nkf,  # Store price in NKF
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            user_id=current_user.id
        )

        # Add the sale to get its ID
        db.session.add(sale)
        db.session.flush()
        
        # Update loan status
        loan.status = 'sold'
        loan.returned_date = datetime.now(pytz.timezone('Africa/Nairobi'))
        
        # # Get the warehouse
        warehouse = Warehouse.query.get_or_404(warehouse_id)
        
        # # Update the stock level in the warehouse
        warehouse_stock = WarehouseStock.query.filter_by(
           warehouse_id=warehouse_id,
           part_id=loan.part_id
         ).first()

        # if not warehouse_stock or warehouse_stock.quantity < loan.quantity:
        #return jsonify({'error': 'Insufficient stock in the warehouse'}), 400

        #warehouse_stock.quantity -= loan.quantity

        # Fetch the current stock balance for the part
        part = Part.query.get(loan.part_id)
        current_balance = part.stock_level if part else 0
        
        # Create bincard entry for the sale
        bincard = BinCard(
            part_id=loan.part_id,
            transaction_type='out',
            quantity=loan.quantity,  # Reflect the quantity sold
            reference_type='sale',
            reference_id=sale.id,
            balance=current_balance,  # Use the current part stock level
            user_id=current_user.id,
            notes=f'Converted loan #{loan.id} to sale at NKF {price_nkf:,.2f} per unit'
        )
        
        
        # Calculate the total amount in NKF
        total_amount_nkf = price_nkf * loan.quantity

        # Create financial transaction for the sale
        financial_transaction = FinancialTransaction(
            type='revenue',
            category='Sales',
            amount=total_amount_nkf,  # Total amount in NKF
            exchange_rate=ExchangeRate.get_rate_for_date(),  # Add exchange rate
            description=f'Loan #{loan.id} converted to sale: {loan.quantity} units at NKF {price_nkf} per unit in {warehouse.name}',
            reference_id=str(sale.id),
            user_id=current_user.id,
            date=datetime.now(pytz.timezone('Africa/Nairobi'))
        )
        
        db.session.add(bincard)
        db.session.add(financial_transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Loan successfully converted to sale'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@loans.route('/api/warehouse-stock')
@login_required
def get_warehouse_stock():
    part_id = request.args.get('part_id', type=int)
    warehouse_id = request.args.get('warehouse_id', type=int)
    
    if not part_id or not warehouse_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    stock = WarehouseStock.query.filter_by(
        part_id=part_id,
        warehouse_id=warehouse_id
    ).first()
    
    return jsonify({
        'quantity': stock.quantity if stock else 0
    })

@loans.route('/loans/create', methods=['POST'])
@login_required
def create_loan():
    try:
        part_id = request.form.get('part_id', type=int)
        part = Part.query.get_or_404(part_id)
        
        loan = Loan(
            part_id=part_id,
            price=part.price,  # Get price from the part
            # ... other fields ...
        )
        
        db.session.add(loan)
        db.session.commit()
        flash('Loan created successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error creating loan: ' + str(e), 'error')
        
    return redirect(url_for('loans.list_loans'))

@loans.route('/loans/<int:loan_id>/add-payment', methods=['POST'])
@login_required
def add_loan_payment(loan_id):
    amount = float(request.form['amount'])
    method = request.form['method']
    notes = request.form.get('notes', '')
    payment = LoanPayment(loan_id=loan_id, amount=amount, method=method, notes=notes)
    db.session.add(payment)
    db.session.flush()  # So payment.id is available if needed

    loan = Loan.query.get_or_404(loan_id)

    # Calculate quantity paid for this payment
    quantity_paid = 0
    if loan.selling_price:
        quantity_paid = round(amount / loan.selling_price, 2)

    # Create a Transaction for this payment
    sale = Transaction(
        part_id=loan.part_id,
        type='sale',
        quantity=1,  # Track how much of the loan is paid off in units
        price=amount,
        date=datetime.now(pytz.timezone('Africa/Nairobi')),
        user_id=current_user.id,
        payment_method=method,
        notes=notes
    )
    db.session.add(sale)
    db.session.flush()

    # Create a FinancialTransaction for this payment
    financial_transaction = FinancialTransaction(
        type='revenue',
        category='Loan Payment',
        amount=amount,
        exchange_rate=ExchangeRate.get_rate_for_date(),
        description=f'Partial payment for Loan #{loan.id}: {amount} NKF, method: {method}',
        reference_id=str(sale.id),
        user_id=current_user.id,
        date=datetime.now(pytz.timezone('Africa/Nairobi'))
    )
    db.session.add(financial_transaction)

    db.session.commit()
    flash('Payment recorded successfully!', 'success')
    return redirect(url_for('loans.loan_status', loan_id=loan_id))

@loans.route('/loans/<int:loan_id>/status')
@login_required
def loan_status(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    total_amount = loan.quantity * (loan.selling_price or 0)
    print(total_amount)
    total_paid = sum(payment.amount for payment in loan.payments)
    outstanding_amount = total_amount - total_paid
    return render_template('loans/status.html', 
                         loan=loan, 
                         total_paid=total_paid,
                         total_amount=total_amount,
                         outstanding_amount=outstanding_amount)