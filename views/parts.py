from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Part, Category, Supplier, BinCard, Warehouse, WarehouseStock
from werkzeug.utils import secure_filename
import os
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

parts = Blueprint('parts', __name__)

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@parts.route('/parts/staff')
@login_required
def staff_list_parts():
    # Get all parts ordered by creation date (newest first)
    parts = Part.query.order_by(desc(Part.created_at)).all()
    
    # Update stock levels from all warehouses
    for part in parts:
        # Calculate total stock across all warehouses
        total_stock = sum(stock.quantity for stock in part.warehouse_stocks)
        part.stock_level = total_stock
    
    # Get categories for filtering
    categories = Category.query.all()
    
    return render_template('parts/staff_list.html', parts=parts, categories=categories)

@parts.route('/parts')
@login_required
def list_parts():
    # Get all parts with their warehouse stocks
    parts = Part.query.all()
    
    # Update stock levels from all warehouses
    for part in parts:
        # Calculate total stock across all warehouses
        total_stock = sum(stock.quantity for stock in part.warehouse_stocks)
        
        # Update the part's stock level
        part.stock_level = total_stock
        
        # Get the latest bincard entry
        latest_bincard = BinCard.query.filter_by(part_id=part.id)\
            .order_by(BinCard.date.desc())\
            .first()
        
        # If there's a bincard entry and its balance doesn't match total stock,
        # create a new adjustment entry
        if latest_bincard and latest_bincard.balance != total_stock:
            adjustment = BinCard(
                part_id=part.id,
                transaction_type='adjustment',
                quantity=abs(total_stock - latest_bincard.balance),
                reference_type='stock_reconciliation',
                reference_id=0,
                balance=total_stock,
                user_id=current_user.id,
                notes=f'Stock reconciliation: adjusted to match warehouse totals'
            )
            db.session.add(adjustment)
    
    # Commit the changes to update stock levels and bincard entries
    db.session.commit()
    
    categories = Category.query.all()
    return render_template('parts/list.html', parts=parts, categories=categories)

@parts.route('/parts/add', methods=['GET', 'POST'])
@login_required
def add_part():
    if request.method == 'POST':
        # Get form data
        part_number = request.form.get('part_number')
        name = request.form.get('name')
        warehouse_id = request.form.get('warehouse_id')
        unit = request.form.get('unit')
        initial_stock = request.form.get('initial_stock', '0')
        
        # Validate required fields
        errors = []
        if not part_number:
            errors.append("Part number is required")
        if not name:
            errors.append("Part name is required")
        if not warehouse_id:
            errors.append("Warehouse selection is required")
        if not unit:
            errors.append("Unit is required")
            
        # Validate numeric fields
        try:
            initial_stock = int(initial_stock)
            if initial_stock < 0:
                errors.append("Initial stock cannot be negative")
        except ValueError:
            errors.append("Initial stock must be a valid number")
            
        if request.form.get('min_stock'):
            try:
                min_stock = int(request.form.get('min_stock'))
                if min_stock < 0:
                    errors.append("Minimum stock level cannot be negative")
            except ValueError:
                errors.append("Minimum stock level must be a valid number")
                
        # Validate price fields if provided
        if request.form.get('min_price'):
            try:
                min_price = float(request.form.get('min_price'))
                if min_price < 0:
                    errors.append("Minimum price cannot be negative")
            except ValueError:
                errors.append("Minimum price must be a valid number")
                
        if request.form.get('max_price'):
            try:
                max_price = float(request.form.get('max_price'))
                if max_price < 0:
                    errors.append("Maximum price cannot be negative")
                if request.form.get('min_price') and max_price < float(request.form.get('min_price')):
                    errors.append("Maximum price cannot be less than minimum price")
            except ValueError:
                errors.append("Maximum price must be a valid number")
        
        # Check if part number already exists
        existing_part = Part.query.filter_by(part_number=part_number).first()
        if existing_part:
            errors.append('A part with this part number already exists')
            
        # If there are any validation errors, flash them and return
        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('parts.add_part'))
            
        try:
            # Create new part
            part = Part(
                part_number=part_number,
                name=name,
                location=request.form.get('location'),
                model=request.form.get('model'),
                make=request.form.get('make'),
                stock_level=initial_stock,
                min_stock=int(request.form.get('min_stock', 0)),
                weight=float(request.form.get('weight')) if request.form.get('weight') else None,
                height=float(request.form.get('height')) if request.form.get('height') else None,
                length=float(request.form.get('length')) if request.form.get('length') else None,
                width=float(request.form.get('width')) if request.form.get('width') else None,
                color=request.form.get('color'),
                description=request.form.get('description', ''),
                unit=unit,
                min_price=float(request.form.get('min_price')) if request.form.get('min_price') else None,
                max_price=float(request.form.get('max_price')) if request.form.get('max_price') else None,
                category_id=request.form.get('category_id') or None,
                supplier_id=request.form.get('supplier_id') or None
            )
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    try:
                        filename = secure_filename(file.filename)
                        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                        
                        # Create upload folder if it doesn't exist
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder)
                            
                        file.save(os.path.join(upload_folder, filename))
                        part.image_url = f'/static/uploads/{filename}'
                    except Exception as e:
                        flash(f'Error uploading image: {str(e)}', 'error')
                        return redirect(url_for('parts.add_part'))
            
            # Add part to database first
            db.session.add(part)
            db.session.flush()  # Flush to get the part ID
            
            # Create warehouse stock entry
            warehouse = Warehouse.query.get(warehouse_id)
            if not warehouse:
                flash('Selected warehouse not found', 'error')
                db.session.rollback()
                return redirect(url_for('parts.add_part'))
            
            warehouse_stock = WarehouseStock(
                warehouse_id=warehouse_id,
                part_id=part.id,
                quantity=initial_stock
            )
            db.session.add(warehouse_stock)
            db.session.flush()  # Flush to get the warehouse_stock ID
            
            # Create bin card entry for initial stock
            if initial_stock > 0:
                bin_card = BinCard(
                    part_id=part.id,
                    transaction_type='in',
                    quantity=initial_stock,
                    reference_type='initial_stock',
                    reference_id=warehouse_stock.id,  # Now we have the warehouse_stock ID
                    balance=initial_stock,
                    user_id=current_user.id,
                    notes=f'Initial stock in warehouse {warehouse.name}'
                )
                db.session.add(bin_card)
            
            db.session.commit()
            flash('Part added successfully', 'success')
            return redirect(url_for('parts.list_parts'))
            
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'error')
            return redirect(url_for('parts.add_part'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding part: {str(e)}', 'error')
            return redirect(url_for('parts.add_part'))
            
    categories = Category.query.all()
    suppliers = Supplier.query.all()
    warehouses = Warehouse.query.all()
    return render_template('parts/add.html', categories=categories, suppliers=suppliers, warehouses=warehouses)

@parts.route('/parts/<int:part_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_part(part_id):
    part = Part.query.get_or_404(part_id)
    categories = Category.query.all()
    suppliers = Supplier.query.all()
    warehouses = Warehouse.query.all()
    
    if request.method == 'POST':
        part.name = request.form.get('name')
        part.make = request.form.get('make')
        part.model = request.form.get('model')
        part.location = request.form.get('location')
        part.weight = float(request.form.get('weight', 0)) if request.form.get('weight') else None
        part.height = float(request.form.get('height', 0)) if request.form.get('height') else None
        part.length = float(request.form.get('length', 0)) if request.form.get('length') else None
        part.width = float(request.form.get('width', 0)) if request.form.get('width') else None
        part.color = request.form.get('color')
        part.description = request.form.get('description')
        part.unit = request.form.get('unit')
        part.min_price = float(request.form.get('min_price', 0)) if request.form.get('min_price') else None
        part.max_price = float(request.form.get('max_price', 0)) if request.form.get('max_price') else None
        part.category_id = int(request.form.get('category_id')) if request.form.get('category_id') else None
        part.supplier_id = int(request.form.get('supplier_id')) if request.form.get('supplier_id') else None
        part.warranty_period = int(request.form.get('warranty_period', 0)) if request.form.get('warranty_period') else None
        part.barcode = request.form.get('barcode')
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    file.save(os.path.join(upload_folder, filename))
                    part.image_url = f'/static/uploads/{filename}'
                except Exception as e:
                    flash(f'Error uploading image: {str(e)}', 'error')
        
        try:
            # Update existing warehouse stock
            total_stock = 0
            for stock in part.warehouse_stocks:
                # Check if stock should be removed
                if f'remove_stock_{stock.warehouse_id}' in request.form:
                    db.session.delete(stock)
                    # Create bin card entry for stock removal
                    bin_card = BinCard(
                        part_id=part.id,
                        transaction_type='out',
                        quantity=stock.quantity,
                        reference_type='warehouse_removal',
                        reference_id=stock.id,
                        balance=total_stock,
                        user_id=current_user.id,
                        notes=f'Removed from warehouse {stock.warehouse.name}'
                    )
                    db.session.add(bin_card)
                else:
                    # Update quantity
                    new_quantity = int(request.form.get(f'stock_{stock.warehouse_id}', 0))
                    if new_quantity != stock.quantity:
                        # Create bin card entry for stock adjustment
                        quantity_change = new_quantity - stock.quantity
                        bin_card = BinCard(
                            part_id=part.id,
                            transaction_type='in' if quantity_change > 0 else 'out',
                            quantity=abs(quantity_change),
                            reference_type='stock_adjustment',
                            reference_id=stock.id,
                            balance=total_stock + new_quantity,
                            user_id=current_user.id,
                            notes=f'Stock adjusted in warehouse {stock.warehouse.name}'
                        )
                        db.session.add(bin_card)
                        stock.quantity = new_quantity
                    total_stock += new_quantity
            
            # Add new warehouse stock if specified
            new_warehouse_id = request.form.get('new_warehouse_id')
            new_quantity = int(request.form.get('new_warehouse_quantity', 0))
            if new_warehouse_id and new_quantity > 0:
                new_stock = WarehouseStock(
                    warehouse_id=int(new_warehouse_id),
                    part_id=part.id,
                    quantity=new_quantity
                )
                db.session.add(new_stock)
                total_stock += new_quantity
                
                # Create bin card entry for new stock
                bin_card = BinCard(
                    part_id=part.id,
                    transaction_type='in',
                    quantity=new_quantity,
                    reference_type='new_warehouse_stock',
                    reference_id=new_stock.warehouse_id,
                    balance=total_stock,
                    user_id=current_user.id,
                    notes=f'Added to warehouse {new_stock.warehouse.name}'
                )
                db.session.add(bin_card)
            
            # Update total stock level
            part.stock_level = total_stock
            
            db.session.commit()
            flash('Part updated successfully', 'success')
            return redirect(url_for('parts.list_parts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating part: {str(e)}', 'error')
            return redirect(url_for('parts.edit_part', part_id=part.id))
    
    return render_template('parts/edit.html', part=part, categories=categories, suppliers=suppliers, warehouses=warehouses)

@parts.route('/parts/<int:part_id>/bincard')
@login_required
def view_bincard(part_id):
    part = Part.query.get_or_404(part_id)
    entries = BinCard.query.filter_by(part_id=part_id).order_by(BinCard.date.desc()).all()
    
    return render_template('parts/bincard.html', 
                         part=part, 
                         entries=entries)

@parts.route('/api/check-part-number')
@login_required
def check_part_number():
    part_number = request.args.get('part_number')
    exists = Part.query.filter_by(part_number=part_number).first() is not None
    return jsonify({'exists': exists})

@parts.route('/parts/<int:part_id>/delete', methods=['POST'])
@login_required
def delete_part(part_id):
    part = Part.query.get_or_404(part_id)
    
    try:
        # Delete the part's image file if it exists
        if part.image_url:
            image_path = os.path.join(current_app.root_path, 'static', part.image_url.lstrip('/static/'))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # Delete associated bin card entries
        BinCard.query.filter_by(part_id=part_id).delete()
        
        # Delete the part
        db.session.delete(part)
        db.session.commit()
        flash('Part deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting part: {str(e)}', 'error')
        
    return redirect(url_for('parts.list_parts')) 