from app import create_app, db
from models import User
import os

def init_db():
    app = create_app()
    
    with app.app_context():
        # Drop all tables if they exist
        print("Dropping all existing tables...")
        db.drop_all()
        
        # Create all tables fresh
        print("Creating new tables...")
        db.create_all()
        
        # Create admin user if it doesn't exist
        print("Checking for admin user...")
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            print("Creating admin user...")
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            try:
                db.session.commit()
                print('Admin user has been created successfully!')
            except Exception as e:
                db.session.rollback()
                print(f'Error creating admin user: {str(e)}')
        else:
            print('Admin user already exists!')

if __name__ == '__main__':
    init_db() 