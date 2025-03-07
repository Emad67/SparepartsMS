from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Part, Transaction, Customer, User, BinCard, FinancialTransaction
from datetime import datetime

sales = Blueprint('sales', __name__)

@sales.route('/sales')
@login_required
def list_sales():
    sales = Transaction.query.filter_by(type='sale').order_by(Transaction.date.desc()).all()
    # Get unique users who have made sales
    users = User.query.join(Transaction).filter(Transaction.type == 'sale').distinct().all()
    return render_template('sales/list.html', sales=sales, users=users)

@sales.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))
        customer_id = request.form.get('customer_id')
        
        part = Part.query.get_or_404(part_id)
        
        if part.stock_level < quantity:
            flash('Not enough stock available', 'error')
            return redirect(url_for('sales.new_sale'))
            
        sale = Transaction(
            part_id=part_id,
            type='sale',
            quantity=quantity,
            price=price,
            date=datetime.utcnow(),
            user_id=current_user.id
        )
        
        # Update stock level
        part.stock_level -= quantity
        
        # First commit the sale to get its ID
        db.session.add(sale)
        db.session.flush()
        
        # Create financial transaction for the sale
        total_amount = price * quantity
        financial_transaction = FinancialTransaction(
            type='revenue',
            category='Sales',
            amount=total_amount,
            description=f'Sale of {quantity} units of part ID {part_id} at ${price} per unit',
            reference_id=str(sale.id),
            user_id=current_user.id,
            date=datetime.utcnow()
        )
        
        # Now create bincard entry with the sale's ID
        bincard = BinCard(
            part_id=part_id,
            transaction_type='out',
            quantity=quantity,
            reference_type='sale',
            reference_id=sale.id,
            balance=part.stock_level,
            user_id=current_user.id,
            notes=f'Sale at ${price} per unit'
        )
        
        db.session.add(bincard)
        db.session.add(financial_transaction)
        db.session.commit()
        
        flash('Sale recorded successfully')
        return redirect(url_for('sales.list_sales'))
        
    parts = Part.query.filter(Part.stock_level > 0).all()
    customers = Customer.query.all()
    return render_template('sales/new.html', parts=parts, customers=customers)

@sales.route('/api/parts/search')
@login_required
def search_parts():
    query = request.args.get('q', '')
    parts = Part.query.filter(
        (Part.name.ilike(f'%{query}%')) |
        (Part.part_number.ilike(f'%{query}%'))
    ).all()
    return jsonify([{
        'id': part.id,
        'name': part.name,
        'part_number': part.part_number,
        'stock_level': part.stock_level,
        'price': part.max_price
    } for part in parts])

@sales.route('/sales/<int:sale_id>')
@login_required
def view_sale(sale_id):
    sale = Transaction.query.filter_by(id=sale_id, type='sale').first_or_404()
    return render_template('sales/view.html', sale=sale)