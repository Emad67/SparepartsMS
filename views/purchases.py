from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Purchase, Part, Supplier, FinancialTransaction, BinCard, Warehouse, WarehouseStock, ExchangeRate
from datetime import datetime
from views.utils import role_required
from sqlalchemy.exc import SQLAlchemyError
from utils.currency import get_nkf_amount  # Import the utility function
from sqlalchemy.orm import joinedload
from sqlalchemy import inspect
from flask import current_app
import random
import pytz

purchases = Blueprint('purchases', __name__)

@purchases.route('/purchases')
@login_required
@role_required('admin', 'manager')
def list_purchases():
    purchases = Purchase.query.filter(Purchase.status != 'cancelled').order_by(Purchase.purchase_date.desc()).all()
    return render_template('purchases/list.html', purchases=purchases)

@purchases.route('/purchases/bulk', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def bulk_purchase():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data or 'items' not in data:
                return jsonify({'success': False, 'message': 'No items provided'}), 400

            warehouse_id = data.get('warehouse_id')
            supplier_id = data.get('supplier_id')
            if not warehouse_id:
                return jsonify({'success': False, 'message': 'Warehouse is required'}), 400
            if not supplier_id:
                return jsonify({'success': False, 'message': 'Supplier is required'}), 400

            # Start a transaction
            db.session.begin_nested()

            # Process each item
            for item in data['items']:
                part_id = item.get('part_id')
                quantity = item.get('quantity')
                unit_cost = item.get('total_unit_price')  # Use total unit price in NKF
                total_cost = unit_cost * quantity
                unit_aed_price = item.get('unit_aed_price')

                if not all([part_id, quantity, unit_cost]):
                    raise ValueError('Missing required fields in item data')

                # Generate unique invoice number
                timestamp = datetime.now(pytz.timezone('Africa/Nairobi')).strftime("%Y%m%d%H%M%S")
                random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(4)])
                invoice_number = f'BULK-{timestamp}-{random_suffix}'

                # Create purchase entry
                purchase = Purchase(
                    part_id=part_id,
                    warehouse_id=warehouse_id,
                    supplier_id=supplier_id,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    status='received',  # Mark as received immediately
                    invoice_number=invoice_number,
                    user_id=current_user.id,
                    unit_aed_price=unit_aed_price
                )
                db.session.add(purchase)

                # Update warehouse stock
                warehouse_stock = WarehouseStock.query.filter_by(
                    warehouse_id=warehouse_id,
                    part_id=part_id
                ).first()

                if not warehouse_stock:
                    warehouse_stock = WarehouseStock(
                        warehouse_id=warehouse_id,
                        part_id=part_id,
                        quantity=quantity
                    )
                    db.session.add(warehouse_stock)
                else:
                    warehouse_stock.quantity += quantity

                # Update part stock level
                part = Part.query.get(part_id)
                if not part:
                    raise ValueError(f'Part not found: {part_id}')
                part.stock_level += quantity

                # Create bincard entry
                bincard = BinCard(
                    part_id=part_id,
                    transaction_type='in',
                    quantity=quantity,
                    reference_type='purchase',
                    reference_id=purchase.id,
                    balance=part.stock_level,
                    user_id=current_user.id,
                    notes=f'Bulk purchase received at NKF {unit_cost} per unit in {purchase.warehouse.name}'
                )
                db.session.add(bincard)

                # Create financial transaction
                financial_transaction = FinancialTransaction(
                    type='expense',
                    category='purchase',
                    amount=total_cost,
                    description=f'Bulk purchase received: {quantity} units of {part.name}',
                    reference_id=str(purchase.id),
                    user_id=current_user.id,
                    date=datetime.now(pytz.timezone('Africa/Nairobi')),
                    exchange_rate=ExchangeRate.get_rate_for_date()
                )
                db.session.add(financial_transaction)
                
                # Calculate cost price in Dirham
                new_cost_price_dirham = part.calculate_cost_price_dirham()
                part.cost_price_dirham = new_cost_price_dirham
                print("New cost price in Dirham:", new_cost_price_dirham)
                db.session.add(part)
                db.session.flush()

                # Update part cost price
                db.session.refresh(part)
                new_cost_price = part.calculate_cost_price()
                part.cost_price = new_cost_price
                db.session.add(part)
                db.session.flush()

                

            # Commit all changes
            db.session.commit()
            return jsonify({'success': True, 'message': 'Bulk purchase processed successfully'})

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in bulk_purchase: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    parts = Part.query.all()
    warehouses = Warehouse.query.all()
    suppliers = Supplier.query.all()
    return render_template('purchases/bulk_entry.html', parts=parts, warehouses=warehouses, suppliers=suppliers)

@purchases.route('/purchases/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def add_purchase():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        supplier_id = request.form.get('supplier_id')
        warehouse_id = request.form.get('warehouse_id')
        quantity = int(request.form.get('quantity'))
        unit_cost = float(request.form.get('unit_price'))
        total_cost = quantity * unit_cost
        invoice_number = request.form.get('invoice_number')
        
        

        # Create the purchase entry
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
        
        try:
            db.session.add(purchase)
            db.session.commit()
            flash('Purchase order created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating purchase order: {str(e)}', 'error')

        
        
        return redirect(url_for('purchases.list_purchases'))
        
    parts = Part.query.all()
    suppliers = Supplier.query.all()
    warehouses = Warehouse.query.all()
    return render_template('purchases/add.html', parts=parts, suppliers=suppliers, warehouses=warehouses)

@purchases.route('/purchases/<int:id>/receive', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def receive_purchase(id):
    """Mark a purchase as received and update stock and financial transactions."""
    try:
        db.session.begin_nested()  # Create a savepoint
        
        # Get purchase and part in a fresh transaction
        purchase = Purchase.query.options(
            joinedload(Purchase.part),
            joinedload(Purchase.supplier),
            joinedload(Purchase.warehouse)
        ).get_or_404(id)
        
        if not purchase.part:
            raise ValueError(f"Part not found for purchase {id}")
            
        part = purchase.part  # Use the already loaded part
        
        if not purchase.warehouse:
            raise ValueError(f"Warehouse not found for purchase {id}")
            
        if purchase.status == 'received':
            flash('This purchase order is already processed')
            return redirect(url_for('purchases.list_purchases'))
        
        # Update warehouse stock
        warehouse_stock = WarehouseStock.query.filter_by(
            warehouse_id=purchase.warehouse_id,
            part_id=purchase.part_id
        ).first()
        
        if not warehouse_stock:
            warehouse_stock = WarehouseStock(
                warehouse_id=purchase.warehouse_id,
                part_id=purchase.part_id,
                quantity=purchase.quantity
            )
            db.session.add(warehouse_stock)
        else:
            warehouse_stock.quantity += purchase.quantity

        # Update part stock level
        purchase.part.stock_level += purchase.quantity

        # Create bincard entry first
        bincard = BinCard(
            part_id=part.id,
            transaction_type='in',
            quantity=purchase.quantity,
            reference_type='purchase',
            reference_id=purchase.id,
            balance=purchase.part.stock_level,
            user_id=current_user.id,
            notes=f'Purchase received at NKF {purchase.unit_cost} per unit (Invoice #{purchase.invoice_number}) in {purchase.warehouse.name}'
        )
        db.session.add(bincard)
        
        # Update purchase status
        purchase.status = 'received'
        db.session.add(purchase)
        
        # Create or update financial transaction
        total_cost_nkf = purchase.total_cost  # Assuming `total_cost` is already in NKF
        financial_transaction = FinancialTransaction(
            type='expense',
            category='purchase',
            amount=total_cost_nkf,
            description=f'Purchase received: {purchase.quantity} units of {part.name} (Invoice #{purchase.invoice_number})',
            reference_id=str(purchase.id),
            user_id=current_user.id,
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            exchange_rate=ExchangeRate.get_rate_for_date()  # Store the exchange rate used
        )
        db.session.add(financial_transaction)
        
        # Update the part's cost price based on the new purchase
        new_cost_price = purchase.part.calculate_cost_price()
        
        # Use SQLAlchemy's set_committed_value to update the cost price
        inspect(purchase.part).session.expire(purchase.part, ['cost_price'])
        purchase.part.cost_price = new_cost_price
        db.session.add(purchase.part)
        db.session.flush()  # Force the update to be written to the database
        flash(f"Calculated new cost price for part in receive_purchase method {purchase.part.id}: {new_cost_price}")
        
        # Calculate cost price in Dirham
        purchase.part.calculate_cost_price_dirham()
        
        # Commit all changes
        db.session.commit()
        flash('Purchase order marked as received and stock updated successfully', 'success')
        return redirect(url_for('purchases.list_purchases'))

    except Exception as e:
        # Rollback in case of an error
        db.session.rollback()
        current_app.logger.error(f"Error in receive_purchase: {str(e)}")
        current_app.logger.error(f"Purchase ID: {id}")
        current_app.logger.error(f"Purchase object: {purchase}")
        if purchase:
            current_app.logger.error(f"Purchase part: {purchase.part}")
            current_app.logger.error(f"Purchase warehouse: {purchase.warehouse}")
        flash(f'Error processing purchase: {str(e)}', 'error')
        
    # Redirect back to the purchases list
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
    purchase = Purchase.query.get_or_404(purchase_id)
    return render_template('purchases/view.html', purchase=purchase)