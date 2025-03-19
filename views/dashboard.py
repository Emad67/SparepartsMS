from flask import Blueprint, render_template, current_app
from flask_login import login_required
from models import Part, Transaction, Loan, CreditPurchase, db
from datetime import datetime, timedelta
from sqlalchemy import func
from utils.date_utils import get_start_of_day, get_end_of_day, format_date

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/')
@login_required
def index():
    try:
        today = datetime.utcnow().date()
        today_start = get_start_of_day(datetime.utcnow())
        today_end = get_end_of_day(datetime.utcnow())
        
        # Today's sales total
        today_sales = db.session.query(func.sum(Transaction.price * Transaction.quantity))\
            .filter(Transaction.type == 'sale',
                   Transaction.date >= today_start,
                   Transaction.date <= today_end).scalar() or 0
        
        # Low stock parts
        low_stock_parts = Part.query.filter(Part.stock_level < 10).count()
        
        # Active loans
        active_loans = Loan.query.filter_by(status='active').count()
        
        # Pending credits
        pending_credits = CreditPurchase.query.filter_by(status='pending').count()
        
        # Sales data for chart (last 7 days)
        sales_data = []
        sales_dates = []
        for i in range(7):
            date = today - timedelta(days=i)
            date_start = get_start_of_day(datetime.combine(date, datetime.min.time()))
            date_end = get_end_of_day(datetime.combine(date, datetime.min.time()))
            sales_sum = db.session.query(func.sum(Transaction.price * Transaction.quantity))\
                .filter(Transaction.type == 'sale',
                       Transaction.date >= date_start,
                       Transaction.date <= date_end).scalar() or 0
            sales_data.insert(0, float(sales_sum))
            sales_dates.insert(0, format_date(date_start))
        
        # Low stock parts data for chart
        low_stock_parts_data = Part.query.filter(Part.stock_level < 10)\
            .order_by(Part.stock_level).limit(10).all()
        stock_labels = [part.name for part in low_stock_parts_data]
        stock_levels = [part.stock_level for part in low_stock_parts_data]
        
        return render_template('dashboard/index.html',
                             today=format_date(datetime.utcnow()),
                             total_parts=today_sales,
                             low_stock_parts=low_stock_parts,
                             active_loans=active_loans,
                             pending_credits=pending_credits,
                             sales_dates=sales_dates,
                             sales_data=sales_data,
                             stock_labels=stock_labels,
                             stock_levels=stock_levels)
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        return render_template('errors/500.html'), 500