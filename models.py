from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
from sqlalchemy import event
from flask import current_app

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
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(100))
    code = db.Column(db.String(100))  # Changed from model
    substitute_part_number = db.Column(db.String(100))  # Changed from make
    stock_level = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)  # Added minimum stock level
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    length = db.Column(db.Float)
    width = db.Column(db.Float)
    color = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    description = db.Column(db.Text)
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

    def calculate_cost_price(self):
        """Calculate average cost price from purchases and credit purchases"""
        total_cost = 0
        total_quantity = 0
        
        current_app.logger.info(f"\nCalculating cost price for Part ID: {self.id}")
        current_app.logger.info(f"Initial cost price: {self.cost_price}")
        
        # Include regular purchases
        current_app.logger.info("\nRegular Purchases:")
        for purchase in self.purchases:
            current_app.logger.info(f"Purchase ID: {purchase.id}, Status: {purchase.status}, Unit Cost: {purchase.unit_cost}, Quantity: {purchase.quantity}")
            if purchase.status == 'received':
                total_cost += purchase.unit_cost * purchase.quantity
                total_quantity += purchase.quantity
        
        # Include credit purchases
        current_app.logger.info("\nCredit Purchases:")
        for credit_purchase in self.credit_purchases:
            current_app.logger.info(f"Credit Purchase ID: {credit_purchase.id}, Status: {credit_purchase.status}, Price: {credit_purchase.price}, Quantity: {credit_purchase.quantity}")
            if credit_purchase.status == 'paid':
                total_cost += credit_purchase.price * credit_purchase.quantity
                total_quantity += credit_purchase.quantity
        
        if total_quantity > 0:
            self.cost_price = total_cost / total_quantity
            current_app.logger.info(f"\nCalculation Results:")
            current_app.logger.info(f"Total cost: {total_cost}")
            current_app.logger.info(f"Total quantity: {total_quantity}")
            current_app.logger.info(f"New cost price: {self.cost_price}")
        else:
            current_app.logger.info("\nNo valid purchases found for cost price calculation")
        
        return self.cost_price

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
    loans = db.relationship('Loan', backref='customer', lazy=True)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    loan_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    returned_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # active, returned, overdue
    
    # Add relationships
    part = db.relationship('Part', backref='loans')

class CreditPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # pending, paid, overdue
    
    # Add relationships
    supplier = db.relationship('Supplier', backref='credit_purchases')
    part = db.relationship('Part', backref='credit_purchases')
    warehouse = db.relationship('Warehouse', backref='credit_purchases')

    def update_part_cost_price(self):
        """Update the part's cost price after credit purchase status changes"""
        if self.part:
            self.part.calculate_cost_price()

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    type = db.Column(db.String(20))  # purchase, sale, return
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Add relationships
    part = db.relationship('Part', backref='transactions')
    user = db.relationship('User', backref='transactions')

class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # pending, in_transit, completed, cancelled
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    items = db.relationship('TransferItem', backref='transfer', lazy=True)
    created_by = db.relationship('User', backref='created_transfers')

class TransferItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfer.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    quantity = db.Column(db.Integer)
    
    # Relationship
    part = db.relationship('Part', backref='transfer_items')

class StockAdjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
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
    
    # Relationships for transfers
    transfers_from = db.relationship('Transfer', backref='from_location', 
                                   foreign_keys='Transfer.from_location_id')
    transfers_to = db.relationship('Transfer', backref='to_location', 
                                 foreign_keys='Transfer.to_location_id')

class WarehouseStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    quantity = db.Column(db.Integer, default=0)
    
    # Add relationships
    warehouse = db.relationship('Warehouse', backref='stock_items')
    part = db.relationship('Part', backref='warehouse_stocks')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    quantity = db.Column(db.Integer)
    unit_cost = db.Column(db.Float)
    total_cost = db.Column(db.Float)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # pending, received, cancelled
    invoice_number = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    part = db.relationship('Part', backref='purchases')
    supplier = db.relationship('Supplier', backref='purchases')
    warehouse = db.relationship('Warehouse', backref='purchases')
    user = db.relationship('User', backref='purchases')
    

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
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Integer, nullable=False)
    reference_type = db.Column(db.String(20), nullable=False)  # 'purchase', 'sale', 'loan', 'return', etc.
    reference_id = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.String(200))
    
    # Relationships
    part = db.relationship('Part', backref=db.backref('bincard_entries', lazy=True))
    user = db.relationship('User', backref=db.backref('bincard_entries', lazy=True))
    
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
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    disposal_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cost = db.Column(db.Float)  # Total cost of disposed items
    
    # Relationships
    part = db.relationship('Part', backref='disposals')
    warehouse = db.relationship('Warehouse', backref='disposals')
    user = db.relationship('User', backref='disposals')

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

# Add SQLAlchemy event listeners
@event.listens_for(Purchase, 'after_insert')
@event.listens_for(Purchase, 'after_update')
def purchase_cost_price_update(mapper, connection, target):
    print(f"Event triggered for Purchase ID: {target.id}, Status: {target.status}")
    target.update_part_cost_price()

@event.listens_for(CreditPurchase, 'after_insert')
@event.listens_for(CreditPurchase, 'after_update')
def credit_purchase_cost_price_update(mapper, connection, target):
    target.update_part_cost_price()