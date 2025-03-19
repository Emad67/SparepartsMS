from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Loan, Customer, Part, BinCard, WarehouseStock, Warehouse, Transaction, FinancialTransaction
from datetime import datetime, timedelta
from sqlalchemy import and_
from utils.date_utils import parse_date_range, format_date

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
        
        # Check if enough total stock is available
        part = Part.query.get_or_404(part_id)
        if part.stock_level < quantity:
            flash('Not enough stock available', 'error')
            return redirect(url_for('loans.add_loan'))
        
        loan = Loan(
            customer_id=customer_id,
            part_id=part_id,
            quantity=quantity,
            loan_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=days),
            status='active'
        )
        
        # Add loan to get its ID
        db.session.add(loan)
        db.session.flush()
        
        # Update part's total stock level
        part.stock_level -= quantity
        
        # Create bincard entry for the loan
        bincard = BinCard(
            part_id=part_id,
            transaction_type='out',
            quantity=quantity,
            reference_type='loan',
            reference_id=loan.id,
            balance=part.stock_level,
            user_id=current_user.id,
            notes=f'Loan to {loan.customer.name} for {days} days'
        )
        
        db.session.add(bincard)
        db.session.commit()
        flash('Loan created successfully')
        return redirect(url_for('loans.list_loans'))
        
    customers = Customer.query.all()
    parts = Part.query.filter(Part.stock_level > 0).all()
    return render_template('loans/add.html', 
                         customers=customers, 
                         parts=parts)

@loans.route('/loans/<int:id>/return', methods=['POST'])
@login_required
def return_loan(id):
    loan = Loan.query.get_or_404(id)
    if loan.status != 'active':
        flash('This loan is already returned or expired')
        return redirect(url_for('loans.list_loans'))
        
    loan.status = 'returned'
    loan.returned_date = datetime.utcnow()
    
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
            
        price = float(data['price'])
        warehouse_id = int(data['warehouse_id'])
        loan = Loan.query.get_or_404(id)
        
        if loan.status != 'active':
            return jsonify({'error': 'This loan is not active'}), 400
            
        # Create sale transaction
        sale = Transaction(
            part_id=loan.part_id,
            type='sale',
            quantity=loan.quantity,
            price=price,
            date=datetime.utcnow(),
            user_id=current_user.id
        )
        
        # Add the sale to get its ID
        db.session.add(sale)
        db.session.flush()
        
        # Update loan status
        loan.status = 'sold'
        loan.returned_date = datetime.utcnow()
        
        # Get the warehouse
        warehouse = Warehouse.query.get_or_404(warehouse_id)
        
        # Create bincard entry for the sale
        bincard = BinCard(
            part_id=loan.part_id,
            transaction_type='out',
            quantity=0,  # No additional stock movement, just status change
            reference_type='sale',
            reference_id=sale.id,
            balance=loan.part.stock_level,  # Stock level remains the same
            user_id=current_user.id,
            notes=f'Converted loan #{loan.id} to sale at ${price} per unit in {warehouse.name}'
        )
        
        # Create financial transaction for the sale
        total_amount = price * loan.quantity
        financial_transaction = FinancialTransaction(
            type='revenue',
            category='Sales',
            amount=total_amount,
            description=f'Loan #{loan.id} converted to sale: {loan.quantity} units at ${price} per unit in {warehouse.name}',
            reference_id=str(sale.id),
            user_id=current_user.id,
            date=datetime.utcnow()
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