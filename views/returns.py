from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Part, Transaction
from datetime import datetime

returns = Blueprint('returns', __name__)

@returns.route('/returns')
@login_required
def list_returns():
    returns = Transaction.query.filter_by(type='return').order_by(Transaction.date.desc()).all()
    return render_template('returns/list.html', returns=returns)

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
            date=datetime.utcnow(),
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