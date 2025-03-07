from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from models import db, User, Supplier, Customer, Warehouse, WarehouseStock, Part
from functools import wraps
from werkzeug.security import generate_password_hash
import os
from datetime import datetime
import json
import sqlite3
import shutil
import zipfile

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/admin/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/admin/suppliers')
@login_required
@admin_required
def suppliers():
    suppliers = Supplier.query.all()
    return render_template('admin/suppliers.html', suppliers=suppliers)

@admin.route('/admin/customers')
@login_required
@admin_required
def customers():
    customers = Customer.query.all()
    return render_template('admin/customers.html', customers=customers)

@admin.route('/admin/warehouses')
@login_required
@admin_required
def warehouses():
    warehouses = Warehouse.query.all()
    return render_template('admin/warehouses.html', warehouses=warehouses)

@admin.route('/admin/warehouses/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_warehouse():
    if request.method == 'POST':
        warehouse = Warehouse(
            name=request.form.get('name'),
            location=request.form.get('location')
        )
        
        try:
            db.session.add(warehouse)
            db.session.commit()
            flash('Warehouse added successfully', 'success')
            return redirect(url_for('admin.warehouses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding warehouse: {str(e)}', 'error')
            
    return render_template('admin/add_warehouse.html')

@admin.route('/admin/warehouses/<int:warehouse_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_warehouse(warehouse_id):
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    if request.method == 'POST':
        warehouse.name = request.form.get('name')
        warehouse.location = request.form.get('location')
        
        try:
            db.session.commit()
            flash('Warehouse updated successfully', 'success')
            return redirect(url_for('admin.warehouses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating warehouse: {str(e)}', 'error')
            
    return render_template('admin/edit_warehouse.html', warehouse=warehouse)

@admin.route('/admin/warehouses/<int:warehouse_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_warehouse(warehouse_id):
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    try:
        # Delete associated warehouse stock records first
        WarehouseStock.query.filter_by(warehouse_id=warehouse_id).delete()
        db.session.delete(warehouse)
        db.session.commit()
        flash('Warehouse deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting warehouse: {str(e)}', 'error')
        
    return redirect(url_for('admin.warehouses'))

@admin.route('/admin/warehouses/<int:warehouse_id>/stock', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_warehouse_stock(warehouse_id):
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        quantity = int(request.form.get('quantity', 0))
        
        stock = WarehouseStock.query.filter_by(
            warehouse_id=warehouse_id,
            part_id=part_id
        ).first()
        
        if stock:
            stock.quantity = quantity
        else:
            stock = WarehouseStock(
                warehouse_id=warehouse_id,
                part_id=part_id,
                quantity=quantity
            )
            db.session.add(stock)
            
        try:
            db.session.commit()
            flash('Stock updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating stock: {str(e)}', 'error')
            
    warehouse_stock = WarehouseStock.query\
        .join(Part)\
        .filter(WarehouseStock.warehouse_id == warehouse_id)\
        .all()
    parts = Part.query.all()
    return render_template('admin/warehouse_stock.html', 
                         warehouse=warehouse, 
                         warehouse_stock=warehouse_stock,
                         parts=parts)

@admin.route('/admin/suppliers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_supplier():
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form.get('name'),
            contact_person=request.form.get('contact_person'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            payment_terms=request.form.get('payment_terms')
        )
        
        try:
            db.session.add(supplier)
            db.session.commit()
            flash('Supplier added successfully', 'success')
            return redirect(url_for('admin.suppliers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding supplier: {str(e)}', 'error')
            
    return render_template('admin/add_supplier.html')

@admin.route('/admin/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if request.method == 'POST':
        supplier.name = request.form.get('name')
        supplier.contact_person = request.form.get('contact_person')
        supplier.email = request.form.get('email')
        supplier.phone = request.form.get('phone')
        supplier.address = request.form.get('address')
        supplier.payment_terms = request.form.get('payment_terms')
        
        try:
            db.session.commit()
            flash('Supplier updated successfully', 'success')
            return redirect(url_for('admin.suppliers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating supplier: {str(e)}', 'error')
            
    return render_template('admin/edit_supplier.html', supplier=supplier)

@admin.route('/admin/suppliers/<int:supplier_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    try:
        db.session.delete(supplier)
        db.session.commit()
        flash('Supplier deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting supplier: {str(e)}', 'error')
        
    return redirect(url_for('admin.suppliers'))

@admin.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('admin.add_user'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('admin.add_user'))
        
        user = User(
            username=username,
            email=email,
            role=role,
            active=True
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('User added successfully', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding user: ' + str(e), 'error')
            return redirect(url_for('admin.add_user'))
    
    return render_template('admin/add_user.html')

@admin.route('/admin/customers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address')
        )
        
        try:
            db.session.add(customer)
            db.session.commit()
            flash('Customer added successfully', 'success')
            return redirect(url_for('admin.customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding customer: {str(e)}', 'error')
            
    return render_template('admin/add_customer.html')

@admin.route('/admin/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        
        try:
            db.session.commit()
            flash('Customer updated successfully', 'success')
            return redirect(url_for('admin.customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'error')
            
    return render_template('admin/edit_customer.html', customer=customer)

@admin.route('/admin/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    try:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'error')
        
    return redirect(url_for('admin.customers'))

@admin.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        active = request.form.get('active') == 'on'
        new_password = request.form.get('password')
        
        # Check if username is taken by another user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            flash('Username already exists', 'error')
            return redirect(url_for('admin.edit_user', user_id=user_id))
            
        # Check if email is taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user_id:
            flash('Email already exists', 'error')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        try:
            user.username = username
            user.email = email
            user.role = role
            user.active = active
            
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating user: ' + str(e), 'error')
            
    return render_template('admin/edit_user.html', user=user)

@admin.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.users'))
        
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        
    return redirect(url_for('admin.users'))

@admin.route('/admin/backup', methods=['GET', 'POST'])
@login_required
@admin_required
def backup_system():
    if request.method == 'POST':
        try:
            # Get database path from app config
            db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                # Check if it's an absolute path
                if db_uri.startswith('sqlite:////'):
                    db_path = db_uri.replace('sqlite:////', '')
                else:
                    # For relative paths, use the instance folder
                    db_path = os.path.join(current_app.instance_path, db_uri.replace('sqlite:///', ''))
            else:
                db_path = db_uri.replace('sqlite:///', '')

            if not os.path.exists(db_path):
                raise FileNotFoundError(f'Database file not found at {db_path}')

            # Create backups directory if it doesn't exist
            backup_dir = os.path.join(current_app.root_path, 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{current_app.name}_{timestamp}.zip'
            backup_path = os.path.join(backup_dir, backup_filename)

            # Create ZIP file
            with zipfile.ZipFile(backup_path, 'w') as zipf:
                # Add database file
                zipf.write(db_path, os.path.basename(db_path))

                # Add uploaded files
                uploads_dir = current_app.config['UPLOAD_FOLDER']
                if os.path.exists(uploads_dir):
                    for root, dirs, files in os.walk(uploads_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, current_app.root_path)
                            zipf.write(file_path, arcname)

            flash('Backup created successfully', 'success')
        except Exception as e:
            flash(f'Error creating backup: {str(e)}', 'error')

    # Get list of existing backups
    backup_dir = os.path.join(current_app.root_path, 'backups')
    backups = []
    if os.path.exists(backup_dir):
        backups = [f for f in os.listdir(backup_dir) if f.startswith('backup_') and f.endswith('.zip')]
        backups.sort(reverse=True)

    return render_template('admin/backup.html', backups=backups)

@admin.route('/admin/restore/<filename>', methods=['POST'])
@login_required
@admin_required
def restore_system(filename):
    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        zip_path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(zip_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.backup_system'))
        
        # Create a temporary directory for restoration
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Find the database file
            db_backup = next(f for f in os.listdir(temp_dir) if f.endswith('.db'))
            db_backup_path = os.path.join(temp_dir, db_backup)
            
            # Close the current database connection
            db.session.remove()
            db.engine.dispose()
            
            # Get the correct database path
            db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                # Handle relative path
                db_path = os.path.join(current_app.root_path, db_uri.replace('sqlite:///', ''))
            else:
                # Handle absolute path (Windows)
                db_path = db_uri.replace('sqlite:///', '')
            
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Replace the current database with the backup
            shutil.copy2(db_backup_path, db_path)
            
            # Restore uploads if they exist in the backup
            uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            backup_uploads = os.path.join(temp_dir, 'static', 'uploads')
            if os.path.exists(backup_uploads):
                if os.path.exists(uploads_dir):
                    shutil.rmtree(uploads_dir)
                shutil.copytree(backup_uploads, uploads_dir)
        
        flash('System restored successfully from backup', 'success')
    except Exception as e:
        flash(f'Error restoring from backup: {str(e)}', 'error')
    
    return redirect(url_for('admin.backup_system'))

@admin.route('/admin/backup/delete/<filename>', methods=['POST'])
@login_required
@admin_required
def delete_backup(filename):
    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        backup_path = os.path.join(backup_dir, filename)
        
        if os.path.exists(backup_path):
            os.remove(backup_path)
            flash('Backup deleted successfully', 'success')
        else:
            flash('Backup file not found', 'error')
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')
    
    return redirect(url_for('admin.backup_system'))

@admin.route('/admin/backup/upload', methods=['POST'])
@login_required
@admin_required
def upload_backup():
    if 'backup_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.backup_system'))
        
    file = request.files['backup_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin.backup_system'))
        
    if not file.filename.endswith('.zip'):
        flash('Invalid file type. Only .zip files are allowed', 'error')
        return redirect(url_for('admin.backup_system'))
    
    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Save the uploaded file
        file.save(os.path.join(backup_dir, file.filename))
        flash('Backup uploaded successfully', 'success')
    except Exception as e:
        flash(f'Error uploading backup: {str(e)}', 'error')
    
    return redirect(url_for('admin.backup_system'))

@admin.route('/admin/backup/download/<filename>')
@login_required
@admin_required
def download_backup(filename):
    try:
        backup_dir = os.path.join(current_app.root_path, 'backups')
        return send_file(os.path.join(backup_dir, filename),
                        as_attachment=True,
                        download_name=filename)
    except Exception as e:
        flash(f'Error downloading backup: {str(e)}', 'error')
        return redirect(url_for('admin.backup_system')) 