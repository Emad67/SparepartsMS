from flask import Blueprint, render_template, request, send_file, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Part, Transaction, Loan, CreditPurchase, Purchase, FinancialTransaction, BinCard, Transfer, Location, User, Warehouse, Disposal
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps
import csv
from io import StringIO, BytesIO
import tempfile
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import xlsxwriter
from utils.date_utils import (
    parse_date_range, format_date, format_datetime,
    get_start_of_day, get_end_of_day, get_date_range
)

reports = Blueprint('reports', __name__)

def finance_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager']:
            flash('You need to be an admin or manager to access financial reports.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@reports.route('/reports')
@login_required
def index():
    return render_template('reports/index.html')

@reports.route('/reports/low-stock')
@login_required
def low_stock():
    low_stock_parts = Part.query.filter(Part.stock_level < 10).all()
    
    # Handle export requests directly from this route
    if request.args.get('export') == 'pdf':
        return export_low_stock_pdf(low_stock_parts)
    elif request.args.get('export') == 'csv':
        return export_low_stock_csv(low_stock_parts)
        
    return render_template('reports/low_stock.html', parts=low_stock_parts)

def export_low_stock_pdf(parts):
    """Dedicated function for exporting low stock reports to PDF"""
    headers = ['Part Number', 'Name', 'Current Stock', 'Location']
    
    # Convert parts to data array for PDF generation
    data = [headers]  # Add headers as first row
    data.extend([
        [
            part.part_number,
            part.name,
            str(part.stock_level),
            part.location or 'N/A'
        ] for part in parts
    ])
    
    # Calculate totals
    total_low_stock = sum(part.stock_level for part in parts)
    
    # Add empty row before totals for spacing
    data.append(['', '', '', ''])
    
    # Add total row - will be detected and styled by generate_pdf
    data.append(['Total Low Stock Parts:', str(len(parts)), '', ''])
    data.append(['Total Units in Low Stock:', str(total_low_stock), '', ''])
    
    title = "Low Stock Report"
    
    # Generate PDF using the existing function
    buffer = generate_pdf(data, title, headers)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'low_stock_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
    )
    
def export_low_stock_csv(parts):
    """Dedicated function for exporting low stock reports to CSV"""
    buffer = BytesIO()
    buffer.write(b'\xef\xbb\xbf')  # UTF-8 BOM for Excel compatibility
    
    # Write report header
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    buffer.write(f'Report Type: Low Stock Report\n'.encode('utf-8'))
    buffer.write(f'Generated on: {current_date}\n'.encode('utf-8'))
    buffer.write('\n'.encode('utf-8'))
    
    # Write CSV header
    buffer.write('Part Number,Name,Current Stock,Location\n'.encode('utf-8'))
    
    # Write part data
    total_low_stock = 0
    for part in parts:
        row = f'{part.part_number},{part.name},{part.stock_level},{part.location or "N/A"}\n'
        buffer.write(row.encode('utf-8'))
        total_low_stock += part.stock_level
    
    # Write totals
    buffer.write('\n'.encode('utf-8'))
    buffer.write(f'Total Low Stock Parts:,,{len(parts)},\n'.encode('utf-8'))
    buffer.write(f'Total Units in Low Stock:,,{total_low_stock},\n'.encode('utf-8'))
    
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'low_stock_report_{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

@reports.route('/reports/sales')
@login_required
def sales():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    user_id = request.args.get('user_id')
    part_search = request.args.get('part_search', '')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Base query
    query = Transaction.query.filter(Transaction.type == 'sale')
    
    # Apply date filters using func.date() to compare only the date part
    if start_datetime:
        query = query.filter(func.date(Transaction.date) >= start_datetime.date())
    if end_datetime:
        query = query.filter(func.date(Transaction.date) <= end_datetime.date())
    
    # Apply user filter if provided
    if user_id:
        query = query.filter(Transaction.user_id == user_id)
    
    # Apply part search if provided
    if part_search:
        search_term = f"%{part_search}%"
        query = query.join(Part).filter(
            db.or_(
                Part.name.ilike(search_term),
                Part.part_number.ilike(search_term)
            )
        )
    
    # Order by date descending (newest first)
    query = query.order_by(Transaction.date.desc())
    
    sales = query.all()
    
    # Get all users who have made sales
    users = User.query.join(Transaction).filter(Transaction.type == 'sale').distinct().all()
    
    # Calculate totals
    total_sales = sum(sale.price * sale.quantity for sale in sales)
    total_items = sum(sale.quantity for sale in sales)
    average_sale = total_sales / len(sales) if sales else 0
    
    return render_template('reports/sales.html', 
                         sales=sales,
                         users=users,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_sales=total_sales,
                         total_items=total_items,
                         average_sale=average_sale,
                         user_id=user_id,
                         part_search=part_search)

@reports.route('/reports/purchases')
@login_required
def purchases():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    status = request.args.get('status', '')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Base query
    query = Purchase.query.filter(
        Purchase.purchase_date >= start_datetime,
        Purchase.purchase_date <= end_datetime
    )
    
    # Apply status filter if provided
    if status:
        query = query.filter(Purchase.status == status)
    
    purchases = query.all()
    
    total_cost = sum(purchase.total_cost for purchase in purchases)
    total_items = sum(purchase.quantity for purchase in purchases)
    average_cost = total_cost / len(purchases) if purchases else 0
    
    # Get all possible statuses for the filter dropdown
    statuses = ['pending', 'received', 'cancelled']
    
    return render_template('reports/purchases.html', 
                         purchases=purchases,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_cost=total_cost,
                         total_items=total_items,
                         average_cost=average_cost,
                         selected_status=status,
                         statuses=statuses)

@reports.route('/reports/revenue')
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
        FinancialTransaction.date <= end_datetime
    ).all()
    
    total_revenue = sum(rev.amount for rev in revenues)
    daily_revenue = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Prepare data for the chart
    dates = [str(date) for date, _ in daily_revenue]
    amounts = [float(amount) for _, amount in daily_revenue]
    
    return render_template('reports/revenue.html',
                         revenues=revenues,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_revenue=total_revenue,
                         daily_revenue=daily_revenue,
                         dates=dates,
                         amounts=amounts)

@reports.route('/reports/expenses')
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
        FinancialTransaction.date <= end_datetime
    ).all()
    
    total_expenses = sum(exp.amount for exp in expenses)
    daily_expenses = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Prepare data for the chart
    dates = [str(date) for date, _ in daily_expenses]
    amounts = [float(amount) for _, amount in daily_expenses]
    
    return render_template('reports/expenses.html',
                         expenses=expenses,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_expenses=total_expenses,
                         daily_expenses=daily_expenses,
                         dates=dates,
                         amounts=amounts)

@reports.route('/reports/profit')
@login_required
@finance_access_required
def profit():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Get revenues and expenses
    revenues = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    expenses = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_datetime,
        FinancialTransaction.date <= end_datetime
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Convert to dictionaries for easier access
    revenue_dict = {str(date): amount for date, amount in revenues}
    expense_dict = {str(date): amount for date, amount in expenses}
    
    # Get all dates in range
    all_dates = sorted(set(revenue_dict.keys()) | set(expense_dict.keys()))
    
    # Calculate daily profits
    daily_profits = []
    total_revenue = 0
    total_expenses = 0
    dates = []
    revenues = []
    expenses = []
    profits = []
    for date in all_dates:
        revenue = revenue_dict.get(date, 0)
        expense = expense_dict.get(date, 0)
        profit = revenue - expense
        daily_profits.append((date, revenue, expense, profit))
        total_revenue += revenue
        total_expenses += expense
        dates.append(date)
        revenues.append(float(revenue))
        expenses.append(float(expense))
        profits.append(float(profit))
    
    total_profit = total_revenue - total_expenses
    
    return render_template('reports/profit.html',
                         daily_profits=daily_profits,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         total_profit=total_profit,
                         dates=dates,
                         revenues=revenues,
                         expenses=expenses,
                         profits=profits)

@reports.route('/reports/credits')
@login_required
def credits():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    status = request.args.get('status', '')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Base query
    query = CreditPurchase.query.filter(
        CreditPurchase.purchase_date >= start_datetime,
        CreditPurchase.purchase_date <= end_datetime
    )
    
    # Apply status filter if provided
    if status:
        query = query.filter(CreditPurchase.status == status)
    
    credits = query.all()
    
    total_pending = sum(credit.price * credit.quantity 
                       for credit in credits if credit.status == 'pending')
                       
    return render_template('reports/credits.html', 
                         credits=credits,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         total_pending=total_pending,
                         selected_status=status)

@reports.route('/reports/loans')
@login_required
def loans():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    status = request.args.get('status', '')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Base query
    query = Loan.query.filter(
        Loan.loan_date >= start_datetime,
        Loan.loan_date <= end_datetime
    )
    
    # Apply status filter if provided
    if status:
        query = query.filter(Loan.status == status)
    
    loans = query.order_by(Loan.loan_date.desc()).all()
    
    # Calculate summary statistics
    total_quantity = sum(loan.quantity for loan in loans)
    total_value = sum(loan.quantity * loan.part.cost_price for loan in loans if loan.part and loan.part.cost_price)
    
    # Get all possible statuses for the filter dropdown
    statuses = ['active', 'returned', 'overdue', 'sold']
    
    return render_template('reports/loans.html',
                         loans=loans,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime),
                         selected_status=status,
                         statuses=statuses,
                         total_quantity=total_quantity,
                         total_value=total_value,
                         now=datetime.utcnow())

@reports.route('/reports/transfers')
@login_required
def transfers():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    from_location = request.args.get('from_location', type=int)
    to_location = request.args.get('to_location', type=int)
    status = request.args.get('status')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Base query
    query = Transfer.query.filter(
        Transfer.created_at >= start_datetime,
        Transfer.created_at <= end_datetime
    )
    
    # Apply filters if provided
    if from_location:
        query = query.filter(Transfer.from_location_id == from_location)
    if to_location:
        query = query.filter(Transfer.to_location_id == to_location)
    if status:
        query = query.filter(Transfer.status == status)
        
    transfers = query.order_by(Transfer.created_at.desc()).all()
    warehouses = Warehouse.query.all()
    
    # Calculate summary statistics
    summary = {
        'total_transfers': len(transfers),
        'completed_transfers': sum(1 for t in transfers if t.status == 'completed'),
        'pending_transfers': sum(1 for t in transfers if t.status == 'pending'),
        'total_items': sum(len(t.items) for t in transfers)
    }
    
    # Handle export requests
    if request.args.get('export') == 'excel':
        return export_transfers_excel(transfers)
    elif request.args.get('export') == 'pdf':
        return export_transfers_pdf(transfers, summary, format_date(start_datetime), format_date(end_datetime))
    elif request.args.get('export') == 'csv':
        return export_transfers_csv(transfers, summary, format_date(start_datetime), format_date(end_datetime))
    
    return render_template('reports/transfers.html',
                         transfers=transfers,
                         warehouses=warehouses,
                         summary=summary)

def export_transfers_excel(transfers):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Add headers
    headers = ['Transfer #', 'Date', 'From Location', 'To Location', 
              'Items Count', 'Status', 'Created By']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)
    
    # Add data
    for row, transfer in enumerate(transfers, start=1):
        worksheet.write(row, 0, transfer.reference_number)
        worksheet.write(row, 1, transfer.created_at.strftime('%Y-%m-%d'))
        worksheet.write(row, 2, transfer.from_location.name)
        worksheet.write(row, 3, transfer.to_location.name)
        worksheet.write(row, 4, len(transfer.items))
        worksheet.write(row, 5, transfer.status)
        worksheet.write(row, 6, transfer.created_by.username)
    
    workbook.close()
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'transfers_report_{datetime.now().strftime("%Y-%m-%d")}.xlsx'
    )

def export_transfers_pdf(transfers, summary, start_date, end_date):
    # Prepare data for PDF
    headers = ['Transfer #', 'Date', 'From', 'To', 'Items', 'Status', 'Created By']
    
    data = [headers]  # Add headers as first row
    data.extend([
        [
            transfer.reference_number,
            transfer.created_at.strftime('%Y-%m-%d'),
            transfer.from_location.name[:20],  # Truncate long names
            transfer.to_location.name[:20],    # Truncate long names
            str(len(transfer.items)),
            transfer.status.title(),
            transfer.created_by.username
        ] for transfer in transfers
    ])
    
    # Add summary data with improved formatting
    data.append(['', '', '', '', '', '', ''])  # Empty row
    data.append(['Summary', '', '', '', '', '', ''])
    data.append(['Total Transfers:', str(summary['total_transfers']), '', '', '', '', ''])
    data.append(['Completed:', str(summary['completed_transfers']), '', '', '', '', ''])
    data.append(['Pending:', str(summary['pending_transfers']), '', '', '', '', ''])
    data.append(['Total Items:', str(summary['total_items']), '', '', '', '', ''])
    
    # Create PDF with improved layout
    title = f"Transfer Report ({start_date} to {end_date})"
    buffer = generate_pdf(data, title, headers)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'transfers_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
    )

def generate_pdf(data, title, headers):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                          leftMargin=36, rightMargin=36,
                          topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Add header with logo and company name
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=15,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#1a237e')  # Dark blue color
    )
    elements.append(Paragraph("SPMS", header_style))
    
    # Add company name
    company_style = ParagraphStyle(
        'Company',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=10,
        alignment=1,
        textColor=colors.HexColor('#424242')  # Dark grey color
    )
    elements.append(Paragraph("by EMANA Solutions", company_style))
    elements.append(Spacer(1, 5))
    
    # Add report title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=1,
        alignment=0,
        textColor=colors.HexColor('#1976d2')  # Blue color
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 5))
    
    # Add date
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=10,
        alignment=2,
        textColor=colors.grey
    )
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style))
    elements.append(Spacer(1, 30))
    
    # Calculate column widths based on content
    total_width = doc.width - (doc.leftMargin + doc.rightMargin)
    
    # Create table with flexible column widths
    table = Table(data, colWidths=[total_width/len(headers)] * len(headers), repeatRows=1)
    
    # Determine which rows are totals rows based on data content
    # Usually they're near the end of the table after an empty row
    totals_row_indices = []
    for i in range(1, len(data)):
        if i < len(data) - 1 and all(cell == '' for cell in data[i]) and data[i+1][0].startswith('Total'):
            totals_row_indices.append(i+1)
        elif i > 1 and data[i][0].startswith('Total'):
            totals_row_indices.append(i)
    
    # Add table style with improved formatting
    table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Row styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        
        # Grid styling
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBEFORE', (0, 0), (-1, -1), 1, colors.black),
        ('LINEAFTER', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.black),
    ])
    
    # Add alternating row background colors for main data (excluding header and totals)
    main_data_end = len(data) - len(totals_row_indices) - 1 if totals_row_indices else len(data)
    table_style.add('ROWBACKGROUNDS', (0, 1), (-1, main_data_end), [colors.white, colors.HexColor('#f5f5f5')])
    
    # Special styling for totals rows
    for row_idx in totals_row_indices:
        # Style for the actual totals row - bold, slightly larger font, light background
        table_style.add('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#f2f7fd'))  # Very light blue
        table_style.add('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold')
        table_style.add('FONTSIZE', (0, row_idx), (-1, row_idx), 10)  # Slightly larger
        table_style.add('BOTTOMPADDING', (0, row_idx), (-1, row_idx), 8)
        table_style.add('TOPPADDING', (0, row_idx), (-1, row_idx), 8)
    
    # Apply the style to the table
    table.setStyle(table_style)
    elements.append(table)
    
    # Add footer
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.grey
    )
    elements.append(Paragraph("SPMS by EMANA Solutions - All rights reserved", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def export_transfers_csv(transfers, summary, start_date, end_date):
    buffer = StringIO()
    writer = csv.writer(buffer)
    
    # Write report header
    writer.writerow(['Transfer Report'])
    writer.writerow([f'Period: {start_date} to {end_date}'])
    writer.writerow([f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])  # Empty row
    
    # Write headers
    writer.writerow(['Transfer #', 'Date', 'From Location', 'To Location', 'Items Count', 'Status', 'Created By'])
    
    # Write data
    for transfer in transfers:
        writer.writerow([
            transfer.reference_number,
            transfer.created_at.strftime('%Y-%m-%d'),
            transfer.from_location.name,
            transfer.to_location.name,
            len(transfer.items),
            transfer.status.title(),
            transfer.created_by.username
        ])
    
    # Write summary
    writer.writerow([])  # Empty row
    writer.writerow(['Summary'])
    writer.writerow(['Total Transfers:', summary['total_transfers']])
    writer.writerow(['Completed Transfers:', summary['completed_transfers']])
    writer.writerow(['Pending Transfers:', summary['pending_transfers']])
    writer.writerow(['Total Items:', summary['total_items']])
    
    # Prepare the response
    buffer.seek(0)
    output = BytesIO()
    output.write(buffer.getvalue().encode('utf-8-sig'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'transfers_report_{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

@reports.route('/reports/export/<report_type>/<format>')
@login_required
def export(report_type, format):
    # Add access control for financial reports
    if report_type in ['revenue', 'expenses', 'profit']:
        if current_user.role not in ['admin', 'manager']:
            flash('You need to be an admin or manager to export financial reports.', 'error')
            return redirect(url_for('dashboard.index'))
            
    if format not in ['csv', 'pdf']:
        return 'Invalid format', 400

    # Get date filters and parse them properly
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Use the same date parsing as the main routes
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)

    if format == 'csv':
        return export_csv(report_type, start_datetime, end_datetime)
    else:
        return export_pdf(report_type, start_datetime, end_datetime)

def export_csv(report_type, start_datetime, end_datetime):
    buffer = BytesIO()
    buffer.write(b'\xef\xbb\xbf')
    
    # Write report header
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    buffer.write(f'Report Type: {report_type.title()} Report\n'.encode('utf-8'))
    buffer.write(f'Generated on: {current_date}\n'.encode('utf-8'))
    if start_datetime and end_datetime:
        buffer.write(f'Period: {format_date(start_datetime)} to {format_date(end_datetime)}\n'.encode('utf-8'))
    buffer.write('\n'.encode('utf-8'))
    
    if report_type == 'sales':
        # Create base query with type filter
        query = Transaction.query.filter_by(type='sale')
        
        # Apply date filters using func.date() to compare only the date part
        if start_datetime:
            query = query.filter(func.date(Transaction.date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(Transaction.date) <= end_datetime.date())
            
        # Get filtered sales
        sales = query.order_by(Transaction.date).all()
        
        buffer.write('Date,Part,Quantity,Price,Total,Sold By\n'.encode('utf-8'))
        total_quantity = 0
        total_amount = 0
        for sale in sales:
            total = sale.price * sale.quantity
            row = f'{sale.date.strftime("%Y-%m-%d")},{sale.part.name},{sale.quantity},{sale.price:.2f},{total:.2f},{sale.user.username}\n'
            buffer.write(row.encode('utf-8'))
            total_quantity += sale.quantity
            total_amount += total
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Totals,,{total_quantity},,{total_amount:.2f},\n'.encode('utf-8'))
        
    elif report_type == 'bincard':
        part_id = request.args.get('part_id')
        if not part_id:
            return 'Part ID is required', 400
            
        part = Part.query.get_or_404(part_id)
        entries = BinCard.query.filter_by(part_id=part_id).order_by(BinCard.date).all()
        
        buffer.write('Part Name,Part Number,Date,Type,Quantity,Reference,Balance,User,Notes\n'.encode('utf-8'))
        total_in = 0
        total_out = 0
        for entry in entries:
            row = f'{part.name},{part.part_number},{entry.date.strftime("%Y-%m-%d %H:%M")},{entry.transaction_type},{entry.quantity},{entry.reference_type} #{entry.reference_id},{entry.balance},{entry.user.username},{entry.notes or ""}\n'
            buffer.write(row.encode('utf-8'))
            if entry.quantity > 0:
                total_in += entry.quantity
            else:
                total_out += abs(entry.quantity)
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Total In:,,,,{total_in},,,,\n'.encode('utf-8'))
        buffer.write(f'Total Out:,,,,{total_out},,,,\n'.encode('utf-8'))
        buffer.write(f'Current Balance:,,,,{part.stock_level},,,,\n'.encode('utf-8'))
        
    elif report_type == 'credits':
        # Apply proper date filters to credit purchases
        query = CreditPurchase.query
        
        # Apply date filters using func.date to handle date comparison properly
        if start_datetime:
            query = query.filter(func.date(CreditPurchase.purchase_date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(CreditPurchase.purchase_date) <= end_datetime.date())
            
        # Apply status filter if provided
        status = request.args.get('status', '')
        if status:
            query = query.filter(CreditPurchase.status == status)
            
        credits = query.order_by(CreditPurchase.purchase_date).all()
        
        buffer.write('Date,Supplier,Part,Quantity,Amount,Due Date,Status\n'.encode('utf-8'))
        total_quantity = 0
        total_amount = 0
        total_pending = 0
        for credit in credits:
            amount = credit.price * credit.quantity
            row = f'{credit.purchase_date.strftime("%Y-%m-%d")},{credit.supplier.name},{credit.part.name},{credit.quantity},${amount:.2f},{credit.due_date.strftime("%Y-%m-%d")},{credit.status}\n'
            buffer.write(row.encode('utf-8'))
            total_quantity += credit.quantity
            total_amount += amount
            if credit.status == 'pending':
                total_pending += amount
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Totals,,,,${total_amount:.2f},,\n'.encode('utf-8'))
        buffer.write(f'Total Quantity:,,,{total_quantity},,,\n'.encode('utf-8'))
        buffer.write(f'Total Pending Amount:,,,,${total_pending:.2f},,\n'.encode('utf-8'))
        
    elif report_type == 'loans':
        # Apply proper date filters to loans
        query = Loan.query
        
        # Apply date filters using func.date to handle date comparison properly
        if start_datetime:
            query = query.filter(func.date(Loan.loan_date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(Loan.loan_date) <= end_datetime.date())
            
        loans = query.order_by(Loan.loan_date).all()
        
        buffer.write('Date,Customer,Part,Quantity,Due Date,Status\n'.encode('utf-8'))
        total_quantity = 0
        total_pending = 0
        for loan in loans:
            row = f'{loan.loan_date.strftime("%Y-%m-%d")},{loan.customer.name},{loan.part.name},{loan.quantity},{loan.due_date.strftime("%Y-%m-%d")},{loan.status}\n'
            buffer.write(row.encode('utf-8'))
            total_quantity += loan.quantity
            if loan.status == 'pending':
                total_pending += loan.quantity
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Total Items Loaned:,,,{total_quantity},,\n'.encode('utf-8'))
        buffer.write(f'Total Pending Returns:,,,{total_pending},,\n'.encode('utf-8'))

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{report_type}_report_{datetime.now().strftime("%Y-%m-%d")}.csv'
    )

def export_pdf(report_type, start_datetime, end_datetime):
    if report_type == 'sales':
        # Create base query with type filter
        query = Transaction.query.filter_by(type='sale')
        
        # Apply date filters using func.date() to compare only the date part
        if start_datetime:
            query = query.filter(func.date(Transaction.date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(Transaction.date) <= end_datetime.date())
            
        # Get filtered sales
        sales = query.order_by(Transaction.date).all()
        
        headers = ['Date', 'Part', 'Quantity', 'Price', 'Total', 'Sold By']
        data = [headers]  # Add headers as first row
        data.extend([
            [
                sale.date.strftime("%Y-%m-%d"),
                sale.part.name,
                str(sale.quantity),
                f"{sale.price:.2f} NKF",
                f"{(sale.price * sale.quantity):.2f} NKF",
                sale.user.username
            ] for sale in sales
        ])
        
        # Add totals
        total_quantity = sum(sale.quantity for sale in sales)
        total_amount = sum(sale.price * sale.quantity for sale in sales)
        data.append(['', '', '', '', '', ''])  # Empty row
        data.append(['Totals', '', str(total_quantity), '', f"{total_amount:.2f} NKF", ''])
        
        title = "Sales Report"
        
        # Add date range to title if dates are provided
        if start_datetime and end_datetime:
            title += f" ({format_date(start_datetime)} to {format_date(end_datetime)})"
            
        buffer = generate_pdf(data, title, headers)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'sales_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )

    elif report_type == 'bincard':
        part_id = request.args.get('part_id')
        if not part_id:
            return 'Part ID is required', 400
            
        part = Part.query.get_or_404(part_id)
        query = BinCard.query.filter_by(part_id=part_id)
        
        # Apply date filters
        if start_datetime:
            query = query.filter(BinCard.date >= start_datetime)
        if end_datetime:
            query = query.filter(BinCard.date <= end_datetime)
            
        entries = query.order_by(BinCard.date).all()
        
        headers = ['Date', 'Type', 'Quantity', 'Reference', 'Balance', 'User', 'Notes']
        data = [headers]  # Add headers as first row
        data.extend([
            [
                entry.date.strftime("%Y-%m-%d %H:%M"),
                entry.transaction_type.upper(),
                str(entry.quantity),
                f"{entry.reference_type} #{entry.reference_id}",
                str(entry.balance),
                entry.user.username,
                entry.notes or ""
            ] for entry in entries
        ])
        
        # Add totals
        total_in = sum(entry.quantity for entry in entries if entry.quantity > 0)
        total_out = sum(abs(entry.quantity) for entry in entries if entry.quantity < 0)
        data.append(['', '', '', '', '', '', ''])  # Empty row
        data.append(['Total In:', str(total_in), '', '', '', '', ''])
        data.append(['Total Out:', str(total_out), '', '', '', '', ''])
        data.append(['Current Balance:', str(part.stock_level), '', '', '', '', ''])
        
        title = f"Bin Card - {part.name} ({part.part_number})"
        
        # Add date range to title if dates are provided
        if start_datetime and end_datetime:
            title += f" ({format_date(start_datetime)} to {format_date(end_datetime)})"
            
        buffer = generate_pdf(data, title, headers)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'bincard_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )
    
    elif report_type == 'credits':
        # Create base query
        query = CreditPurchase.query
        
        # Apply date filters using func.date to handle date comparison properly
        if start_datetime:
            query = query.filter(func.date(CreditPurchase.purchase_date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(CreditPurchase.purchase_date) <= end_datetime.date())
            
        # Apply status filter if provided
        status = request.args.get('status', '')
        if status:
            query = query.filter(CreditPurchase.status == status)
            
        credits = query.order_by(CreditPurchase.purchase_date).all()
        
        headers = ['Date', 'Supplier', 'Part', 'Quantity', 'Amount', 'Due Date', 'Status']
        data = [headers]  # Add headers as first row
        data.extend([
            [
                credit.purchase_date.strftime("%Y-%m-%d"),
                credit.supplier.name,
                credit.part.name,
                str(credit.quantity),
                f"{credit.price * credit.quantity:.2f} NKF",
                credit.due_date.strftime("%Y-%m-%d"),
                credit.status.title()
            ] for credit in credits
        ])
        
        # Add totals
        total_quantity = sum(credit.quantity for credit in credits)
        total_amount = sum(credit.price * credit.quantity for credit in credits)
        total_pending = sum(credit.price * credit.quantity for credit in credits if credit.status == 'pending')
        data.append(['', '', '', '', '', '', ''])  # Empty row
        data.append(['Summary', '', '', '', '', '', ''])  # Summary header
        data.append(['Total Credits:', '', '', str(total_quantity), f"{total_amount:.2f} NKF", '', ''])
        data.append(['Total Pending:', '', '', '', f"{total_pending:.2f} NKF", '', ''])
        data.append(['Total Completed:', '', '', '', f"{(total_amount - total_pending):.2f} NKF", '', ''])
        
        title = "Credit Purchases Report"
        
        # Add date range to title if dates are provided
        if start_datetime and end_datetime:
            title += f" ({format_date(start_datetime)} to {format_date(end_datetime)})"
            
        buffer = generate_pdf(data, title, headers)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'credits_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )

    elif report_type == 'loans':
        # Create base query
        query = Loan.query
        
        # Apply date filters using func.date to handle date comparison properly
        if start_datetime:
            query = query.filter(func.date(Loan.loan_date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(Loan.loan_date) <= end_datetime.date())
            
        loans = query.order_by(Loan.loan_date).all()
        
        headers = ['Date', 'Customer', 'Part', 'Quantity', 'Due Date', 'Status']
        data = [headers]  # Add headers as first row
        data.extend([
            [
                loan.loan_date.strftime("%Y-%m-%d"),
                loan.customer.name,
                loan.part.name,
                str(loan.quantity),
                loan.due_date.strftime("%Y-%m-%d"),
                loan.status
            ] for loan in loans
        ])
        
        # Add totals
        total_quantity = sum(loan.quantity for loan in loans)
        total_pending = sum(loan.quantity for loan in loans if loan.status == 'pending')
        data.append(['', '', '', '', '', ''])  # Empty row
        data.append(['Total Items Loaned:', '', '', str(total_quantity), '', ''])
        data.append(['Total Pending Loans:', '', '', str(total_pending), '', ''])
        
        title = "Loans Report"
        
        # Add date range to title if dates are provided
        if start_datetime and end_datetime:
            title += f" ({format_date(start_datetime)} to {format_date(end_datetime)})"
            
        buffer = generate_pdf(data, title, headers)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'loans_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )
    
    elif report_type == 'purchases':
        # Create base query
        query = Purchase.query
        
        # Apply date filters
        if start_datetime:
            query = query.filter(func.date(Purchase.purchase_date) >= start_datetime.date())
        if end_datetime:
            query = query.filter(func.date(Purchase.purchase_date) <= end_datetime.date())
            
        purchases = query.order_by(Purchase.purchase_date).all()
        
        headers = ['Date', 'Part', 'Quantity', 'Unit Cost', 'Total Cost', 'Supplier', 'Status']
        data = [headers]  # Add headers as first row
        data.extend([
            [
                purchase.purchase_date.strftime("%Y-%m-%d"),
                purchase.part.name,
                str(purchase.quantity),
                f"{purchase.unit_cost:.2f} NKF",
                f"{purchase.total_cost:.2f} NKF",
                purchase.supplier.name if purchase.supplier else "N/A",
                purchase.status.title()
            ] for purchase in purchases
        ])
        
        # Add totals
        total_quantity = sum(purchase.quantity for purchase in purchases)
        total_cost = sum(purchase.total_cost for purchase in purchases)
        data.append(['', '', '', '', '', '', ''])  # Empty row
        data.append(['Totals', '', str(total_quantity), '', f"{total_cost:.2f} NKF", '', ''])
        
        title = "Purchases Report"
        
        # Add date range to title if dates are provided
        if start_datetime and end_datetime:
            title += f" ({format_date(start_datetime)} to {format_date(end_datetime)})"
            
        buffer = generate_pdf(data, title, headers)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'purchases_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )
    
    else:
        return 'Invalid report type', 400

@reports.route('/reports/disposals')
@login_required
def disposals():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Get date range with fallback to last 30 days
    start_datetime, end_datetime = parse_date_range(start_date_str, end_date_str)
    
    # Base query
    query = Disposal.query.filter(
        Disposal.disposal_date >= start_datetime,
        Disposal.disposal_date <= end_datetime
    )
    
    disposals = query.order_by(Disposal.disposal_date.desc()).all()
    
    # Calculate summary statistics
    summary = {
        'total_disposals': len(disposals),
        'total_items': sum(disposal.quantity for disposal in disposals),
        'total_cost': sum(disposal.part.cost_price * disposal.quantity for disposal in disposals)
    }
    
    # Handle export requests
    if request.args.get('export') == 'pdf':
        return export_disposals_pdf(disposals, summary, format_date(start_datetime), format_date(end_datetime))
    elif request.args.get('export') == 'csv':
        return export_disposals_csv(disposals, summary, format_date(start_datetime), format_date(end_datetime))
    
    return render_template('reports/disposals.html',
                         disposals=disposals,
                         summary=summary,
                         start_date=format_date(start_datetime),
                         end_date=format_date(end_datetime))

def export_disposals_pdf(disposals, summary, start_date, end_date):
    # Prepare data for PDF
    headers = ['Date', 'Part Number', 'Part Name', 'Quantity', 'Reason', 'Cost Impact', 'Disposed By']
    
    data = [headers]  # Add headers as first row
    data.extend([
        [
            disposal.disposal_date.strftime('%Y-%m-%d'),
            disposal.part.part_number,
            disposal.part.name,
            str(disposal.quantity),
            disposal.reason,
            f"{(disposal.part.cost_price * disposal.quantity):.2f} NKF",
            disposal.user.username
        ] for disposal in disposals
    ])
    
    # Add summary data with improved formatting
    data.append(['', '', '', '', '', '', ''])  # Empty row
    data.append(['Summary', '', '', '', '', '', ''])
    data.append(['Total Disposals:', str(summary['total_disposals']), '', '', '', '', ''])
    data.append(['Total Items:', str(summary['total_items']), '', '', '', '', ''])
    data.append(['Total Cost Impact:', '', '', '', '', f"{summary['total_cost']:.2f} NKF", ''])
    
    # Create PDF with improved layout
    title = f"Parts Disposal Report ({start_date} to {end_date})"
    buffer = generate_pdf(data, title, headers)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'disposals_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
    )

def export_disposals_csv(disposals, summary, start_date, end_date):
    # Create StringIO buffer for CSV writing
    output = StringIO()
    writer = csv.writer(output)
    
    # Write report header
    writer.writerow(['Parts Disposal Report'])
    writer.writerow([f'Period: {start_date} to {end_date}'])
    writer.writerow([f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])  # Empty row
    
    # Write headers
    headers = ['Date', 'Part Number', 'Part Name', 'Quantity', 'Reason', 'Cost Impact', 'Disposed By']
    writer.writerow(headers)
    
    # Write disposal data
    for disposal in disposals:
        writer.writerow([
            disposal.disposal_date.strftime('%Y-%m-%d'),
            disposal.part.part_number,
            disposal.part.name,
            disposal.quantity,
            disposal.reason,
            f"{(disposal.part.cost_price * disposal.quantity):.2f} NKF",
            disposal.user.username
        ])
    
    # Write summary
    writer.writerow([])  # Empty row
    writer.writerow(['Summary'])
    writer.writerow(['Total Disposals:', summary['total_disposals']])
    writer.writerow(['Total Items:', summary['total_items']])
    writer.writerow(['Total Cost Impact:', f"{summary['total_cost']:.2f} NKF"])
    
    # Convert to bytes for file download
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8-sig')),  # UTF-8 with BOM for Excel
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'disposals_report_{datetime.now().strftime("%Y-%m-%d")}.csv'
    ) 