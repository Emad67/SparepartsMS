from app import create_app
from models import db, User, Role
import uuid
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

app = create_app()

with app.app_context():
    # Create roles
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin')
        db.session.add(admin_role)
        db.session.commit()

    # Create superuser
    super_user = User.query.filter_by(email='root1@example.com').first()
    if not super_user:
        super_user = User(email='root@example.com', fs_uniquifier=uuid.uuid4().hex, confirmed_at=datetime.now(timezone.utc))
        super_user.set_password('Emadude@123')
        db.session.add(super_user)
        db.session.commit()

    # Assign role
    if admin_role not in super_user.roles:
        super_user.roles.append(admin_role)
        db.session.commit()

    print(f"Superuser created with email: {super_user.email}")
