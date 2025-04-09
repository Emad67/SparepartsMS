from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Part, Warehouse, WarehouseStock, Disposal, BinCard, FinancialTransaction, ExchangeRate
from datetime import datetime
from views.utils import role_required
from utils.currency import format_nkf  # Import the utility function


disposals = Blueprint('disposals', __name__)

@disposals.route('/disposals')
@login_required
@role_required('admin', 'manager')
def list_disposals():
    disposals = Disposal.query.order_by(Disposal.disposal_date.desc()).all()
    return render_template('disposals/list.html', disposals=disposals)

@disposals.route('/disposals/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_disposal():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        warehouse_id = request.form.get('warehouse_id')
        quantity = int(request.form.get('quantity', 0))
        reason = request.form.get('reason')
        
        if not all([part_id, warehouse_id, quantity, reason]):
            flash('All fields are required', 'error')
            return redirect(url_for('disposals.add_disposal'))
        
        # Check warehouse stock
        warehouse_stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_id,
            part_id=part_id
        ).first()
        
        if not warehouse_stock or warehouse_stock.quantity < quantity:
            flash('Insufficient stock in selected warehouse', 'error')
            return redirect(url_for('disposals.add_disposal'))
        
        try:
            # Start transaction
            db.session.begin_nested()
            
            part = Part.query.get(part_id)
            
            # Calculate cost of disposed items
            unit_cost = part.cost_price or 0
            total_cost = unit_cost * quantity
            
            # Create disposal record
            disposal = Disposal(
                part_id=part_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                reason=reason,
                user_id=current_user.id,
                cost=total_cost
            )
            db.session.add(disposal)
            db.session.flush()  # Generate the disposal ID without committing
            
            # Update warehouse stock
            warehouse_stock.quantity -= quantity
            part.stock_level -= quantity
            
            # Create bin card entry
            bin_card = BinCard(
                part_id=part_id,
                transaction_type='out',
                quantity=quantity,
                reference_type='disposal',
                reference_id=disposal.id,
                balance=part.stock_level,
                user_id=current_user.id,
                notes=f'Disposal: {reason}'
            )
            db.session.add(bin_card)
            
            # Create financial transaction for the loss
            financial_transaction = FinancialTransaction(
                type='expense',
                category='Disposal Loss',
                amount=total_cost,
                description=f'Disposal of {quantity} units of {part.name} (#{part.part_number}) at {format_nkf(unit_cost)} per unit',
                reference_id=str(disposal.id),
                user_id=current_user.id,
                date=datetime.utcnow(),
                exchange_rate=ExchangeRate.get_rate_for_date()
            )
            db.session.add(financial_transaction)
            
            db.session.commit()
            flash('Part disposal recorded successfully', 'success')
            return redirect(url_for('disposals.list_disposals'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording disposal: {str(e)}', 'error')
            return redirect(url_for('disposals.add_disposal'))
    
    # GET request - show form
    parts = Part.query.all()
    warehouses = Warehouse.query.all()
    return render_template('disposals/add.html', parts=parts, warehouses=warehouses)

@disposals.route('/api/warehouse-stock')
@login_required
@role_required('admin', 'manager')
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