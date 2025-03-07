from app import create_app, db
from models import (Category, Part, Supplier, Customer, Warehouse, User, 
                   Loan, Purchase, Transaction, CreditPurchase, Transfer,
                   TransferItem, Location)
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import uuid

def insert_sample_data():
    app = create_app()
    
    with app.app_context():
        # Create sample suppliers
        supplier_data = [
            {
                'name': 'ABC Electronics',
                'contact_person': 'John Doe',
                'email': 'john@abcelectronics.com',
                'phone': '555-0100',
                'address': '123 Main St, City',
                'payment_terms': 'Net 30'
            },
            {
                'name': 'XYZ Parts Ltd',
                'contact_person': 'Jane Smith',
                'email': 'jane@xyzparts.com',
                'phone': '555-0200',
                'address': '456 Oak Ave, Town',
                'payment_terms': 'Net 45'
            },
            {
                'name': 'Global Auto Parts',
                'contact_person': 'Mike Johnson',
                'email': 'mike@globalauto.com',
                'phone': '555-0300',
                'address': '789 Pine St, City',
                'payment_terms': 'Net 60'
            },
            {
                'name': 'Tech Components Inc',
                'contact_person': 'Sarah Wilson',
                'email': 'sarah@techcomp.com',
                'phone': '555-0400',
                'address': '321 Maple Dr, Town',
                'payment_terms': 'Net 30'
            }
        ]
        
        suppliers = []
        for data in supplier_data:
            supplier = Supplier.query.filter_by(name=data['name']).first()
            if not supplier:
                supplier = Supplier(**data)
                db.session.add(supplier)
            suppliers.append(supplier)
        db.session.commit()

        # Create sample categories
        category_data = [
            {'name': 'Electronics', 'description': 'Electronic components and parts'},
            {'name': 'Mechanical', 'description': 'Mechanical parts and components'},
            {'name': 'Tools', 'description': 'Tools and equipment'},
            {'name': 'Electrical', 'description': 'Electrical components and wiring'},
            {'name': 'Hydraulics', 'description': 'Hydraulic systems and components'},
            {'name': 'Safety Equipment', 'description': 'Personal protective equipment and safety gear'}
        ]
        
        categories = []
        for data in category_data:
            category = Category.query.filter_by(name=data['name']).first()
            if not category:
                category = Category(**data)
                db.session.add(category)
            categories.append(category)
        db.session.commit()

        # Create sample locations
        location_data = [
            {
                'name': 'Main Warehouse',
                'address': '1000 Storage Drive, Industrial Park',
                'contact_person': 'Robert Brown',
                'phone': '555-0500',
                'email': 'robert@mainwarehouse.com'
            },
            {
                'name': 'Downtown Branch',
                'address': '250 Market St, Downtown',
                'contact_person': 'Lisa Chen',
                'phone': '555-0600',
                'email': 'lisa@downtown.com'
            },
            {
                'name': 'East Wing Storage',
                'address': '789 East Road, Industrial Zone',
                'contact_person': 'David Miller',
                'phone': '555-0700',
                'email': 'david@eastwing.com'
            }
        ]

        locations = []
        for data in location_data:
            location = Location.query.filter_by(name=data['name']).first()
            if not location:
                location = Location(**data)
                db.session.add(location)
            locations.append(location)
        db.session.commit()

        # Create sample parts
        part_data = [
            {
                'part_number': 'EL001',
                'name': 'Circuit Board',
                'location': 'Shelf A1',
                'model': 'CB-2023',
                'make': 'ABC Electronics',
                'stock_level': 50,
                'min_stock': 10,
                'weight': 0.2,
                'height': 10,
                'length': 15,
                'width': 10,
                'color': 'Green',
                'unit': 'piece',
                'min_price': 25.00,
                'max_price': 35.00,
                'category_id': categories[0].id,
                'supplier_id': suppliers[0].id,
                'warranty_period': 12,
                'barcode': '1234567890'
            },
            {
                'part_number': 'ME001',
                'name': 'Bearing Assembly',
                'location': 'Shelf B2',
                'model': 'BA-2023',
                'make': 'XYZ Parts',
                'stock_level': 30,
                'min_stock': 5,
                'weight': 0.5,
                'height': 5,
                'length': 5,
                'width': 5,
                'color': 'Silver',
                'unit': 'piece',
                'min_price': 15.00,
                'max_price': 25.00,
                'category_id': categories[1].id,
                'supplier_id': suppliers[1].id,
                'warranty_period': 6,
                'barcode': '0987654321'
            },
            {
                'part_number': 'HY001',
                'name': 'Hydraulic Pump',
                'location': 'Shelf C3',
                'model': 'HP-2023',
                'make': 'Global Auto Parts',
                'stock_level': 15,
                'min_stock': 3,
                'weight': 2.5,
                'height': 20,
                'length': 25,
                'width': 15,
                'color': 'Blue',
                'unit': 'piece',
                'min_price': 150.00,
                'max_price': 200.00,
                'category_id': categories[4].id,
                'supplier_id': suppliers[2].id,
                'warranty_period': 24,
                'barcode': '5678901234'
            },
            {
                'part_number': 'SF001',
                'name': 'Safety Helmet',
                'location': 'Shelf D4',
                'model': 'SH-2023',
                'make': 'Tech Components Inc',
                'stock_level': 100,
                'min_stock': 20,
                'weight': 0.4,
                'height': 25,
                'length': 20,
                'width': 18,
                'color': 'Yellow',
                'unit': 'piece',
                'min_price': 35.00,
                'max_price': 45.00,
                'category_id': categories[5].id,
                'supplier_id': suppliers[3].id,
                'warranty_period': 12,
                'barcode': '9876543210'
            }
        ]
        
        parts = []
        for data in part_data:
            part = Part.query.filter_by(part_number=data['part_number']).first()
            if not part:
                part = Part(**data)
                db.session.add(part)
            parts.append(part)
        db.session.commit()

        # Create sample customers
        customer_data = [
            {
                'name': 'Acme Industries',
                'email': 'contact@acme.com',
                'phone': '555-0800',
                'address': '789 Pine St, Village'
            },
            {
                'name': 'Tech Solutions Inc',
                'email': 'info@techsolutions.com',
                'phone': '555-0900',
                'address': '321 Elm St, County'
            },
            {
                'name': 'Manufacturing Pro',
                'email': 'info@mpro.com',
                'phone': '555-1000',
                'address': '456 Industrial Ave, City'
            },
            {
                'name': 'Construction Corp',
                'email': 'contact@constructioncorp.com',
                'phone': '555-1100',
                'address': '789 Builder St, Town'
            }
        ]
        
        customers = []
        for data in customer_data:
            customer = Customer.query.filter_by(name=data['name']).first()
            if not customer:
                customer = Customer(**data)
                db.session.add(customer)
            customers.append(customer)
        db.session.commit()

        # Create sample warehouse
        warehouse = Warehouse.query.filter_by(name='Main Storage').first()
        if not warehouse:
            warehouse = Warehouse(
                name='Main Storage',
                location='1000 Storage Drive'
            )
            db.session.add(warehouse)
            db.session.commit()

        # Create sample loans
        loan_data = [
            {
                'customer_id': customers[0].id,
                'part_id': parts[0].id,
                'quantity': 2,
                'loan_date': datetime.utcnow(),
                'due_date': datetime.utcnow() + timedelta(days=7),
                'status': 'active'
            },
            {
                'customer_id': customers[1].id,
                'part_id': parts[1].id,
                'quantity': 1,
                'loan_date': datetime.utcnow() - timedelta(days=5),
                'due_date': datetime.utcnow() + timedelta(days=2),
                'status': 'active'
            },
            {
                'customer_id': customers[2].id,
                'part_id': parts[2].id,
                'quantity': 3,
                'loan_date': datetime.utcnow() - timedelta(days=10),
                'due_date': datetime.utcnow() - timedelta(days=3),
                'status': 'overdue'
            }
        ]
        
        for data in loan_data:
            existing_loan = Loan.query.filter_by(
                customer_id=data['customer_id'],
                part_id=data['part_id'],
                status=data['status']
            ).first()
            if not existing_loan:
                loan = Loan(**data)
                db.session.add(loan)
        db.session.commit()

        # Create sample transfers
        transfer_data = [
            {
                'reference_number': f'TRF-{uuid.uuid4().hex[:8].upper()}',
                'from_location_id': locations[0].id,
                'to_location_id': locations[1].id,
                'status': 'completed',
                'created_by_id': User.query.filter_by(role='admin').first().id
            },
            {
                'reference_number': f'TRF-{uuid.uuid4().hex[:8].upper()}',
                'from_location_id': locations[1].id,
                'to_location_id': locations[2].id,
                'status': 'pending',
                'created_by_id': User.query.filter_by(role='admin').first().id
            }
        ]

        for data in transfer_data:
            transfer = Transfer(**data)
            db.session.add(transfer)
            db.session.commit()

            # Add transfer items
            transfer_items = [
                {
                    'transfer_id': transfer.id,
                    'part_id': parts[0].id,
                    'quantity': 5
                },
                {
                    'transfer_id': transfer.id,
                    'part_id': parts[1].id,
                    'quantity': 3
                }
            ]
            
            for item_data in transfer_items:
                transfer_item = TransferItem(**item_data)
                db.session.add(transfer_item)
        db.session.commit()

        # Create sample purchases
        admin_user = User.query.filter_by(role='admin').first()
        purchase_data = [
            {
                'part_id': parts[0].id,
                'supplier_id': suppliers[0].id,
                'quantity': 10,
                'unit_cost': 20.00,
                'total_cost': 200.00,
                'purchase_date': datetime.utcnow() - timedelta(days=10),
                'status': 'received',
                'invoice_number': 'INV-001',
                'user_id': admin_user.id
            },
            {
                'part_id': parts[1].id,
                'supplier_id': suppliers[1].id,
                'quantity': 15,
                'unit_cost': 12.00,
                'total_cost': 180.00,
                'purchase_date': datetime.utcnow() - timedelta(days=5),
                'status': 'pending',
                'invoice_number': 'INV-002',
                'user_id': admin_user.id
            },
            {
                'part_id': parts[2].id,
                'supplier_id': suppliers[2].id,
                'quantity': 8,
                'unit_cost': 160.00,
                'total_cost': 1280.00,
                'purchase_date': datetime.utcnow() - timedelta(days=3),
                'status': 'received',
                'invoice_number': 'INV-003',
                'user_id': admin_user.id
            }
        ]
        
        for data in purchase_data:
            existing_purchase = Purchase.query.filter_by(invoice_number=data['invoice_number']).first()
            if not existing_purchase:
                purchase = Purchase(**data)
                db.session.add(purchase)
        db.session.commit()

        # Create sample transactions (sales)
        transaction_data = [
            {
                'part_id': parts[0].id,
                'type': 'sale',
                'quantity': 5,
                'price': 30.00,
                'date': datetime.utcnow() - timedelta(days=3),
                'user_id': admin_user.id
            },
            {
                'part_id': parts[1].id,
                'type': 'sale',
                'quantity': 3,
                'price': 20.00,
                'date': datetime.utcnow() - timedelta(days=1),
                'user_id': admin_user.id
            },
            {
                'part_id': parts[2].id,
                'type': 'sale',
                'quantity': 2,
                'price': 180.00,
                'date': datetime.utcnow(),
                'user_id': admin_user.id
            }
        ]
        
        for data in transaction_data:
            transaction = Transaction(**data)
            db.session.add(transaction)
        db.session.commit()

        print("Sample data has been inserted successfully!")

if __name__ == '__main__':
    insert_sample_data()