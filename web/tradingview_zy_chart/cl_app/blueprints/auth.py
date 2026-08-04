import datetime

from flask import Blueprint, redirect, render_template, request, session
from flask_login import (
    LoginManager,
    UserMixin,
    login_required,
    login_user,
    logout_user,
)

from tradingview_zy.web_security import rotate_csrf_token, verify_login_password

from ..web_services import get_web_services

auth_bp = Blueprint("auth", __name__)


class LoginUser(UserMixin):
    def __init__(self, user_id: str | None = None) -> None:
        super().__init__()
        self.id = user_id or get_web_services().storage_principal

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_opt():
    services = get_web_services()
    if services.auto_login:
        login_user(LoginUser(), remember=False)
        return redirect('/')
    emsg = ''
    if request.method == 'POST':
        remote_key = request.remote_addr or 'unknown'
        if not services.login_limiter.is_allowed(remote_key):
            return (render_template('login.html', emsg='登录失败次数过多，请稍后再试'), 429)
        password = request.form.get('password')
        if verify_login_password(password, services.login_password, services.login_password_hash):
            services.login_limiter.reset(remote_key)
            login_user(LoginUser(), remember=services.remember_days > 0, duration=datetime.timedelta(days=max(services.remember_days, 1)))
            rotate_csrf_token(session)
            return redirect('/')
        services.login_limiter.record_failure(remote_key)
        emsg = '密码错误'
    return render_template('login.html', emsg=emsg)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout_opt():
    logout_user()
    rotate_csrf_token(session)
    return redirect('/login')

def init_auth(app) -> LoginManager:
    services = app.extensions["tradingview_zy.web_services"]
    login_manager = LoginManager()
    login_manager.session_protection = "basic"
    login_manager.login_view = "auth.login_opt"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return LoginUser(services.storage_principal) if user_id == services.storage_principal else None

    app.extensions["login_manager"] = login_manager
    return login_manager
