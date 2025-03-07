from flask import Blueprint, render_template, request, send_file, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Part, Transaction, Loan, CreditPurchase, Purchase, FinancialTransaction, BinCard, Transfer, Location
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps
import csv
from io import StringIO, BytesIO
import tempfile
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import xlsxwriter

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
    return render_template('reports/low_stock.html', parts=low_stock_parts)

@reports.route('/reports/sales')
@login_required
def sales():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    sales = Transaction.query.filter(
        Transaction.type == 'sale',
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    total_sales = sum(sale.price * sale.quantity for sale in sales)
    total_items = sum(sale.quantity for sale in sales)
    average_sale = total_sales / len(sales) if sales else 0
    
    return render_template('reports/sales.html', 
                         sales=sales,
                         start_date=start_date,
                         end_date=end_date,
                         total_sales=total_sales,
                         total_items=total_items,
                         average_sale=average_sale)

@reports.route('/reports/purchases')
@login_required
def purchases():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    status = request.args.get('status', '')
    
    # Base query
    query = Purchase.query.filter(
        Purchase.purchase_date >= start_date,
        Purchase.purchase_date <= end_date
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
                         start_date=start_date,
                         end_date=end_date,
                         total_cost=total_cost,
                         total_items=total_items,
                         average_cost=average_cost,
                         selected_status=status,
                         statuses=statuses)

@reports.route('/reports/revenue')
@login_required
@finance_access_required
def revenue():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    revenues = FinancialTransaction.query.filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).all()
    
    total_revenue = sum(rev.amount for rev in revenues)
    daily_revenue = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Prepare data for the chart
    dates = [str(date) for date, _ in daily_revenue]
    amounts = [float(amount) for _, amount in daily_revenue]
    
    return render_template('reports/revenue.html',
                         revenues=revenues,
                         start_date=start_date,
                         end_date=end_date,
                         total_revenue=total_revenue,
                         daily_revenue=daily_revenue,
                         dates=dates,
                         amounts=amounts)

@reports.route('/reports/expenses')
@login_required
@finance_access_required
def expenses():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    expenses = FinancialTransaction.query.filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).all()
    
    total_expenses = sum(exp.amount for exp in expenses)
    daily_expenses = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    # Prepare data for the chart
    dates = [str(date) for date, _ in daily_expenses]
    amounts = [float(amount) for _, amount in daily_expenses]
    
    return render_template('reports/expenses.html',
                         expenses=expenses,
                         start_date=start_date,
                         end_date=end_date,
                         total_expenses=total_expenses,
                         daily_expenses=daily_expenses,
                         dates=dates,
                         amounts=amounts)

@reports.route('/reports/profit')
@login_required
@finance_access_required
def profit():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    # Get revenues and expenses
    revenues = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'revenue',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).group_by(func.date(FinancialTransaction.date)).all()
    
    expenses = db.session.query(
        func.date(FinancialTransaction.date),
        func.sum(FinancialTransaction.amount)
    ).filter(
        FinancialTransaction.type == 'expense',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
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
                         start_date=start_date,
                         end_date=end_date,
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
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    credits = CreditPurchase.query.filter(
        CreditPurchase.purchase_date >= start_date,
        CreditPurchase.purchase_date <= end_date
    ).all()
    
    total_pending = sum(credit.price * credit.quantity 
                       for credit in credits if credit.status == 'pending')
                       
    return render_template('reports/credits.html', 
                         credits=credits,
                         start_date=start_date,
                         end_date=end_date,
                         total_pending=total_pending)

@reports.route('/reports/loans')
@login_required
def loans():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    loans = Loan.query.filter(
        Loan.loan_date >= start_date,
        Loan.loan_date <= end_date
    ).all()
    
    return render_template('reports/loans.html',
                         loans=loans,
                         start_date=start_date,
                         end_date=end_date,
                         now=datetime.utcnow())

@reports.route('/reports/transfers')
@login_required
def transfers():
    start_date = request.args.get('start_date', 
                                 (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    from_location = request.args.get('from_location', type=int)
    to_location = request.args.get('to_location', type=int)
    status = request.args.get('status')
    
    # Base query
    query = Transfer.query.filter(
        Transfer.created_at >= start_date,
        Transfer.created_at <= end_date
    )
    
    # Apply filters if provided
    if from_location:
        query = query.filter(Transfer.from_location_id == from_location)
    if to_location:
        query = query.filter(Transfer.to_location_id == to_location)
    if status:
        query = query.filter(Transfer.status == status)
        
    transfers = query.order_by(Transfer.created_at.desc()).all()
    locations = Location.query.all()
    
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
        return export_transfers_pdf(transfers, summary, start_date, end_date)
    elif request.args.get('export') == 'csv':
        return export_transfers_csv(transfers, summary, start_date, end_date)
    
    return render_template('reports/transfers.html',
                         transfers=transfers,
                         locations=locations,
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
    headers = ['Transfer #', 'Date', 'From Location', 'To Location', 
              'Items Count', 'Status', 'Created By']
    
    data = [
        [
            transfer.reference_number,
            transfer.created_at.strftime('%Y-%m-%d'),
            transfer.from_location.name,
            transfer.to_location.name,
            str(len(transfer.items)),
            transfer.status.title(),
            transfer.created_by.username
        ] for transfer in transfers
    ]
    
    # Add summary data
    summary_data = [
        ['Total Transfers:', str(summary['total_transfers']), '', '', '', '', ''],
        ['Completed Transfers:', str(summary['completed_transfers']), '', '', '', '', ''],
        ['Pending Transfers:', str(summary['pending_transfers']), '', '', '', '', ''],
        ['Total Items:', str(summary['total_items']), '', '', '', '', '']
    ]
    
    # Create PDF
    title = f"Transfer Report ({start_date} to {end_date})"
    buffer = generate_pdf(data + [['', '', '', '', '', '', '']] + summary_data, title, headers)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'transfers_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
    )

def generate_pdf(data, title, headers):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          leftMargin=36, rightMargin=36,
                          topMargin=72, bottomMargin=72)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Add header with logo and company name
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#1a237e')  # Dark blue color
    )
    elements.append(Paragraph("SPMS", header_style))
    
    # Add company name
    company_style = ParagraphStyle(
        'Company',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#424242')  # Dark grey color
    )
    elements.append(Paragraph("by EMANA Solutions", company_style))
    elements.append(Spacer(1, 20))
    
    # Add report title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#1976d2')  # Blue color
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # Add date
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        textColor=colors.grey
    )
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style))
    elements.append(Spacer(1, 30))
    
    # Add table with improved styling
    table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Row styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Grid styling
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBEFORE', (0, 0), (-1, -1), 1, colors.black),
        ('LINEAFTER', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.black),
        
        # Alternate row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
    ])
    
    # Create the table
    table_data = [headers] + data
    col_widths = [doc.width/len(headers)] * len(headers)  # Equal column widths
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
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
    buffer = BytesIO()
    buffer.write(b'\xef\xbb\xbf')  # UTF-8 BOM for Excel compatibility
    
    # Write report header
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    buffer.write(f'Transfer Report ({start_date} to {end_date})\n'.encode('utf-8'))
    buffer.write(f'Generated on: {current_date}\n\n'.encode('utf-8'))
    
    # Write headers
    buffer.write('Transfer #,Date,From Location,To Location,Items Count,Status,Created By\n'.encode('utf-8'))
    
    # Write data
    for transfer in transfers:
        row = f'{transfer.reference_number},{transfer.created_at.strftime("%Y-%m-%d")},{transfer.from_location.name},{transfer.to_location.name},{len(transfer.items)},{transfer.status.title()},{transfer.created_by.username}\n'
        buffer.write(row.encode('utf-8'))
    
    # Write summary
    buffer.write('\n'.encode('utf-8'))
    buffer.write('Summary:\n'.encode('utf-8'))
    buffer.write(f'Total Transfers:,{summary["total_transfers"]}\n'.encode('utf-8'))
    buffer.write(f'Completed Transfers:,{summary["completed_transfers"]}\n'.encode('utf-8'))
    buffer.write(f'Pending Transfers:,{summary["pending_transfers"]}\n'.encode('utf-8'))
    buffer.write(f'Total Items:,{summary["total_items"]}\n'.encode('utf-8'))
    
    buffer.seek(0)
    return send_file(
        buffer,
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
    
    if report_type == 'purchases':
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status')
        
        # Base query
        query = Purchase.query
        
        # Apply filters if provided
        if start_date and end_date:
            query = query.filter(
                Purchase.purchase_date >= start_date,
                Purchase.purchase_date <= end_date
            )
        if status:
            query = query.filter(Purchase.status == status)
            
        purchases = query.all()
        
        buffer.write('Date,Part,Supplier,Quantity,Unit Cost,Total Cost,Status\n'.encode('utf-8'))
        total_quantity = 0
        total_cost = 0
        for purchase in purchases:
            row = f'{purchase.purchase_date.strftime("%Y-%m-%d")},{purchase.part.name},{purchase.supplier.name},{purchase.quantity},${purchase.unit_cost:.2f},${purchase.total_cost:.2f},{purchase.status}\n'
            buffer.write(row.encode('utf-8'))
            total_quantity += purchase.quantity
            total_cost += purchase.total_cost
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Totals,,,,{total_quantity},${total_cost:.2f},\n'.encode('utf-8'))
        
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
        
    elif report_type == 'sales':
        sales = Transaction.query.filter_by(type='sale').all()
        buffer.write('Date,Part,Quantity,Price,Total,Sold By\n'.encode('utf-8'))
        total_quantity = 0
        total_amount = 0
        for sale in sales:
            total = sale.price * sale.quantity
            row = f'{sale.date.strftime("%Y-%m-%d")},{sale.part.name},{sale.quantity},${sale.price:.2f},${total:.2f},{sale.user.username}\n'
            buffer.write(row.encode('utf-8'))
            total_quantity += sale.quantity
            total_amount += total
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Totals,,{total_quantity},,${total_amount:.2f},\n'.encode('utf-8'))
        
    elif report_type == 'low_stock':
        parts = Part.query.filter(Part.stock_level < 10).all()
        buffer.write('Part Number,Name,Current Stock,Location\n'.encode('utf-8'))
        total_low_stock = 0
        for part in parts:
            row = f'{part.part_number},{part.name},{part.stock_level},{part.location}\n'
            buffer.write(row.encode('utf-8'))
            total_low_stock += part.stock_level
        
        # Write totals
        buffer.write('\n'.encode('utf-8'))
        buffer.write(f'Total Low Stock Parts:,,{len(parts)},\n'.encode('utf-8'))
        buffer.write(f'Total Units in Low Stock:,,{total_low_stock},\n'.encode('utf-8'))
        
    elif report_type == 'credits':
        credits = CreditPurchase.query.all()
        buffer.write('Date,Customer,Part,Quantity,Amount,Due Date,Status\n'.encode('utf-8'))
        total_quantity = 0
        total_amount = 0
        total_pending = 0
        for credit in credits:
            amount = credit.price * credit.quantity
            row = f'{credit.purchase_date.strftime("%Y-%m-%d")},{credit.customer.name},{credit.part.name},{credit.quantity},${amount:.2f},{credit.due_date.strftime("%Y-%m-%d")},{credit.status}\n'
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
        loans = Loan.query.all()
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

def export_pdf(report_type):
    if report_type == 'bincard':
        part_id = request.args.get('part_id')
        if not part_id:
            return 'Part ID is required', 400
            
        part = Part.query.get_or_404(part_id)
        entries = BinCard.query.filter_by(part_id=part_id).order_by(BinCard.date).all()
        
        headers = ['Date', 'Type', 'Quantity', 'Reference', 'Balance', 'User', 'Notes']
        data = [
            [
                entry.date.strftime("%Y-%m-%d %H:%M"),
                entry.transaction_type.upper(),
                str(entry.quantity),
                f"{entry.reference_type} #{entry.reference_id}",
                str(entry.balance),
                entry.user.username,
                entry.notes or ""
            ] for entry in entries
        ]
        
        # Add totals
        total_in = sum(entry.quantity for entry in entries if entry.quantity > 0)
        total_out = sum(abs(entry.quantity) for entry in entries if entry.quantity < 0)
        data.append(['', '', '', '', '', '', ''])  # Empty row
        data.append(['Total In:', str(total_in), '', '', '', '', ''])
        data.append(['Total Out:', str(total_out), '', '', '', '', ''])
        data.append(['Current Balance:', str(part.stock_level), '', '', '', '', ''])
        
        title = f"Bin Card - {part.name} ({part.part_number})"
    
    elif report_type == 'sales':
        sales = Transaction.query.filter_by(type='sale').all()
        headers = ['Date', 'Part', 'Quantity', 'Price', 'Total', 'Sold By']
        data = [
            [
                sale.date.strftime("%Y-%m-%d"),
                sale.part.name,
                str(sale.quantity),
                f"${sale.price:.2f}",
                f"${(sale.price * sale.quantity):.2f}",
                sale.user.username
            ] for sale in sales
        ]
        
        # Add totals
        total_quantity = sum(sale.quantity for sale in sales)
        total_amount = sum(sale.price * sale.quantity for sale in sales)
        data.append(['', '', '', '', '', ''])  # Empty row
        data.append(['Totals', '', str(total_quantity), '', f"${total_amount:.2f}", ''])
        
        title = "Sales Report"
    
    elif report_type == 'low_stock':
        parts = Part.query.filter(Part.stock_level < 10).all()
        headers = ['Part Number', 'Name', 'Current Stock', 'Location']
        data = [
            [
                part.part_number,
                part.name,
                str(part.stock_level),
                part.location
            ] for part in parts
        ]
        
        # Add totals
        total_low_stock = sum(part.stock_level for part in parts)
        data.append(['', '', '', ''])  # Empty row
        data.append(['Total Low Stock Parts:', str(len(parts)), '', ''])
        data.append(['Total Units in Low Stock:', str(total_low_stock), '', ''])
        
        title = "Low Stock Report"
    
    elif report_type == 'credits':
        credits = CreditPurchase.query.all()
        headers = ['Date', 'Customer', 'Part', 'Quantity', 'Amount', 'Due Date', 'Status']
        data = [
            [
                credit.purchase_date.strftime("%Y-%m-%d"),
                credit.customer.name,
                credit.part.name,
                str(credit.quantity),
                f"${(credit.price * credit.quantity):.2f}",
                credit.due_date.strftime("%Y-%m-%d"),
                credit.status
            ] for credit in credits
        ]
        
        # Add totals
        total_quantity = sum(credit.quantity for credit in credits)
        total_amount = sum(credit.price * credit.quantity for credit in credits)
        total_pending = sum(credit.price * credit.quantity for credit in credits if credit.status == 'pending')
        data.append(['', '', '', '', '', '', ''])  # Empty row
        data.append(['Totals', '', '', str(total_quantity), f"${total_amount:.2f}", '', ''])
        data.append(['Total Pending:', '', '', '', f"${total_pending:.2f}", '', ''])
        
        title = "Credit Purchases Report"
    
    elif report_type == 'loans':
        loans = Loan.query.all()
        headers = ['Date', 'Customer', 'Part', 'Quantity', 'Due Date', 'Status']
        data = [
            [
                loan.loan_date.strftime("%Y-%m-%d"),
                loan.customer.name,
                loan.part.name,
                str(loan.quantity),
                loan.due_date.strftime("%Y-%m-%d"),
                loan.status
            ] for loan in loans
        ]
        
        # Add totals
        total_quantity = sum(loan.quantity for loan in loans)
        total_pending = sum(loan.quantity for loan in loans if loan.status == 'pending')
        data.append(['', '', '', '', '', ''])  # Empty row
        data.append(['Total Items Loaned:', '', '', str(total_quantity), '', ''])
        data.append(['Total Pending Returns:', '', '', str(total_pending), '', ''])
        
        title = "Loans Report"
    
    elif report_type == 'purchases':
        purchases = Purchase.query.all()
        headers = ['Date', 'Part', 'Supplier', 'Quantity', 'Unit Cost', 'Total Cost', 'Status']
        data = [
            [
                purchase.purchase_date.strftime("%Y-%m-%d"),
                purchase.part.name,
                purchase.supplier.name,
                str(purchase.quantity),
                f"${purchase.unit_cost:.2f}",
                f"${purchase.total_cost:.2f}",
                purchase.status
            ] for purchase in purchases
        ]
        
        # Add totals
        total_quantity = sum(purchase.quantity for purchase in purchases)
        total_cost = sum(purchase.total_cost for purchase in purchases)
        data.append(['', '', '', '', '', '', ''])  # Empty row
        data.append(['Totals', '', '', str(total_quantity), '', f"${total_cost:.2f}", ''])
        
        title = "Purchases Report"
    
    else:
        return 'Invalid report type', 400

    buffer = generate_pdf(data, title, headers)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{report_type}_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
    ) 