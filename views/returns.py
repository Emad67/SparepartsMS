from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Part, Transaction
from datetime import datetime
from utils.date_utils import parse_date_range, format_date
import pytz

returns = Blueprint('returns', __name__)

@returns.route('/returns')
@login_required
def list_returns():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Transaction.query.filter_by(type='return')
    
    # Parse date range
    if start_date or end_date:
        start_datetime, end_datetime = parse_date_range(start_date, end_date)
        query = query.filter(
            Transaction.date >= start_datetime,
            Transaction.date <= end_datetime
        )
    
    # Execute query and order by date
    returns = query.order_by(Transaction.date.desc()).all()
    
    return render_template('returns/list.html', 
                         returns=returns,
                         start_date=format_date(start_datetime) if start_date else None,
                         end_date=format_date(end_datetime) if end_date else None)

@returns.route('/returns/add', methods=['GET', 'POST'])
@login_required
def add_return():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        quantity = int(request.form.get('quantity'))
        reason = request.form.get('reason')
        
        return_transaction = Transaction(
            part_id=part_id,
            type='return',
            quantity=quantity,
            price=0,  # or calculate refund amount
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            user_id=current_user.id
        )
        
        # Update stock level
        part = Part.query.get(part_id)
        part.stock_level += quantity
        
        db.session.add(return_transaction)
        db.session.commit()
        flash('Return recorded successfully')
        return redirect(url_for('returns.list_returns'))
        
    parts = Part.query.all()
    return render_template('returns/add.html', parts=parts) 