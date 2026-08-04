from flask import Blueprint, current_app, request, session

from tradingview_zy.web_security import get_csrf_token, validate_csrf_request

from ..web_services import get_web_services

core_bp = Blueprint("core", __name__)

@core_bp.app_errorhandler(413)
def request_too_large(_error):
    return ({'status': 'error', 'error': 'request_too_large', 'message': 'request body exceeds the configured limit'}, 413)

@core_bp.app_context_processor
def inject_csrf_token():
    return {'csrf_token': lambda: get_csrf_token(session)}

@core_bp.before_app_request
def protect_unsafe_requests():
    services = get_web_services()
    valid, reason = validate_csrf_request(request, session, trusted_origins=services.csrf_trusted_origins)
    if valid:
        return None
    current_app.logger.warning('CSRF request rejected endpoint=%s reason=%s', request.endpoint, reason)
    return ({'ok': False, 'error': 'csrf_failed', 'msg': '请求安全校验失败，请刷新页面后重试'}, 403)
