from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CreditPurchase, Supplier, Part, BinCard, WarehouseStock, Warehouse, FinancialTransaction
from datetime import datetime, timedelta
from sqlalchemy import and_

credits = Blueprint('credits', __name__)

@credits.route('/credits')
@login_required
def list_credits():
    # Get filter parameters
    supplier_id = request.args.get('supplier_id', type=int)
    due_date_start = request.args.get('due_date_start')
    due_date_end = request.args.get('due_date_end')
    
    # Base query
    query = CreditPurchase.query.join(Part).join(Supplier)
    
    # Apply filters
    if supplier_id:
        query = query.filter(CreditPurchase.supplier_id == supplier_id)
    if due_date_start:
        query = query.filter(CreditPurchase.due_date >= due_date_start)
    if due_date_end:
        query = query.filter(CreditPurchase.due_date <= due_date_end)
    
    # Get all suppliers for the filter dropdown
    suppliers = Supplier.query.order_by(Supplier.name).all()
    
    # Execute query and order by purchase date
    credits = query.order_by(CreditPurchase.purchase_date.desc()).all()
    
    return render_template('credits/list.html', 
                         credits=credits,
                         suppliers=suppliers,
                         selected_supplier_id=supplier_id,
                         due_date_start=due_date_start,
                         due_date_end=due_date_end)

@credits.route('/credits/add', methods=['GET', 'POST'])
@login_required
def add_credit():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        part_id = request.form.get('part_id')
        warehouse_id = request.form.get('warehouse_id')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))
        days = int(request.form.get('days', 30))
        total_amount = price * quantity
        
        credit = CreditPurchase(
            supplier_id=supplier_id,
            part_id=part_id,
            quantity=quantity,
            price=price,
            purchase_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=days),
            status='pending'
        )
        
        # Add credit purchase and flush to get its ID
        db.session.add(credit)
        db.session.flush()
        
        # Create financial transaction for the credit purchase
        financial_transaction = FinancialTransaction(
            type='expense',
            category='Credit Purchase',
            amount=total_amount,
            description=f'Credit purchase of {quantity} units of part ID {part_id} at ${price} per unit',
            reference_id=str(credit.id),
            user_id=current_user.id,
            date=datetime.utcnow()
        )
        db.session.add(financial_transaction)
        
        # Update warehouse stock
        warehouse_stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_id,
            part_id=part_id
        ).first()
        
        if warehouse_stock:
            warehouse_stock.quantity += quantity
        else:
            warehouse_stock = WarehouseStock(
                warehouse_id=warehouse_id,
                part_id=part_id,
                quantity=quantity
            )
            db.session.add(warehouse_stock)
        
        # Update part's total stock level
        part = Part.query.get(part_id)
        part.stock_level += quantity
        
        # Create bincard entry for the credit purchase
        bincard = BinCard(
            part_id=part_id,
            transaction_type='in',
            quantity=quantity,
            reference_type='credit_purchase',
            reference_id=credit.id,
            balance=part.stock_level,
            user_id=current_user.id,
            notes=f'Credit purchase at ${price} per unit in {warehouse_stock.warehouse.name}'
        )
        
        db.session.add(bincard)
        db.session.commit()
        flash('Credit purchase created successfully')
        return redirect(url_for('credits.list_credits'))
        
    suppliers = Supplier.query.all()
    parts = Part.query.all()
    warehouses = Warehouse.query.all()
    return render_template('credits/add.html', 
                         suppliers=suppliers, 
                         parts=parts,
                         warehouses=warehouses)

@credits.route('/credits/<int:id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(id):
    credit = CreditPurchase.query.get_or_404(id)
    
    if credit.status == 'paid':
        flash('This credit purchase is already marked as paid', 'warning')
        return redirect(url_for('credits.list_credits'))
    
    credit.status = 'paid'
    
    # Create financial transaction for the payment
    total_amount = credit.price * credit.quantity
    financial_transaction = FinancialTransaction(
        type='expense',
        category='Credit Payment',
        amount=total_amount,
        description=f'Payment for credit purchase #{credit.id}: {credit.quantity} units at ${credit.price} per unit',
        reference_id=str(credit.id),
        user_id=current_user.id,
        date=datetime.utcnow()
    )
    db.session.add(financial_transaction)
    
    db.session.commit()
    flash('Credit purchase marked as paid')
    return redirect(url_for('credits.list_credits')) 