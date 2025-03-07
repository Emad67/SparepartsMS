from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Purchase, Part, Supplier, FinancialTransaction, BinCard
from datetime import datetime

purchases = Blueprint('purchases', __name__)

@purchases.route('/purchases')
@login_required
def list_purchases():
    purchases = Purchase.query.order_by(Purchase.purchase_date.desc()).all()
    return render_template('purchases/list.html', purchases=purchases)

@purchases.route('/purchases/add', methods=['GET', 'POST'])
@login_required
def add_purchase():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        supplier_id = request.form.get('supplier_id')
        quantity = int(request.form.get('quantity'))
        unit_cost = float(request.form.get('unit_cost'))
        total_cost = quantity * unit_cost
        invoice_number = request.form.get('invoice_number')
        
        purchase = Purchase(
            part_id=part_id,
            supplier_id=supplier_id,
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
    return render_template('purchases/add.html', parts=parts, suppliers=suppliers)

@purchases.route('/purchases/<int:id>/receive', methods=['POST'])
@login_required
def receive_purchase(id):
    purchase = Purchase.query.get_or_404(id)
    if purchase.status != 'pending':
        flash('This purchase order is already processed')
        return redirect(url_for('purchases.list_purchases'))
        
    # Update purchase status
    purchase.status = 'received'
    
    # Update stock level
    part = Part.query.get(purchase.part_id)
    part.stock_level += purchase.quantity
    
    # Create bincard entry for the received purchase
    bincard = BinCard(
        part_id=purchase.part_id,
        transaction_type='in',
        quantity=purchase.quantity,
        reference_type='purchase',
        reference_id=purchase.id,
        balance=part.stock_level,
        user_id=current_user.id,
        notes=f'Purchase received at ${purchase.unit_cost} per unit (Invoice #{purchase.invoice_number})'
    )
    
    db.session.add(bincard)
    db.session.commit()
    flash('Purchase order marked as received and stock updated')
    return redirect(url_for('purchases.list_purchases'))

@purchases.route('/purchases/<int:id>/cancel', methods=['POST'])
@login_required
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
def view_purchase(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    return render_template('purchases/view.html', purchase=purchase)