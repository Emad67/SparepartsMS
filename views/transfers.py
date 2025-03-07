from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Transfer, Part, Warehouse, WarehouseStock, BinCard, TransferItem, Location
from datetime import datetime
import uuid

transfers = Blueprint('transfers', __name__)

@transfers.route('/transfers')
@login_required
def list_transfers():
    transfers = Transfer.query.order_by(Transfer.created_at.desc()).all()
    return render_template('transfers/list.html', transfers=transfers)

@transfers.route('/transfers/add', methods=['GET', 'POST'])
@login_required
def add_transfer():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        from_location = request.form.get('from_location')
        to_location = request.form.get('to_location')
        quantity = int(request.form.get('quantity'))
        
        # Validate locations are different
        if from_location == to_location:
            flash('Source and destination locations must be different', 'error')
            return redirect(url_for('transfers.add_transfer'))
        
        # Validate source warehouse has enough stock
        source_stock = WarehouseStock.query.filter_by(
            warehouse_id=from_location,
            part_id=part_id
        ).first()
        
        if not source_stock or source_stock.quantity < quantity:
            flash('Not enough stock in source location', 'error')
            return redirect(url_for('transfers.add_transfer'))
        
        # Create transfer with a reference number
        transfer = Transfer(
            reference_number=f'TRF-{datetime.utcnow().strftime("%Y%m%d")}-{uuid.uuid4().hex[:6].upper()}',
            from_location_id=from_location,
            to_location_id=to_location,
            status='pending',
            created_by_id=current_user.id
        )
        
        # Create transfer item
        transfer_item = TransferItem(
            part_id=part_id,
            quantity=quantity
        )
        transfer.items.append(transfer_item)
        
        # Reduce stock in source warehouse immediately
        source_stock.quantity -= quantity
        
        db.session.add(transfer)
        db.session.commit()
        
        flash('Transfer created successfully')
        return redirect(url_for('transfers.list_transfers'))
        
    parts = Part.query.all()
    warehouses = Warehouse.query.all()
    
    # Get stock levels for each part in each warehouse
    stock_levels = {}
    for part in parts:
        stock_levels[part.id] = {}
        for warehouse in warehouses:
            stock = WarehouseStock.query.filter_by(
                warehouse_id=warehouse.id,
                part_id=part.id
            ).first()
            stock_levels[part.id][warehouse.id] = stock.quantity if stock else 0
    
    return render_template('transfers/add.html', 
                         parts=parts, 
                         warehouses=warehouses,
                         stock_levels=stock_levels)

@transfers.route('/transfers/<int:id>/complete', methods=['POST'])
@login_required
def complete_transfer(id):
    transfer = Transfer.query.get_or_404(id)
    
    if transfer.status != 'pending':
        flash('This transfer is already processed', 'error')
        return redirect(url_for('transfers.list_transfers'))
    
    # Process each transfer item
    for transfer_item in transfer.items:
        # Update destination warehouse stock
        dest_stock = WarehouseStock.query.filter_by(
            warehouse_id=transfer.to_location_id,
            part_id=transfer_item.part_id
        ).first()
        
        if not dest_stock:
            dest_stock = WarehouseStock(
                warehouse_id=transfer.to_location_id,
                part_id=transfer_item.part_id,
                quantity=0
            )
            db.session.add(dest_stock)
        
        dest_stock.quantity += transfer_item.quantity
        
        # Get source warehouse stock for balance
        source_stock = WarehouseStock.query.filter_by(
            warehouse_id=transfer.from_location_id,
            part_id=transfer_item.part_id
        ).first()
        
        # Create bin card entries
        source_bincard = BinCard(
            part_id=transfer_item.part_id,
            transaction_type='out',
            quantity=transfer_item.quantity,
            reference_type='transfer',
            reference_id=transfer.id,
            balance=source_stock.quantity if source_stock else 0,
            user_id=current_user.id,
            notes=f'Transfer to warehouse {transfer.to_location.name}'
        )
        
        dest_bincard = BinCard(
            part_id=transfer_item.part_id,
            transaction_type='in',
            quantity=transfer_item.quantity,
            reference_type='transfer',
            reference_id=transfer.id,
            balance=dest_stock.quantity,
            user_id=current_user.id,
            notes=f'Transfer from warehouse {transfer.from_location.name}'
        )
        
        db.session.add(source_bincard)
        db.session.add(dest_bincard)
    
    transfer.status = 'completed'
    db.session.commit()
    
    flash('Transfer completed successfully')
    return redirect(url_for('transfers.list_transfers'))

@transfers.route('/transfers/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_transfer(id):
    transfer = Transfer.query.get_or_404(id)
    
    if transfer.status != 'pending':
        flash('Only pending transfers can be cancelled', 'error')
        return redirect(url_for('transfers.list_transfers'))
    
    # Return stock to source warehouse for each item
    for transfer_item in transfer.items:
        source_stock = WarehouseStock.query.filter_by(
            warehouse_id=transfer.from_location_id,
            part_id=transfer_item.part_id
        ).first()
        
        if source_stock:
            source_stock.quantity += transfer_item.quantity
        
        # Create bin card entry for returned stock
        bincard = BinCard(
            part_id=transfer_item.part_id,
            transaction_type='in',
            quantity=transfer_item.quantity,
            reference_type='transfer_cancelled',
            reference_id=transfer.id,
            balance=source_stock.quantity if source_stock else transfer_item.quantity,
            user_id=current_user.id,
            notes=f'Transfer cancelled'
        )
        
        db.session.add(bincard)
    
    transfer.status = 'cancelled'
    db.session.commit()
    
    flash('Transfer cancelled successfully')
    return redirect(url_for('transfers.list_transfers'))

@transfers.route('/api/stock-level')
@login_required
def get_stock_level():
    warehouse_id = request.args.get('warehouse_id')
    part_id = request.args.get('part_id')
    
    stock = WarehouseStock.query.filter_by(
        warehouse_id=warehouse_id,
        part_id=part_id
    ).first()
    
    return jsonify({
        'quantity': stock.quantity if stock else 0
    })

@transfers.route('/transfers/<int:transfer_id>')
@login_required
def view_transfer(transfer_id):
    transfer = Transfer.query.get_or_404(transfer_id)
    return render_template('transfers/view.html', transfer=transfer) 