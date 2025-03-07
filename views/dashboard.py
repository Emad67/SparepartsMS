from flask import Blueprint, render_template, current_app
from flask_login import login_required
from models import Part, Transaction, Loan, CreditPurchase, db
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/')
@login_required
def index():
    try:
        # Basic statistics
        total_parts = Part.query.count()
        low_stock_parts = Part.query.filter(Part.stock_level < 10).count()
        active_loans = Loan.query.filter_by(status='active').count()
        pending_credits = CreditPurchase.query.filter_by(status='pending').count()
        
        # Recent transactions
        recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(5).all()
        
        # Sales data for chart (last 7 days)
        sales_data = []
        sales_dates = []
        for i in range(7):
            date = datetime.utcnow().date() - timedelta(days=i)
            sales_sum = db.session.query(func.sum(Transaction.price))\
                .filter(Transaction.type == 'sale',
                       func.date(Transaction.date) == date).scalar() or 0
            sales_data.insert(0, float(sales_sum))
            sales_dates.insert(0, date.strftime('%Y-%m-%d'))
        
        # Stock levels data for chart (top 10 parts)
        top_parts = Part.query.order_by(Part.stock_level.desc()).limit(10).all()
        stock_labels = [part.name for part in top_parts]
        stock_levels = [part.stock_level for part in top_parts]
        
        return render_template('dashboard/index.html',
                             total_parts=total_parts,
                             low_stock_parts=low_stock_parts,
                             active_loans=active_loans,
                             pending_credits=pending_credits,
                             recent_transactions=recent_transactions,
                             sales_dates=sales_dates,
                             sales_data=sales_data,
                             stock_labels=stock_labels,
                             stock_levels=stock_levels)
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        return render_template('errors/500.html'), 500 