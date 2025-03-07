from app import create_app, db
from sqlalchemy import text

def reset_db():
    app = create_app()
    
    with app.app_context():
        # Drop all tables including alembic_version
        with db.engine.connect() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
            conn.commit()
        
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        print("Database has been reset successfully!")

if __name__ == '__main__':
    reset_db() 