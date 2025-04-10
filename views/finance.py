from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db, FinancialTransaction, Transaction, Purchase, ExchangeRate, WarehouseStock, BinCard, CreditPurchase
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps
from io import BytesIO
from utils.date_utils import (
    parse_date_range, format_date, format_datetime,
    get_start_of_day, get_end_of_day, get_date_range
)

finance = Blueprint('finance', __name__)

def finance_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager']:
            flash('You need to be an admin or manager to access financial management.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this feature.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@finance.route('/finance')
@login_required
@finance_access_required
def index():
    # Get date range for summary
    start_date, end_date = get_date_range(days=30)
    
    # Get summary statistics
    revenue = db.session.query(func.sum(FinancialTransaction.amount))\
        .filter(FinancialTransaction.type == 'revenue')\
        .filter(FinancialTransaction.date >= start_date).scalar() or 0
        
    expenses = db.session.query(func.sum(FinancialTransaction.amount))\
        .filter(FinancialTransaction.type == 'expense')\
        .filter(FinancialTransaction.date >= start_date).scalar() or 0
    
    # Get recent transactions
    recent_transactions = FinancialTransaction.query\
        .order_by(FinancialTransaction.date.desc())\
        .limit(10)\
        .all()
    
    # Add exchange rate to the context
    current_rate = ExchangeRate.get_rate_for_date()
    
    net_profit = revenue - expenses
    
    return render_template('finance/index.html',
                         total_revenue=revenue,
                         total_expenses=expenses,
                         net_profit=net_profit,
                         recent_transactions=recent_transactions,
                         current_rate=current_rate)

@finance.route('/finance/transactions')
@login_required
@finance_access_required
def list_transactions():
    # Get filter parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    trans_type = request.args.get('type')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Build query
    query = FinancialTransaction.query
    
    if start_datetime:
        query = query.filter(func.date(FinancialTransaction.date) >= start_datetime.date())
    if end_datetime:
        query = query.filter(func.date(FinancialTransaction.date) <= end_datetime.date())
    if trans_type:
        query = query.filter(FinancialTransaction.type == trans_type)
    
    transactions = query.order_by(FinancialTransaction.date.desc()).all()
    
    # Calculate totals for the filtered transactions
    total_revenue = sum(t.amount for t in transactions if t.type == 'revenue')
    total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
    
    return render_template('finance/transactions.html', 
                         transactions=transactions,
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime))

@finance.route('/finance/add', methods=['GET', 'POST'])
@login_required
@finance_access_required
def add_transaction():
    if request.method == 'POST':
        # Get current exchange rate
        current_rate = ExchangeRate.get_rate_for_date()
        
        transaction = FinancialTransaction(
            type=request.form.get('type'),
            category=request.form.get('category'),
            amount=float(request.form.get('amount')),
            description=request.form.get('description'),
            reference_id=request.form.get('reference_id'),
            date=datetime.utcnow(),
            user_id=current_user.id,
            exchange_rate=current_rate  # Add exchange rate
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction added successfully.', 'success')
        return redirect(url_for('finance.list_transactions'))
    
    return render_template('finance/add.html')

@finance.route('/finance/report')
@login_required
@finance_access_required
def report():
    # Get filter parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    days = int(request.args.get('days', 30))
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str, days)
    
    # Get daily totals
    daily_totals = db.session.query(
        func.date(FinancialTransaction.date).label('date'),
        FinancialTransaction.type,
        func.sum(FinancialTransaction.amount).label('amount')
    ).filter(
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime
    ).group_by(
        'date',
        FinancialTransaction.type
    ).all()
    
    # Get category totals
    category_totals = db.session.query(
        FinancialTransaction.category,
        FinancialTransaction.type,
        func.sum(FinancialTransaction.amount).label('amount')
    ).filter(
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime
    ).group_by(
        FinancialTransaction.category,
        FinancialTransaction.type
    ).all()
    
    # Process data for charts
    dates = sorted(list(set(str(date) for date, _, _ in daily_totals)))
    categories = sorted(list(set(cat for cat, _, _ in category_totals if cat)))
    
    # Daily data
    revenues = []
    expenses = []
    for date in dates:
        revenue = next((amount for d, t, amount in daily_totals 
                       if str(d) == date and t == 'revenue'), 0)
        expense = next((amount for d, t, amount in daily_totals 
                       if str(d) == date and t == 'expense'), 0)
        revenues.append(float(revenue) if revenue else 0)
        expenses.append(float(expense) if expense else 0)
    
    # Category data
    category_revenues = []
    category_expenses = []
    for category in categories:
        revenue = next((float(amount) for cat, t, amount in category_totals 
                       if cat == category and t == 'revenue'), 0)
        expense = next((float(amount) for cat, t, amount in category_totals 
                       if cat == category and t == 'expense'), 0)
        category_revenues.append(revenue)
        category_expenses.append(expense)
    
    chart_data = {
        'dates': dates,
        'revenues': revenues,
        'expenses': expenses,
        'categories': categories,
        'categoryRevenues': category_revenues,
        'categoryExpenses': category_expenses
    }
    
    # Calculate totals
    total_revenue = sum(revenues)
    total_expenses = sum(expenses)
    profit = total_revenue - total_expenses
    
    return render_template('finance/report.html',
                         chart_data=chart_data,
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         profit=profit,
                         daily_totals=daily_totals,
                         category_totals=category_totals,
                         days=days,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime))

@finance.route('/finance/revenue')
@login_required
@finance_access_required
def revenue():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    revenues = FinancialTransaction.query.filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime,
        FinancialTransaction.voided == False
    ).order_by(FinancialTransaction.date.desc()).all()
    
    total_revenue = sum(rev.amount for rev in revenues)
    daily_revenue = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime,
        FinancialTransaction.voided == False
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Prepare data for the chart
    dates = [str(date) for date, _ in daily_revenue]
    amounts = [float(amount) for _, amount in daily_revenue]
    
    return render_template('finance/revenue.html',
                         revenues=revenues,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_revenue=total_revenue,
                         dates=dates,
                         amounts=amounts)

@finance.route('/finance/expenses')
@login_required
@finance_access_required
def expenses():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    expenses = FinancialTransaction.query.filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime,
        FinancialTransaction.voided == False
    ).order_by(FinancialTransaction.date.desc()).all()
    
    total_expenses = sum(exp.amount for exp in expenses)
    daily_expenses = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime,
        FinancialTransaction.voided == False
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Prepare data for the chart
    dates = [str(date) for date, _ in daily_expenses]
    amounts = [float(amount) for _, amount in daily_expenses]
    
    return render_template('finance/expenses.html',
                         expenses=expenses,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_expenses=total_expenses,
                         dates=dates,
                         amounts=amounts)

@finance.route('/finance/profit')
@login_required
@finance_access_required
def profit():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Get daily totals for both revenue and expenses
    daily_totals = db.session.query(
        func.date(FinancialTransaction.date).label('date'),
        FinancialTransaction.type,
        func.sum(FinancialTransaction.amount).label('amount')
    ).filter(
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime,
        FinancialTransaction.voided == False
    ).group_by(
        'date',
        FinancialTransaction.type
    ).all()
    
    # Process data for charts
    dates = sorted(list(set(str(date) for date, _, _ in daily_totals)))
    
    # Initialize data arrays
    revenues = []
    expenses = []
    profits = []
    daily_profits = []
    
    # Calculate daily totals
    for date in dates:
        revenue = next((float(amount) for d, t, amount in daily_totals 
                       if str(d) == date and t == 'revenue'), 0)
        expense = next((float(amount) for d, t, amount in daily_totals 
                       if str(d) == date and t == 'expense'), 0)
        profit = revenue - expense
        
        revenues.append(revenue)
        expenses.append(expense)
        profits.append(profit)
        daily_profits.append((date, revenue, expense, profit))
    
    # Calculate overall totals
    total_revenue = sum(revenues)
    total_expenses = sum(expenses)
    total_profit = total_revenue - total_expenses
    
    return render_template('finance/profit.html',
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         dates=dates,
                         revenues=revenues,
                         expenses=expenses,
                         profits=profits,
                         daily_profits=daily_profits,
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         total_profit=total_profit)

@finance.route('/finance/export/<report_type>/<format>')
@login_required
@finance_access_required
def export(report_type, format):
    if format not in ['csv', 'pdf']:
        return 'Invalid format', 400

    if format == 'csv':
        return export_csv(report_type)
    else:
        return export_pdf(report_type)

def export_csv(report_type):
    buffer = BytesIO()
    buffer.write(b'\xef\xbb\xbf')
    
    # Write report header
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    buffer.write(f'Report Type: {report_type.title()} Report\n'.encode('utf-8'))
    buffer.write(f'Generated on: {current_date}\n'.encode('utf-8'))
    buffer.write('\n'.encode('utf-8'))
    
    if report_type == 'revenue':
        revenues = FinancialTransaction.query.filter_by(type='revenue').all()
        buffer.write('Date,Category,Amount,Description,Reference,Recorded By\n'.encode('utf-8'))
        total_revenue = 0
        for revenue in revenues:
            row = f'{revenue.date.strftime("%Y-%m-%d")},{revenue.category},{revenue.amount:.2f},{revenue.description},{revenue.reference_id},{revenue.user.username}\n'
            buffer.write(row.encode('utf-8'))
            total_revenue += revenue.amount
        
        # Write total at the bottom
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Total Revenue:,,,,,${total_revenue:.2f}\n'.encode('utf-8'))
    
    elif report_type == 'expenses':
        expenses = FinancialTransaction.query.filter_by(type='expense').all()
        buffer.write('Date,Category,Amount,Description,Reference,Recorded By\n'.encode('utf-8'))
        total_expenses = 0
        for expense in expenses:
            row = f'{expense.date.strftime("%Y-%m-%d")},{expense.category},{expense.amount:.2f},{expense.description},{expense.reference_id},{expense.user.username}\n'
            buffer.write(row.encode('utf-8'))
            total_expenses += expense.amount
        
        # Write total at the bottom
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Total Expenses:,,,,,${total_expenses:.2f}\n'.encode('utf-8'))
    
    elif report_type == 'profit':
        transactions = FinancialTransaction.query.all()
        buffer.write('Date,Revenue,Expenses,Profit,Profit Margin\n'.encode('utf-8'))
        
        # Group transactions by date
        daily_totals = {}
        total_revenue = 0
        total_expenses = 0
        
        for trans in transactions:
            date = trans.date.strftime("%Y-%m-%d")
            if date not in daily_totals:
                daily_totals[date] = {'revenue': 0, 'expenses': 0}
            if trans.type == 'revenue':
                daily_totals[date]['revenue'] += trans.amount
                total_revenue += trans.amount
            else:
                daily_totals[date]['expenses'] += trans.amount
                total_expenses += trans.amount
        
        for date, totals in sorted(daily_totals.items()):
            revenue = totals['revenue']
            expenses = totals['expenses']
            profit = revenue - expenses
            margin = (profit / revenue * 100) if revenue > 0 else 0
            row = f'{date},{revenue:.2f},{expenses:.2f},{profit:.2f},{margin:.1f}%\n'
            buffer.write(row.encode('utf-8'))
        
        # Write totals at the bottom
        total_profit = total_revenue - total_expenses
        total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Totals,${total_revenue:.2f},${total_expenses:.2f},${total_profit:.2f},{total_margin:.1f}%\n'.encode('utf-8'))
    
    else:
        return 'Invalid report type', 400

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{report_type}_report_{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

def export_pdf(report_type):
    if report_type == 'revenue':
        revenues = FinancialTransaction.query.filter_by(type='revenue').all()
        headers = ['Date', 'Category', 'Amount', 'Description', 'Reference', 'Recorded By']
        data = [
            [
                revenue.date.strftime("%Y-%m-%d"),
                revenue.category,
                f"${revenue.amount:.2f}",
                revenue.description,
                revenue.reference_id,
                revenue.user.username
            ] for revenue in revenues
        ]
        total_revenue = sum(revenue.amount for revenue in revenues)
        # Add total row
        data.append(['', 'Total Revenue', f"${total_revenue:.2f}", '', '', ''])
        title = "Revenue Report"
    
    elif report_type == 'expenses':
        expenses = FinancialTransaction.query.filter_by(type='expense').all()
        headers = ['Date', 'Category', 'Amount', 'Description', 'Reference', 'Recorded By']
        data = [
            [
                expense.date.strftime("%Y-%m-%d"),
                expense.category,
                f"${expense.amount:.2f}",
                expense.description,
                expense.reference_id,
                expense.user.username
            ] for expense in expenses
        ]
        total_expenses = sum(expense.amount for expense in expenses)
        # Add total row
        data.append(['', 'Total Expenses', f"${total_expenses:.2f}", '', '', ''])
        title = "Expenses Report"
    
    elif report_type == 'profit':
        transactions = FinancialTransaction.query.all()
        headers = ['Date', 'Revenue', 'Expenses', 'Profit', 'Profit Margin']
        
        # Group transactions by date
        daily_totals = {}
        total_revenue = 0
        total_expenses = 0
        
        for trans in transactions:
            date = trans.date.strftime("%Y-%m-%d")
            if date not in daily_totals:
                daily_totals[date] = {'revenue': 0, 'expenses': 0}
            if trans.type == 'revenue':
                daily_totals[date]['revenue'] += trans.amount
                total_revenue += trans.amount
            else:
                daily_totals[date]['expenses'] += trans.amount
                total_expenses += trans.amount
        
        data = [
            [
                date,
                f"${totals['revenue']:.2f}",
                f"${totals['expenses']:.2f}",
                f"${(totals['revenue'] - totals['expenses']):.2f}",
                f"{((totals['revenue'] - totals['expenses']) / totals['revenue'] * 100 if totals['revenue'] > 0 else 0):.1f}%"
            ] for date, totals in sorted(daily_totals.items())
        ]
        
        # Add totals row
        total_profit = total_revenue - total_expenses
        total_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        data.append([
            'Totals',
            f"${total_revenue:.2f}",
            f"${total_expenses:.2f}",
            f"${total_profit:.2f}",
            f"{total_margin:.1f}%"
        ])
        title = "Profit Report"
    
    else:
        return 'Invalid report type', 400

    buffer = generate_pdf(data, title, headers)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{report_type}_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
    )

def generate_pdf(data, title, headers):
    """Generate a PDF report with the given data, title and headers."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    
    # Add company header
    styles = getSampleStyleSheet()
    company_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=20,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph("Spare Parts Management System", company_style))
    
    # Add title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=10,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph(title, title_style))
    
    # Add date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=20,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", date_style))
    
    # Add some space
    elements.append(Spacer(1, 20))
    
    # Create table
    table_data = [headers] + data
    table = Table(table_data)
    
    # Add style to table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        # Style for totals row
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ])
    
    # Add alternating row colors (except for the last row which is totals)
    for i in range(1, len(table_data) - 1):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
    
    table.setStyle(style)
    elements.append(table)
    
    # Add footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1  # Center alignment
    )
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("© 2024 Spare Parts Management System. All rights reserved.", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@finance.route('/finance/void')
@login_required
@finance_access_required
def void_transactions():
    """List transactions that can be voided"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    transaction_type = request.args.get('type')
    
    # Base query
    query = FinancialTransaction.query
    
    # Apply filters
    if start_date:
        query = query.filter(FinancialTransaction.date >= start_date)
    if end_date:
        query = query.filter(FinancialTransaction.date <= end_date)
    if transaction_type:
        query = query.filter(FinancialTransaction.type == transaction_type)
    
    # Get transactions ordered by date
    transactions = query.order_by(FinancialTransaction.date.desc()).all()
    
    return render_template('finance/void_transactions.html',
                         transactions=transactions,
                         start_date=start_date,
                         end_date=end_date)

@finance.route('/finance/void/<int:transaction_id>', methods=['POST'])
@login_required
@finance_access_required
def void_transaction(transaction_id):
    """Void a financial transaction and update all related records"""
    try:
        data = request.json
        if not data or 'reason' not in data:
            return jsonify({'error': 'Reason is required'}), 400
            
        transaction = FinancialTransaction.query.get_or_404(transaction_id)
        
        # Check if already voided
        if transaction.voided:
            return jsonify({'error': 'Transaction is already voided'}), 400
        
        # Start a transaction to ensure all updates are atomic
        db.session.begin_nested()
        
        # Create reversing entry
        reversing_entry = FinancialTransaction(
            date=datetime.utcnow(),
            type=transaction.type,  # Same type as original
            category=transaction.category,
            amount=-transaction.amount,  # Negative amount to reverse
            description=f'VOID: {transaction.description}\nReason: {data["reason"]}',
            reference_id=f'VOID-{transaction.reference_id}',
            user_id=current_user.id
        )
        
        # Mark original transaction as voided
        transaction.voided = True
        transaction.void_reason = data['reason']
        transaction.voided_by_id = current_user.id
        transaction.voided_at = datetime.utcnow()
        
        # Add and commit both transactions
        db.session.add(reversing_entry)
        db.session.flush()  # To get the reversing entry ID
        
        # Link the transactions
        transaction.void_reference_id = reversing_entry.id
        
        # Update related records based on transaction type and reference
        if transaction.reference_id:
            # Handle purchase-related transactions
            if transaction.category == 'purchase':
                purchase = Purchase.query.filter_by(id=transaction.reference_id).first()
                if purchase:
                    # Update purchase status
                    purchase.status = 'cancelled'
                    
                    # Update warehouse stock
                    warehouse_stock = WarehouseStock.query.filter_by(
                        warehouse_id=purchase.warehouse_id,
                        part_id=purchase.part_id
                    ).first()
                    if warehouse_stock:
                        warehouse_stock.quantity -= purchase.quantity
                    
                    # Update part stock level
                    purchase.part.stock_level -= purchase.quantity
                    
                    # Create void bincard entry
                    bincard = BinCard(
                        part_id=purchase.part_id,
                        transaction_type='out',
                        quantity=purchase.quantity,
                        reference_type='purchase_void',
                        reference_id=purchase.id,
                        balance=purchase.part.stock_level,
                        user_id=current_user.id,
                        notes=f'Purchase voided: {data["reason"]}'
                    )
                    db.session.add(bincard)
                    
                    # Update part cost price
                    purchase.part.calculate_cost_price()
            
            # Handle credit purchase-related transactions
            elif transaction.category == 'credit_purchase':
                credit = CreditPurchase.query.filter_by(id=transaction.reference_id).first()
                if credit:
                    # Update credit status
                    credit.status = 'cancelled'
                    
                    # Update warehouse stock
                    warehouse_stock = WarehouseStock.query.filter_by(
                        warehouse_id=credit.warehouse_id,
                        part_id=credit.part_id
                    ).first()
                    if warehouse_stock:
                        warehouse_stock.quantity -= credit.quantity
                    
                    # Update part stock level
                    credit.part.stock_level -= credit.quantity
                    
                    # Create void bincard entry
                    bincard = BinCard(
                        part_id=credit.part_id,
                        transaction_type='out',
                        quantity=credit.quantity,
                        reference_type='credit_purchase_void',
                        reference_id=credit.id,
                        balance=credit.part.stock_level,
                        user_id=current_user.id,
                        notes=f'Credit purchase voided: {data["reason"]}'
                    )
                    db.session.add(bincard)
                    
                    # Update part cost price
                    credit.part.calculate_cost_price()
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Transaction voided successfully and all related records updated'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@finance.route('/exchange-rates', methods=['GET'])
@login_required
@admin_required
def list_exchange_rates():
    rates = ExchangeRate.query.order_by(ExchangeRate.effective_from.desc()).all()
    return render_template('finance/exchange_rates.html', rates=rates)

@finance.route('/exchange-rates/add', methods=['POST'])
@login_required
@admin_required
def add_exchange_rate():
    try:
        rate = float(request.form['rate'])
        effective_from = datetime.strptime(request.form['effective_from'], '%Y-%m-%d')
        
        exchange_rate = ExchangeRate(
            rate=rate,
            effective_from=effective_from,
            user_id=current_user.id
        )
        
        db.session.add(exchange_rate)
        db.session.commit()
        
        flash('Exchange rate updated successfully', 'success')
        return redirect(url_for('finance.list_exchange_rates'))
    except Exception as e:
        flash(f'Error updating exchange rate: {str(e)}', 'error')
        return redirect(url_for('finance.list_exchange_rates'))