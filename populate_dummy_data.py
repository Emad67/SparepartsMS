from app import create_app
from models import db, User, Role, Part
import uuid
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

app = create_app()

with app.app_context():
    try:
        # Create roles
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            db.session.commit()
            print("Admin role created.")

        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user')
            db.session.add(user_role)
            db.session.commit()
            print("User role created.")

        # Create users
        super_user = User.query.filter_by(email='admin@example.com').first()
        if not super_user:
            super_user = User(email='admin@example.com', fs_uniquifier=uuid.uuid4().hex, confirmed_at=datetime.now(timezone.utc))
            super_user.set_password('AdminPass123')
            db.session.add(super_user)
            db.session.commit()
            super_user.roles.append(admin_role)
            db.session.commit()
            print("Superuser created.")
        else:
            if admin_role not in super_user.roles:
                super_user.roles.append(admin_role)
                db.session.commit()
                print("Admin role assigned to superuser.")

        regular_user = User.query.filter_by(email='user@example.com').first()
        if not regular_user:
            regular_user = User(email='user@example.com', fs_uniquifier=uuid.uuid4().hex, confirmed_at=datetime.now(timezone.utc))
            regular_user.set_password('UserPass123')
            db.session.add(regular_user)
            db.session.commit()
            regular_user.roles.append(user_role)
            db.session.commit()
            print("Regular user created.")

        # Create parts
        part1 = Part(name='Brake Pad', part_number='BP123', quantity=50)
        part2 = Part(name='Oil Filter', part_number='OF456', quantity=30)
        part3 = Part(name='Air Filter', part_number='AF789', quantity=20)

        db.session.add(part1)
        db.session.add(part2)
        db.session.add(part3)
        db.session.commit()
        print("Parts created.")

        print("Dummy data inserted successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
