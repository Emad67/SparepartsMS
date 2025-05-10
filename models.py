from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
from sqlalchemy import event
from flask import current_app
from utils.part_code_generator import generate_part_code

db = SQLAlchemy()

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='staff')  # admin, manager, staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)  # Renamed from is_active to active
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True, default=None)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.fs_uniquifier:
            self.fs_uniquifier = uuid.uuid4().hex

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.active  # Now returns the active column value

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parts = db.relationship('Part', backref='category', lazy=True)

class Part(db.Model):
    __tablename__ = 'parts'
    
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    stock_level = db.Column(db.Integer, default=0)
    cost_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    location = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100), nullable=False)
    quality_level = db.Column(db.String(20), nullable=False)
    code = db.Column(db.String(100))
    substitute_part_number = db.Column(db.String(100))  # Changed from make
    min_stock = db.Column(db.Integer, default=0)  # Added minimum stock level
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    length = db.Column(db.Float)
    width = db.Column(db.Float)
    color = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    unit = db.Column(db.String(20))  # piece, set, box
    min_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    cost_price = db.Column(db.Float)  # Average cost price
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    warranty_period = db.Column(db.Integer)  # in months
    barcode = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __init__(self, *args, **kwargs):
        super(Part, self).__init__(*args, **kwargs)
        if self.manufacturer and self.quality_level and self.part_number:
            self.code = generate_part_code(self.manufacturer, self.quality_level, self.part_number)
    
    def update_code(self):
        """Update the code field based on current values"""
        if self.manufacturer and self.quality_level and self.part_number:
            self.code = generate_part_code(self.manufacturer, self.quality_level, self.part_number)

    def calculate_cost_price(self):
        """Calculate average cost price from purchases and credit purchases"""
        total_cost = 0
        total_quantity = 0
        
        # Include regular purchases
        for purchase in self.purchases:
            if purchase.status == 'received':  # Only include received purchases
                total_cost += purchase.unit_cost * purchase.quantity
                total_quantity += purchase.quantity
        
        # Include credit purchases
        for credit_purchase in self.credit_purchases:
            if credit_purchase.status == 'paid':  # Only include paid credit purchases
                total_cost += credit_purchase.price * credit_purchase.quantity
                total_quantity += credit_purchase.quantity
        
        if total_quantity > 0:
            new_cost_price = total_cost / total_quantity
            self.cost_price = new_cost_price
            db.session.add(self)
            db.session.flush()
        else:
            new_cost_price = self.cost_price  # Keep the existing cost price if no valid purchases
        
        return new_cost_price

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    payment_terms = db.Column(db.Text)
    parts = db.relationship('Part', backref='supplier', lazy=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    # The loans relationship is defined in the Loan model

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    loan_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    returned_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # active, returned, overdue
    
    # Add relationships with explicit foreign keys and primaryjoin
    part = db.relationship('Part', 
                         backref=db.backref('loans', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='Loan.part_id == Part.id')
    
    customer = db.relationship('Customer', 
                             backref=db.backref('loans', lazy=True),
                             foreign_keys=[customer_id],
                             primaryjoin='Loan.customer_id == Customer.id')

class CreditPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # pending, paid, overdue
    voided = db.Column(db.Boolean, default=False)
    
    # Add relationships with explicit foreign keys and primaryjoin
    supplier = db.relationship('Supplier', 
                             backref=db.backref('credit_purchases', lazy=True),
                             foreign_keys=[supplier_id],
                             primaryjoin='CreditPurchase.supplier_id == Supplier.id')
    
    part = db.relationship('Part', 
                         backref=db.backref('credit_purchases', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='CreditPurchase.part_id == Part.id')
    
    warehouse = db.relationship('Warehouse', 
                              backref=db.backref('credit_purchases', lazy=True),
                              foreign_keys=[warehouse_id],
                              primaryjoin='CreditPurchase.warehouse_id == Warehouse.id')

    def update_part_cost_price(self):
        """Update the part's cost price after credit purchase status changes"""
        if self.part:
            self.part.calculate_cost_price()

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    type = db.Column(db.String(20))  # purchase, sale, return
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20))  # pending, paid, overdue
    voided = db.Column(db.Boolean, default=False)
    
    # Relationships with explicit foreign keys and primaryjoin
    part = db.relationship('Part', 
                         backref=db.backref('transactions', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='Transaction.part_id == Part.id')
    
    user = db.relationship('User', 
                         backref=db.backref('transactions', lazy=True),
                         foreign_keys=[user_id],
                         primaryjoin='Transaction.user_id == User.id')

class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    to_location_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # pending, in_transit, completed, cancelled
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    items = db.relationship('TransferItem', backref='transfer', lazy=True)
    created_by = db.relationship('User', backref='created_transfers')
    from_location = db.relationship('Warehouse', foreign_keys=[from_location_id], backref='transfers_from')
    to_location = db.relationship('Warehouse', foreign_keys=[to_location_id], backref='transfers_to')

class TransferItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfer.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    quantity = db.Column(db.Integer)
    
    # Relationship with explicit foreign keys and primaryjoin
    part = db.relationship('Part', 
                         backref=db.backref('transfer_items', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='TransferItem.part_id == Part.id')

class StockAdjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    quantity_change = db.Column(db.Integer)
    reason = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Location {self.name}>'

class WarehouseStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Note: using 'parts' table name
    quantity = db.Column(db.Integer, default=0)
    
    # Add relationships with explicit foreign keys and primaryjoin
    warehouse = db.relationship('Warehouse', 
                              backref=db.backref('stock_items', lazy=True),
                              foreign_keys=[warehouse_id],
                              primaryjoin='WarehouseStock.warehouse_id == Warehouse.id')
    
    part = db.relationship('Part', 
                          backref=db.backref('warehouse_stocks', lazy=True),
                          foreign_keys=[part_id],
                          primaryjoin='WarehouseStock.part_id == Part.id')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    quantity = db.Column(db.Integer)
    unit_cost = db.Column(db.Float)
    total_cost = db.Column(db.Float)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # pending, received, cancelled
    invoice_number = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    voided = db.Column(db.Boolean, default=False)  # Added voided field
    
    # Add relationships with explicit foreign keys and primaryjoin
    part = db.relationship('Part', 
                         backref=db.backref('purchases', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='Purchase.part_id == Part.id')
    
    supplier = db.relationship('Supplier', 
                             backref=db.backref('purchases', lazy=True),
                             foreign_keys=[supplier_id],
                             primaryjoin='Purchase.supplier_id == Supplier.id')
    
    warehouse = db.relationship('Warehouse', 
                              backref=db.backref('purchases', lazy=True),
                              foreign_keys=[warehouse_id],
                              primaryjoin='Purchase.warehouse_id == Warehouse.id')
    
    user = db.relationship('User', 
                         backref=db.backref('purchases', lazy=True),
                         foreign_keys=[user_id],
                         primaryjoin='Purchase.user_id == User.id')

    def update_part_cost_price(self):
        """Update the part's cost price after purchase status changes"""
        if self.part:
            print(f"Updating cost price for part: {self.part.name}")
            self.part.calculate_cost_price()
            #db.session.add(self.part)

class FinancialTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(20))  # revenue, expense
    category = db.Column(db.String(50))  # utilities, salary, Water, Electricity, etc.
    amount = db.Column(db.Float)
    description = db.Column(db.Text)
    reference_id = db.Column(db.String(50))  # Reference to related transaction (sale_id, purchase_id, etc.)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # New fields for voiding functionality
    voided = db.Column(db.Boolean, default=False)
    void_reason = db.Column(db.Text)
    voided_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    voided_at = db.Column(db.DateTime)
    void_reference_id = db.Column(db.Integer, db.ForeignKey('financial_transaction.id'))  # Reference to the reversing entry
    
    # Add new field for storing the exchange rate at time of transaction
    exchange_rate = db.Column(db.Float)
    
    # Relationships
    user = db.relationship('User', backref='financial_transactions', foreign_keys=[user_id])
    voided_by = db.relationship('User', backref='voided_transactions', foreign_keys=[voided_by_id])
    void_reference = db.relationship('FinancialTransaction', backref='original_transaction',
                                   remote_side=[id], foreign_keys=[void_reference_id])
    
    def get_amount_ern(self):
        """Get amount in ERN using historical exchange rate"""
        return self.amount * (self.exchange_rate or ExchangeRate.get_rate_for_date(self.date))
    
    @property
    def amount_ern(self):
        return self.get_amount_ern()

class BinCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)  # Changed from 'part.id' to 'parts.id'
    transaction_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Integer, nullable=False)
    reference_type = db.Column(db.String(20), nullable=False)  # 'purchase', 'sale', 'loan', 'return', etc.
    reference_id = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.String(200))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)  # Fixed table name from 'warehouses' to 'warehouse'
    
    # Relationships with explicit foreign keys and primaryjoin
    part = db.relationship('Part', 
                         backref=db.backref('bincard_entries', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='BinCard.part_id == Part.id')
    
    user = db.relationship('User', 
                         backref=db.backref('bincard_entries', lazy=True),
                         foreign_keys=[user_id],
                         primaryjoin='BinCard.user_id == User.id')
    
    warehouse = db.relationship('Warehouse',  # Add warehouse relationship
                              backref=db.backref('bincard_entries', lazy=True),
                              foreign_keys=[warehouse_id],
                              primaryjoin='BinCard.warehouse_id == Warehouse.id')
    
    def __repr__(self):
        return f'<BinCard {self.id}: {self.transaction_type} {self.quantity} of Part {self.part_id}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    
    def __repr__(self):
        return f'<Message {self.id}: {self.subject}>'

class Disposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'))  # Changed from 'part.id' to 'parts.id'
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    disposal_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cost = db.Column(db.Float)  # Total cost of disposed items
    
    # Relationships with explicit foreign keys and primaryjoin
    part = db.relationship('Part', 
                         backref=db.backref('disposals', lazy=True),
                         foreign_keys=[part_id],
                         primaryjoin='Disposal.part_id == Part.id')
    
    warehouse = db.relationship('Warehouse', 
                              backref=db.backref('disposals', lazy=True),
                              foreign_keys=[warehouse_id],
                              primaryjoin='Disposal.warehouse_id == Warehouse.id')
    
    user = db.relationship('User', 
                         backref=db.backref('disposals', lazy=True),
                         foreign_keys=[user_id],
                         primaryjoin='Disposal.user_id == User.id')

class ExchangeRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='exchange_rates')
    
    @staticmethod
    def get_rate_for_date(date=None):
        if date is None:
            date = datetime.utcnow()
        rate = ExchangeRate.query.filter(
            ExchangeRate.effective_from <= date
        ).order_by(ExchangeRate.effective_from.desc()).first()
        return rate.rate if rate else 15.0  # Default rate

class PartName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

# # Add SQLAlchemy event listeners
# @event.listens_for(Purchase, 'after_insert')
# @event.listens_for(Purchase, 'after_update')
# def purchase_cost_price_update(mapper, connection, target):
#     """Update part cost price when purchase is created or updated"""
#     if target.part:
#         current_app.logger.info(f"Event triggered for Purchase ID: {target.id}")
#         target.part.calculate_cost_price()
#         db.session.add(target.part)
#         db.session.flush()

# @event.listens_for(CreditPurchase, 'after_insert')
# @event.listens_for(CreditPurchase, 'after_update')
# def credit_purchase_cost_price_update(mapper, connection, target):
#     """Update part cost price when credit purchase is created or updated"""
#     if target.part:
#         current_app.logger.info(f"Event triggered for Credit Purchase ID: {target.id}")
#         target.part.calculate_cost_price()
#         db.session.add(target.part)
#         db.session.flush()

# @event.listens_for(Transaction, 'after_insert')
# @event.listens_for(Transaction, 'after_update')
# def transaction_cost_price_update(mapper, connection, target):
#     """Update part cost price when transaction is created or updated"""
#     if target.part and target.type == 'sale':
#         current_app.logger.info(f"Event triggered for Transaction ID: {target.id}")
#         target.part.calculate_cost_price()
#         db.session.add(target.part)
#         db.session.flush()
#         db.session.add(target.part)
#         db.session.flush()