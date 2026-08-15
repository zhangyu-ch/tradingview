from flask import Blueprint, render_template
from flask_login import login_required

from ..web_services import get_web_services

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
@login_required
def index_show():
    """首页。"""

    services = get_web_services()
    market_frequencies = {
        market: list(frequencies)
        for market, frequencies in services.market_frequencies.items()
    }
    return render_template(
        "index.html",
        market_default_codes=dict(services.market_default_codes),
        market_frequencys=market_frequencies,
        market_catalog=[dict(item) for item in services.market_catalog],
        default_market=services.default_market,
    )
