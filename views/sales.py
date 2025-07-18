from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Part, Transaction, Customer, User, BinCard, FinancialTransaction, ExchangeRate, LoanPayment
from datetime import datetime
from utils.template_filters import format_price_nkf
from io import BytesIO
from sqlalchemy import func
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pytz
from utils.date_utils import (
    parse_date_range, format_date, format_datetime,
    get_start_of_day, get_end_of_day, get_date_range
)
from sqlalchemy.orm import joinedload

sales = Blueprint('sales', __name__)

@sales.route('/sales')
@login_required
def list_sales():
    # Exclude sales linked to voided loan payments using an outer join
    sales = db.session.query(Transaction).outerjoin(LoanPayment, Transaction.loan_payment_id == LoanPayment.id)
    sales = sales.filter(
        Transaction.type == 'sale',
        ((Transaction.status == None) | (Transaction.status != 'cancelled')),
        Transaction.voided == False,
        ((Transaction.loan_payment_id == None) | (LoanPayment.voided == False))
    ).order_by(Transaction.date.desc()).all()
    # Get unique users who have made sales
    users = User.query.join(Transaction).filter(Transaction.type == 'sale').distinct().all()
    return render_template('sales/list.html', sales=sales, users=users)

@sales.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        part_id = request.form.get('part_id')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))
        customer_id = request.form.get('customer_id')
        
        part = Part.query.get_or_404(part_id)
        
        if part.stock_level < quantity:
            flash('Not enough stock available', 'error')
            return redirect(url_for('sales.new_sale'))
            
        sale = Transaction(
            part_id=part_id,
            type='sale',
            quantity=quantity,
            price=price,
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            user_id=current_user.id
        )
        
        # Update stock level
        part.stock_level -= quantity
        
        # First commit the sale to get its ID
        db.session.add(sale)
        db.session.flush()
        
        # Create financial transaction for the sale
        total_amount = price * quantity
        financial_transaction = FinancialTransaction(
            type='revenue',
            category='Sales',
            amount=total_amount,
            description=f'Sale of {quantity} units of part ID {part_id} at {format_price_nkf(price)} per unit',
            reference_id=str(sale.id),
            user_id=current_user.id,
            date=datetime.now(pytz.timezone('Africa/Nairobi')),
            exchange_rate=ExchangeRate.get_rate_for_date()
        )
        
        # Now create bincard entry with the sale's ID
        bincard = BinCard(
            part_id=part_id,
            transaction_type='out',
            quantity=quantity,
            reference_type='sale',
            reference_id=sale.id,
            balance=part.stock_level,
            user_id=current_user.id,
            notes=f'Sale at {format_price_nkf(price)} per unit'
        )
        
        db.session.add(bincard)
        db.session.add(financial_transaction)
        db.session.commit()
        
        flash(f'Sale recorded successfully. Total amount: {format_price_nkf(total_amount)}', 'success')
        return redirect(url_for('sales.list_sales'))
        
    parts = Part.query.filter(Part.stock_level > 0).all()
    customers = Customer.query.all()
    return render_template('sales/new.html', parts=parts, customers=customers)

@sales.route('/api/parts/search')
@login_required
def search_parts():
    query = request.args.get('q', '')
    parts = Part.query.filter(
        (Part.name.ilike(f'%{query}%')) |
        (Part.part_number.ilike(f'%{query}%'))
    ).all()
    return jsonify([{
        'id': part.id,
        'name': part.name,
        'part_number': part.part_number,
        'stock_level': part.stock_level,
        'price': part.max_price
    } for part in parts])

@sales.route('/sales/<int:sale_id>')
@login_required
def view_sale(sale_id):
    sale = Transaction.query.filter_by(id=sale_id, type='sale').first_or_404()
    return render_template('sales/view.html', sale=sale)

@sales.route('/sales/export/pdf')
@login_required
def export_pdf():
    # Get filters from query params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user = request.args.get('user')

    query = Transaction.query.filter_by(type='sale').filter(
        ((Transaction.status == None) | (Transaction.status != 'cancelled')) & (Transaction.voided == False)
    )
    if start_date:
        query = query.filter(func.date(Transaction.date) >= start_date)
    if end_date:
        query = query.filter(func.date(Transaction.date) <= end_date)
    if user:
        query = query.join(User).filter(User.username == user)
    sales = query.order_by(Transaction.date.desc()).all()

    # Prepare title and headers like other reports
    title = "Sales History"
    filter_parts = []
    if start_date:
        filter_parts.append(f"From: {start_date}")
    if end_date:
        filter_parts.append(f"To: {end_date}")
    if user:
        filter_parts.append(f"User: {user}")
    if filter_parts:
        title += " (" + ", ".join(filter_parts) + ")"
    headers = ['Date', 'Part', 'Quantity', 'Price', 'Total', 'Sold By', 'Payment Method', 'Note']

    # Custom PDF header using reportlab
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    # Header
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=24, alignment=1, textColor=colors.HexColor('#1a237e'))
    elements.append(Paragraph("SPMS by EMANA Solutions", header_style))
    elements.append(Spacer(1, 8))
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading2'], fontSize=18, alignment=0, textColor=colors.HexColor('#1976d2'))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 8))
    # Info rows
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=13, alignment=0, textColor=colors.HexColor('#333333'))
    elements.append(Paragraph(f"Printed Date: <b>{datetime.now(pytz.timezone('Africa/Nairobi')).strftime('%Y-%m-%d %H:%M:%S')}</b>", info_style))
    elements.append(Paragraph(f"Printed By: <b>{current_user.username}</b>", info_style))
    elements.append(Paragraph(f"Start Date: <b>{start_date if start_date else '-'} </b> | End Date: <b>{end_date if end_date else '-'}</b>", info_style))
    if user:
        elements.append(Paragraph(f"Filtered User: <b>{user}</b>", info_style))
    elements.append(Spacer(1, 16))
    # Prepare table data with Paragraphs for wrapping
    data = [headers]
    for sale in sales:
        data.append([
            Paragraph(sale.date.strftime('%Y-%m-%d %H:%M'), styles['Normal']),
            Paragraph(sale.part.name if sale.part else 'N/A', styles['Normal']),
            Paragraph(str(sale.quantity), styles['Normal']),
            Paragraph(f"{sale.price:,.2f} NKF", styles['Normal']),
            Paragraph(f"{(sale.price * sale.quantity):,.2f} NKF", styles['Normal']),
            Paragraph(sale.user.username if sale.user else 'N/A', styles['Normal']),
            Paragraph(sale.payment_method.capitalize() if sale.payment_method else 'N/A', styles['Normal']),
            Paragraph(sale.notes or '', styles['Normal'])
        ])
        # Add totals
    total_quantity = sum(sale.quantity for sale in sales)
    total_amount = sum(sale.price * sale.quantity for sale in sales)
    data.append(['', '', '', '', '', ''])  # Empty row
    data.append(['Grand Total', '', str(total_quantity), '', f"{total_amount:.2f} NKF", ''])
        
    col_widths = [90, 90, 60, 70, 70, 80, 110, 120]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBEFORE', (0, 0), (-1, -1), 1, colors.black),
        ('LINEAFTER', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ('LINEABOVE', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('WORDWRAP', (0, 0), (-1, -1)),
    ]))
    elements.append(table)
    doc.build(elements)
    
     
    
    
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='sales_history.pdf')