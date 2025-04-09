from flask import Blueprint
from models import ExchangeRate

def format_price_nkf(value):
    """Convert USD to NKF and format with currency symbol"""
    if value is None:
        return "NKF 0.00"
    rate = ExchangeRate.get_rate_for_date()
    nkf_amount = value * rate
    return f"NKF {nkf_amount:,.2f}"

def get_current_rate():
    """Get current exchange rate"""
    return ExchangeRate.get_rate_for_date()

def register_template_filters(app):
    app.jinja_env.filters['nkf'] = format_price_nkf
    app.jinja_env.globals['get_current_rate'] = get_current_rate