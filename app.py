from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from models import db, User
from auth import auth as auth_blueprint
from views.dashboard import dashboard as dashboard_blueprint
from views.parts import parts as parts_blueprint
from views.categories import categories as categories_blueprint
from views.loans import loans as loans_blueprint
from views.credits import credits as credits_blueprint
from views.transfers import transfers as transfers_blueprint
from views.returns import returns as returns_blueprint
from views.reports import reports as reports_blueprint
from views.admin import admin as admin_blueprint
from views.sales import sales as sales_blueprint
from views.purchases import purchases as purchases_blueprint
from views.finance import finance as finance_blueprint
from views.messages import messages
from views.pos import pos as pos_blueprint
import os
from flask.cli import with_appcontext
import click
import hashlib
import platform
import uuid
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_hardware_id():
    """Generate a unique hardware ID"""
    system_info = platform.uname()
    mac = uuid.getnode()
    return hashlib.sha256(f"{system_info.node}{mac}".encode()).hexdigest()

def validate_license():
    """Validate the software license"""
    hardware_id = get_hardware_id()
    license_file = os.path.join(os.path.dirname(__file__), '.license')
    
    if not os.path.exists(license_file):
        print("Error: No valid license found.")
        print("Please contact: Aman Kflom (07229417) or Nesredin Abdelrahim (07546658)")
        sys.exit(1)
    
    try:
        with open(license_file, 'r') as f:
            stored_hash = f.read().strip()
            if stored_hash != hardware_id:
                print("Error: Invalid license for this machine.")
                print("Please contact: Aman Kflom (07229417) or Nesredin Abdelrahim (07546658)")
                sys.exit(1)
    except Exception:
        print("Error: License validation failed.")
        print("Please contact: Aman Kflom (07229417) or Nesredin Abdelrahim (07546658)")
        sys.exit(1)

def create_app():
    # Validate license before starting the application
    validate_license()
    
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///spms.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['DEBUG'] = True

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Custom template filters
    @app.template_filter('nl2br')
    def nl2br(value):
        if not value:
            return ''
        return value.replace('\n', '<br>')

    @app.template_filter('file_size')
    def file_size(filename):
        backup_dir = os.path.join(app.root_path, 'backups')
        file_path = os.path.join(backup_dir, filename)
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0

    # Register all blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(dashboard_blueprint)
    app.register_blueprint(parts_blueprint)
    app.register_blueprint(categories_blueprint)
    app.register_blueprint(loans_blueprint)
    app.register_blueprint(credits_blueprint)
    app.register_blueprint(transfers_blueprint)
    app.register_blueprint(returns_blueprint)
    app.register_blueprint(reports_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(sales_blueprint)
    app.register_blueprint(purchases_blueprint)
    app.register_blueprint(finance_blueprint)
    app.register_blueprint(messages)
    app.register_blueprint(pos_blueprint)

    # Add template context processor
    @app.context_processor
    def utility_processor():
        return {'current_year': datetime.utcnow().year}

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)