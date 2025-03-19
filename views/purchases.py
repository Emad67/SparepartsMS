from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Purchase, Part, Supplier, FinancialTransaction, BinCard, Warehouse, WarehouseStock
from datetime import datetime
from views.utils import role_required
from sqlalchemy.exc import SQLAlchemyError

purchases = Blueprint('purchases', __name__)

@purchases.route('/purchases')
@login_required
@role_required('admin', 'manager')
def list_purchases():
    purchases = Purchase.query.order_by(Purchase.purchase_date.desc()).all()
    return render_template('purchases/list.html', purchases=purchases)

@purchases.route('/purchases/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_purchase():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        supplier_id = request.form.get('supplier_id')
        warehouse_id = request.form.get('warehouse_id')
        quantity = int(request.form.get('quantity'))
        unit_cost = float(request.form.get('unit_cost'))
        total_cost = quantity * unit_cost
        invoice_number = request.form.get('invoice_number')
        
        purchase = Purchase(
            part_id=part_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            status='pending',
            invoice_number=invoice_number,
            user_id=current_user.id
        )
        
        # Create financial transaction for the purchase
        financial_transaction = FinancialTransaction(
            type='expense',
            category='purchase',
            amount=total_cost,
            description=f'Purchase of {quantity} units of part ID {part_id}',
            reference_id=str(purchase.id),
            user_id=current_user.id
        )
        
        db.session.add(purchase)
        db.session.add(financial_transaction)
        db.session.commit()
        
        flash('Purchase order created successfully')
        return redirect(url_for('purchases.list_purchases'))
        
    parts = Part.query.all()
    suppliers = Supplier.query.all()
    warehouses = Warehouse.query.all()
    return render_template('purchases/add.html', parts=parts, suppliers=suppliers, warehouses=warehouses)

@purchases.route('/purchases/<int:id>/receive', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def receive_purchase(id):
    try:
        db.session.begin_nested()  # Create a savepoint
        
        # Get purchase and part in a fresh transaction
        purchase = Purchase.query.get_or_404(id)
        part = Part.query.get_or_404(purchase.part_id)
        
        if purchase.status != 'pending':
            flash('This purchase order is already processed')
            return redirect(url_for('purchases.list_purchases'))
        
        # Calculate new stock level
        new_stock_level = part.stock_level + purchase.quantity
        
        # Update warehouse stock
        warehouse_stock = WarehouseStock.query.filter_by(
            warehouse_id=purchase.warehouse_id,
            part_id=purchase.part_id
        ).first()
        
        if warehouse_stock:
            warehouse_stock.quantity += purchase.quantity
        else:
            warehouse_stock = WarehouseStock(
                warehouse_id=purchase.warehouse_id,
                part_id=purchase.part_id,
                quantity=purchase.quantity
            )
            db.session.add(warehouse_stock)
        
        # Create bincard entry first
        bincard = BinCard(
            part_id=part.id,
            transaction_type='in',
            quantity=purchase.quantity,
            reference_type='purchase',
            reference_id=purchase.id,
            balance=new_stock_level,
            user_id=current_user.id,
            notes=f'Purchase received at ${purchase.unit_cost} per unit (Invoice #{purchase.invoice_number}) in {warehouse_stock.warehouse.name}'
        )
        db.session.add(bincard)
        
        # Update part stock level
        part.stock_level = new_stock_level
        
        # Update purchase status
        purchase.status = 'received'
        purchase.received_date = datetime.utcnow()
        
        # Create or update financial transaction
        financial_transaction = FinancialTransaction.query.filter_by(
            reference_id=str(purchase.id),
            type='expense',
            category='purchase'
        ).first()
        
        if not financial_transaction:
            financial_transaction = FinancialTransaction(
                type='expense',
                category='purchase',
                amount=purchase.total_cost,
                description=f'Purchase received: {purchase.quantity} units of {part.name} (#{purchase.invoice_number})',
                reference_id=str(purchase.id),
                user_id=current_user.id,
                date=datetime.utcnow()
            )
            db.session.add(financial_transaction)
        
        # Commit all changes
        db.session.commit()
        flash('Purchase order marked as received and stock updated successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing purchase: {str(e)}', 'error')
        return redirect(url_for('purchases.list_purchases'))
    
    return redirect(url_for('purchases.list_purchases'))

@purchases.route('/purchases/<int:id>/cancel', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def cancel_purchase(id):
    purchase = Purchase.query.get_or_404(id)
    
    if purchase.status != 'pending':
        flash('Only pending purchases can be cancelled', 'error')
        return redirect(url_for('purchases.list_purchases'))
    
    purchase.status = 'cancelled'
    
    try:
        db.session.commit()
        flash('Purchase order has been cancelled successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling purchase: {str(e)}', 'error')
    
    return redirect(url_for('purchases.list_purchases'))

@purchases.route('/purchases/<int:purchase_id>')
@login_required
@role_required('admin', 'manager')
def view_purchase(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    return render_template('purchases/view.html', purchase=purchase)