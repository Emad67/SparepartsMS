from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Part, Warehouse, WarehouseStock, Transaction, BinCard, FinancialTransaction
from decimal import Decimal
from datetime import datetime

pos = Blueprint('pos', __name__)

@pos.route('/pos')
@login_required
def index():
    warehouses = Warehouse.query.all()
    return render_template('pos/index.html', warehouses=warehouses)

@pos.route('/api/search-parts')
@login_required
def search_parts():
    query = request.args.get('query', '')
    warehouse_id = request.args.get('warehouse_id')
    dimensions = request.args.get('dimensions', '').split(',')
    
    # Base query with joins
    base_query = Part.query.join(WarehouseStock)
    
    if warehouse_id:
        base_query = base_query.filter(WarehouseStock.warehouse_id == warehouse_id)
    
    # Add dimension filters if provided
    if dimensions and len(dimensions) == 3:
        try:
            length, width, height = map(float, dimensions)
            if length > 0:
                base_query = base_query.filter(Part.length == length)
            if width > 0:
                base_query = base_query.filter(Part.width == width)
            if height > 0:
                base_query = base_query.filter(Part.height == height)
        except ValueError:
            pass
    
    # Search across multiple fields
    search = f"%{query}%"
    parts = base_query.filter(
        db.or_(
            Part.part_number.ilike(search),
            Part.name.ilike(search),
            Part.model.ilike(search),
            Part.make.ilike(search)
        )
    ).all()
    
    return jsonify([{
        'id': part.id,
        'part_number': part.part_number,
        'name': part.name,
        'model': part.model,
        'make': part.make,
        'min_price': float(part.min_price) if part.min_price else 0,
        'max_price': float(part.max_price) if part.max_price else 0,
        'length': float(part.length) if part.length else 0,
        'width': float(part.width) if part.width else 0,
        'height': float(part.height) if part.height else 0,
        'image_url': part.image_url,
        'stock': {
            stock.warehouse_id: {
                'quantity': stock.quantity,
                'warehouse_name': stock.warehouse.name
            } for stock in part.warehouse_stocks
        }
    } for part in parts])

@pos.route('/api/complete-sale', methods=['POST'])
@login_required
def complete_sale():
    cart_items = request.json.get('items', [])
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    try:
        total_amount = 0
        for item in cart_items:
            part_id = item['partId']
            warehouse_id = item['warehouseId']
            quantity = item['quantity']
            price = item['price']
            total_item_amount = price * quantity
            total_amount += total_item_amount
            
            # Get the warehouse stock
            warehouse_stock = WarehouseStock.query.filter_by(
                warehouse_id=warehouse_id,
                part_id=part_id
            ).first()
            
            if not warehouse_stock or warehouse_stock.quantity < quantity:
                return jsonify({
                    'error': f'Not enough stock for part {item["partNumber"]} in warehouse {item["warehouseName"]}'
                }), 400
            
            # Create sale transaction
            sale = Transaction(
                part_id=part_id,
                type='sale',
                quantity=quantity,
                price=price,
                date=datetime.utcnow(),
                user_id=current_user.id
            )
            
            # Update warehouse stock
            warehouse_stock.quantity -= quantity
            
            # Add the sale to get its ID
            db.session.add(sale)
            db.session.flush()
            
            # Create bincard entry
            bincard = BinCard(
                part_id=part_id,
                transaction_type='out',
                quantity=quantity,
                reference_type='sale',
                reference_id=sale.id,
                balance=warehouse_stock.quantity,
                user_id=current_user.id,
                notes=f'Sale at ${price} per unit from {warehouse_stock.warehouse.name}'
            )
            
            db.session.add(bincard)
            
            # Create financial transaction for the sale
            financial_transaction = FinancialTransaction(
                type='revenue',
                category='Sales',
                amount=total_item_amount,
                description=f'Sale of {quantity} units of part ID {part_id} at ${price} per unit',
                reference_id=str(sale.id),
                user_id=current_user.id,
                date=datetime.utcnow()
            )
            db.session.add(financial_transaction)
        
        db.session.commit()
        return jsonify({'message': 'Sale completed successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 