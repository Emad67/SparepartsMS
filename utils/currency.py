from models import ExchangeRate

def get_nkf_amount(usd_amount, date=None):
    rate = ExchangeRate.get_rate_for_date(date)
    return usd_amount * rate

def format_nkf(amount):
    """Format amount in NKF with exchange rate conversion"""
    if amount is None:
        return "NKF 0.00"
    rate = ExchangeRate.get_rate_for_date()
    nkf_amount = amount * rate
    return f"NKF {nkf_amount:,.2f}"

def get_usd_amount(nkf_amount, date=None):
    rate = ExchangeRate.get_rate_for_date(date)
    if not rate or rate == 0:
        raise ValueError("Invalid exchange rate")
    return nkf_amount / rate