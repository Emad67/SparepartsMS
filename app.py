from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from models import db, User, ExchangeRate
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
from views.profile import profile as profile_blueprint
from views.disposals import disposals as disposals_blueprint
import os
from flask.cli import with_appcontext
import click
import hashlib
import platform
import uuid
import sys
from datetime import datetime
from dotenv import load_dotenv
from utils.template_filters import register_template_filters

# Load environment variables from .env file
load_dotenv()

def get_hardware_id():
    """Generate a unique hardware ID"""
    # Use a combination of system information that is less likely to change
    system_info = platform.uname()
    
    # For Windows, use the computer name and processor information
    if platform.system() == 'Windows':
        import subprocess
        try:
            # Get the computer name (more stable than node)
            computer_name = subprocess.check_output('hostname', shell=True).decode().strip()
            
            # Get processor information
            processor_info = platform.processor()
            
            # Use these more stable identifiers
            return hashlib.sha256(f"{computer_name}{processor_info}".encode()).hexdigest()
        except:
            # Fallback to the original method if the above fails
            mac = uuid.getnode()
            return hashlib.sha256(f"{system_info.node}{mac}".encode()).hexdigest()
    else:
        # For other operating systems, use the original method
        mac = uuid.getnode()
        return hashlib.sha256(f"{system_info.node}{mac}".encode()).hexdigest()

def get_license_path():
    """Get the path to the license file in a permanent location"""
    # Use the user's home directory for Windows
    if platform.system() == 'Windows':
        home_dir = os.path.expanduser('~')
        license_dir = os.path.join(home_dir, '.spareparts')
        os.makedirs(license_dir, exist_ok=True)
        return os.path.join(license_dir, '.license')
    # For other operating systems, use the application directory
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '.license')

def validate_license():
    """Validate the software license"""
    hardware_id = get_hardware_id()
    license_file = get_license_path()
    
    print(f"Validating license...")
    print(f"Hardware ID: {hardware_id}")
    print(f"License file path: {license_file}")
    
    if not os.path.exists(license_file):
        print(f"Error: License file not found at {license_file}")
        print("Please contact: Aman Kflom (07229417) or Nesredin Abdelrahim (07546658)")
        sys.exit(1)
    
    try:
        with open(license_file, 'r') as f:
            stored_hash = f.read().strip()
            print(f"Stored license hash: {stored_hash}")
            if stored_hash != hardware_id:
                print(f"Error: License mismatch. Expected {hardware_id}, got {stored_hash}")
                print("Please contact: Aman Kflom (07229417) or Nesredin Abdelrahim (07546658)")
                sys.exit(1)
            else:
                print("License validated successfully!")
    except Exception as e:
        print(f"Error: License validation failed: {str(e)}")
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
    app.register_blueprint(profile_blueprint)
    app.register_blueprint(disposals_blueprint)

    # Add template context processor
    @app.context_processor
    def utility_processor():
        return {
            'current_year': datetime.utcnow().year,
            'ExchangeRate': ExchangeRate
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    register_template_filters(app)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)