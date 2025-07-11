from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from models import db, Part, Warehouse, WarehouseStock, Transaction, BinCard, FinancialTransaction, ExchangeRate
from decimal import Decimal
from datetime import datetime
import pytz

pos = Blueprint('pos', __name__, url_prefix='/pos')

@pos.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    search_query = request.args.get('search', '')
    
    # Get all warehouses for the dropdown
    warehouses = Warehouse.query.all()
    
    if search_query:
        query = Part.query.filter(
            db.or_(
                Part.part_number.ilike(f'%{search_query}%'),
                Part.name.ilike(f'%{search_query}%'),
                Part.code.ilike(f'%{search_query}%'),
                Part.substitute_part_number.ilike(f'%{search_query}%')
            )
        )
    else:
        query = Part.query
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    parts = pagination.items
    
    # Convert Part objects to dictionaries with all necessary data
    parts_data = [{
        'id': part.id,
        'name': part.name,
        'part_number': part.part_number,
        'code': part.code,
        'substitute_part_number': part.substitute_part_number,
        'selling_price': float(part.selling_price) if hasattr(part, 'selling_price') and part.selling_price else 0,
        'stock_level': sum(stock.quantity for stock in part.warehouse_stocks),
        'min_price': float(part.min_price) if part.min_price else 0,
        'max_price': float(part.max_price) if part.max_price else 0,
        'image_url': part.image_url or '/static/images/no-image.png',
        'stock': {
            str(stock.warehouse_id): {  # Convert ID to string for JSON
                'quantity': stock.quantity,
                'warehouse_name': stock.warehouse.name
            } for stock in part.warehouse_stocks
        }
    } for part in parts]
    
    return render_template('pos/index.html', 
                         parts=parts_data, 
                         search_query=search_query,
                         warehouses=warehouses,
                         csrf_token=generate_csrf(),
                         pagination=pagination)

@pos.route('/api/search-parts')
@login_required
def search_parts():
    query = request.args.get('query', '')
    warehouse_id = request.args.get('warehouse_id')
    length = request.args.get('length', '')
    width = request.args.get('width', '')
    height = request.args.get('height', '')
    
    # Start with base query
    base_query = Part.query
    
    # Add warehouse filter if specified
    if warehouse_id:
        base_query = base_query.join(WarehouseStock).filter(WarehouseStock.warehouse_id == warehouse_id)
    
    # Add dimension filters if provided
    try:
        if length and float(length) > 0:
            base_query = base_query.filter(Part.length == float(length))
        if width and float(width) > 0:
            base_query = base_query.filter(Part.width == float(width))
        if height and float(height) > 0:
            base_query = base_query.filter(Part.height == float(height))
    except ValueError:
        pass
    
    # Add search filter if query provided
    if query:
        search = f"%{query}%"
        base_query = base_query.filter(
            db.or_(
                Part.part_number.ilike(search),
                Part.name.ilike(search),
                Part.code.ilike(search),
                Part.substitute_part_number.ilike(search)
            )
        )
    
    # Get all parts matching the criteria
    parts = base_query.all()
    
    # Convert to JSON response
    return jsonify([{
        'id': part.id,
        'part_number': part.part_number,
        'name': part.name,
        'code': part.code,
        'substitute_part_number': part.substitute_part_number,
        'selling_price': float(part.selling_price) if hasattr(part, 'selling_price') and part.selling_price else 0,
        'stock_level': sum(stock.quantity for stock in part.warehouse_stocks),
        'min_price': float(part.min_price) if part.min_price else 0,
        'max_price': float(part.max_price) if part.max_price else 0,
        'image_url': part.image_url or '/static/images/no-image.png',
        'stock': {
            str(stock.warehouse_id): {
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
        sales = []  # Keep track of all sales transactions
        
        for item in cart_items:
            part_id = item['partId']
            warehouse_id = item['warehouseId']
            quantity = item['quantity']
            price = item['price']
            payment_method = item.get('paymentMethod')
            payment_note = item.get('paymentInfo')
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
                date=datetime.now(pytz.timezone('Africa/Nairobi')),
                user_id=current_user.id,
                payment_method=payment_method,
                notes=payment_note
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
                notes=f'Sale at NKF {price} per unit from {warehouse_stock.warehouse.name}'
            )
            
            db.session.add(bincard)
            sales.append(sale)
            
        # Create financial transaction for the entire sale
        financial_transaction = FinancialTransaction(
            type='revenue',
            category='Sales',
            amount=total_amount,
            description=f'POS Sale of {len(cart_items)} items',
            reference_id=','.join(str(sale.id) for sale in sales),
            user_id=current_user.id,
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            exchange_rate=ExchangeRate.get_rate_for_date()
        )
        db.session.add(financial_transaction)
        
        # Commit all changes to the database
        db.session.commit()
        
        # Return success with redirect flag
        return jsonify({
            'success': True,
            'message': 'Sale completed successfully',
            'total_amount': total_amount,
            'redirect': True
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500