from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, CreditPurchase, Supplier, Part, BinCard, WarehouseStock, Warehouse, FinancialTransaction, ExchangeRate
from datetime import datetime, timedelta
from sqlalchemy import and_
from views.utils import role_required
from utils.date_utils import parse_date_range, format_date
from sqlalchemy.orm import joinedload
from sqlalchemy import inspect
import pytz


credits = Blueprint('credits', __name__)

@credits.route('/credits')
@login_required
@role_required('admin', 'manager')
def list_credits():
    # Get filter parameters
    supplier_id = request.args.get('supplier_id', type=int)
    due_date_start = request.args.get('due_date_start')
    due_date_end = request.args.get('due_date_end')
    
    # Base query
    query = CreditPurchase.query.join(Part)
    
    # Apply filters
    if supplier_id:
        query = query.filter(CreditPurchase.supplier_id == supplier_id)
    
    # Initialize date range variables
    start_datetime, end_datetime = None, None

    # Parse date range
    if due_date_start or due_date_end:
        start_datetime, end_datetime = parse_date_range(due_date_start, due_date_end)
        query = query.filter(
            CreditPurchase.due_date >= start_datetime,
            CreditPurchase.due_date <= end_datetime
        )
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of suppliers per page
    suppliers = Supplier.query.order_by(Supplier.name).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all suppliers for the filter dropdown
    suppliers = Supplier.query.order_by(Supplier.name).all()
    
    # Execute query and order by purchase date
    credits = query.order_by(CreditPurchase.purchase_date.desc()).all()
    
    # Get all warehouses for the dropdown
    warehouses = Warehouse.query.all()
    
    return render_template('credits/list.html', 
                         credits=credits,
                         suppliers=suppliers,
                         warehouses=warehouses,
                         selected_supplier_id=supplier_id,
                         due_date_start=format_date(start_datetime) if due_date_start else None,
                         due_date_end=format_date(end_datetime) if due_date_end else None)

@credits.route('/credits/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_credit():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        part_id = request.form.get('part_id')
        warehouse_id = request.form.get('warehouse_id')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))
        days = int(request.form.get('days', 30))
        
        credit = CreditPurchase(
            supplier_id=supplier_id,
            part_id=part_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            price=price,
            purchase_date=datetime.now(pytz.timezone('Africa/Nairobi')),
            due_date=datetime.now(pytz.timezone('Africa/Nairobi')) + timedelta(days=days),
            status='pending'
        )
        
        try:
            db.session.add(credit)
            db.session.commit()
            flash('Credit purchase created successfully')
            return redirect(url_for('credits.list_credits'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating credit purchase: {str(e)}', 'error')
            return redirect(url_for('credits.add_credit'))
        
    suppliers = Supplier.query.all()
    parts = Part.query.all()
    warehouses = Warehouse.query.all()
    return render_template('credits/add.html', 
                         suppliers=suppliers, 
                         parts=parts,
                         warehouses=warehouses)

@credits.route('/credits/bulk', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def bulk_credit():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data or 'items' not in data:
                return {'success': False, 'message': 'No items provided'}, 400
            warehouse_id = data.get('warehouse_id')
            supplier_id = data.get('supplier_id')
            due_days = int(data.get('due_days', 30))
            if not warehouse_id:
                return {'success': False, 'message': 'Warehouse is required'}, 400
            if not supplier_id:
                return {'success': False, 'message': 'Supplier is required'}, 400
            from datetime import datetime, timedelta
            import pytz
            db.session.begin_nested()
            for item in data['items']:
                part_id = item.get('part_id')
                quantity = item.get('quantity')
                unit_price = item.get('unit_price')
                if not all([part_id, quantity, unit_price]):
                    raise ValueError('Missing required fields in item data')
                credit = CreditPurchase(
                    supplier_id=supplier_id,
                    part_id=part_id,
                    warehouse_id=warehouse_id,
                    quantity=quantity,
                    price=unit_price,
                    purchase_date=datetime.now(pytz.timezone('Africa/Nairobi')),
                    due_date=datetime.now(pytz.timezone('Africa/Nairobi')) + timedelta(days=due_days),
                    status='pending'
                )
                db.session.add(credit)
            db.session.commit()
            return {'success': True, 'message': 'Bulk credit purchase processed successfully'}
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in bulk_credit: {str(e)}")
            return {'success': False, 'message': str(e)}, 500
    parts = Part.query.all()
    warehouses = Warehouse.query.all()
    suppliers = Supplier.query.all()
    return render_template('credits/bulk_entry.html', parts=parts, warehouses=warehouses, suppliers=suppliers)

@credits.route('/credits/<int:id>/mark-paid', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def mark_paid(id):
    try:
        # Start a new transaction
        db.session.begin_nested()
        
        # Eagerly load the credit purchase with its relationships
        credit = CreditPurchase.query.options(
            joinedload(CreditPurchase.part),
            joinedload(CreditPurchase.supplier),
            joinedload(CreditPurchase.warehouse)
        ).get_or_404(id)
        
        if credit.status == 'paid':
            flash('This credit purchase is already marked as paid', 'warning')
            return redirect(url_for('credits.list_credits'))

        # Update warehouse stock using the stored warehouse_id
        warehouse_stock = WarehouseStock.query.filter_by(
            warehouse_id=credit.warehouse_id,
            part_id=credit.part_id
        ).first()
        
        if warehouse_stock:
            warehouse_stock.quantity += credit.quantity
        else:
            warehouse_stock = WarehouseStock(
                warehouse_id=credit.warehouse_id,
                part_id=credit.part_id,
                quantity=credit.quantity
            )
            db.session.add(warehouse_stock)
        
        # Update part's total stock level
        credit.part.stock_level += credit.quantity
        
        # Create bincard entry
        bincard = BinCard(
            part_id=credit.part_id,
            transaction_type='in',
            quantity=credit.quantity,
            reference_type='credit_purchase',
            reference_id=credit.id,
            balance=credit.part.stock_level,
            user_id=current_user.id,
            notes=f'Credit purchase at ${credit.price} per unit in {credit.warehouse.name}'
        )
        db.session.add(bincard)
        
        # Create financial transaction for the payment
        total_amount = credit.price * credit.quantity
        financial_transaction = FinancialTransaction(
            type='expense',
            category='Credit Payment',
            amount=total_amount,
            description=f'Payment for credit purchase #{credit.id}: {credit.quantity} units at ${credit.price} per unit',
            reference_id=str(credit.id),
            user_id=current_user.id,
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            exchange_rate=ExchangeRate.get_rate_for_date()
        )
        db.session.add(financial_transaction)
        
        # Update credit status
        credit.status = 'paid'
        
        # Calculate new cost price
        new_cost_price = credit.part.calculate_cost_price()
        
        # Use SQLAlchemy's set_committed_value to update the cost price
        inspect(credit.part).session.expire(credit.part, ['cost_price'])
        credit.part.cost_price = new_cost_price
        db.session.add(credit.part)
        
        # Commit all changes
        db.session.commit()
        flash('Credit purchase marked as paid and stock updated')
        return redirect(url_for('credits.list_credits'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in mark_paid: {str(e)}")
        flash(f'Error marking credit as paid: {str(e)}', 'error')
        return redirect(url_for('credits.list_credits'))

@credits.route('/credits/<int:id>/status')
@login_required
@role_required('admin', 'manager')
def credit_status(id):
    credit = CreditPurchase.query.options(
        joinedload(CreditPurchase.part),
        joinedload(CreditPurchase.supplier),
        joinedload(CreditPurchase.warehouse)
    ).get_or_404(id)
    # Get all payments (FinancialTransaction) for this credit, including voided
    payments = FinancialTransaction.query.filter_by(
        category='Credit Payment', reference_id=str(credit.id)
    ).order_by(FinancialTransaction.date.desc()).all()
    total_paid = sum(p.amount for p in payments if not p.voided)
    total_amount = credit.price * credit.quantity
    outstanding = total_amount - total_paid
    return render_template('credits/status.html', credit=credit, payments=payments, total_paid=total_paid, total_amount=total_amount, outstanding=outstanding)

@credits.route('/credits/<int:id>/add-payment', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def add_credit_payment(id):
    credit = CreditPurchase.query.get_or_404(id)
    amount = float(request.form['amount'])
    method = request.form['method']
    notes = request.form.get('notes', '')
    payment = FinancialTransaction(
        type='expense',
        category='Credit Payment',
        amount=amount,
        description=f'Payment for credit purchase #{credit.id}: {amount} NKF, method: {method}',
        reference_id=str(credit.id),
        user_id=current_user.id,
        date=datetime.now(pytz.timezone('Africa/Nairobi')),
        exchange_rate=ExchangeRate.get_rate_for_date(),
        voided=False
    )
    db.session.add(payment)
    db.session.flush()
    # If fully paid, update status
    total_paid = sum(p.amount for p in FinancialTransaction.query.filter_by(category='Credit Payment', reference_id=str(credit.id)).all() if not p.voided)
    total_amount = credit.price * credit.quantity
    if total_paid >= total_amount:
        credit.status = 'paid'
        db.session.add(credit)
    db.session.commit()
    flash('Payment recorded successfully', 'success')
    return redirect(url_for('credits.credit_status', id=credit.id))