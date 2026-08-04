from flask import Blueprint, render_template
from flask_login import login_required

from ..web_services import get_web_services

pages_bp = Blueprint("pages", __name__)

@pages_bp.route('/')
@login_required
def index_show():
    """
        首页
        """
    services = get_web_services()
    return render_template('index.html', market_default_codes=services.market_default_codes, market_frequencys=services.market_frequencies, market_catalog=services.market_catalog, default_market=services.default_market)
