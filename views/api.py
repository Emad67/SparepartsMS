from flask import jsonify
from utils import format_price_nkf

return jsonify({
    'price': format_price_nkf(part.price),
    'total': format_price_nkf(total_amount)
})