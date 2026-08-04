from flask import Blueprint, render_template, request
from flask_login import login_required

from tradingview_zy.base import Market
from tradingview_zy.settings_security import (
    feishu_secret_is_configured,
    merge_feishu_settings,
    migrate_feishu_settings,
    retire_superseded_feishu_secret,
)

from ..web_services import get_web_services

settings_bp = Blueprint("settings", __name__)

@settings_bp.route('/setting', methods=['GET'])
@login_required
def setting():
    services = get_web_services()
    proxy = services.database.cache_get('req_proxy')
    secret_store = services.secret_store_factory(services.get_data_path())
    fs_setting, migrated = migrate_feishu_settings(services.database.cache_get('fs_keys'), store=secret_store)
    if migrated:
        services.database.cache_set('fs_keys', fs_setting)
    set_config = {'fs_app_id': fs_setting.get('fs_app_id', ''), 'fs_app_secret_configured': feishu_secret_is_configured(fs_setting, store=secret_store), 'fs_user_id': fs_setting.get('fs_user_id', ''), 'proxy_host': proxy.get('host', '') if proxy else '', 'proxy_port': proxy.get('port', '') if proxy else ''}
    return (render_template('setting.html', **set_config), 200, {'Cache-Control': 'no-store', 'Pragma': 'no-cache'})

@settings_bp.route('/setting/save', methods=['POST'])
@login_required
def setting_save():
    services = get_web_services()
    proxy = {'host': request.form.get('proxy_host', '').strip(), 'port': request.form.get('proxy_port', '').strip()}
    secret_store = services.secret_store_factory(services.get_data_path())
    existing, migrated = migrate_feishu_settings(services.database.cache_get('fs_keys'), store=secret_store)
    if migrated:
        services.database.cache_set('fs_keys', existing)
    fs_keys, superseded_reference = merge_feishu_settings(existing, app_id=request.form.get('fs_app_id'), app_secret=request.form.get('fs_app_secret'), user_id=request.form.get('fs_user_id'), store=secret_store)
    services.database.cache_set('req_proxy', proxy)
    services.database.cache_set('fs_keys', fs_keys)
    retire_superseded_feishu_secret(secret_store, superseded_reference)
    return ({'ok': True}, 200, {'Cache-Control': 'no-store'})

@settings_bp.route('/a/bkgn_list', methods=['GET'])
@login_required
def a_bkgn_list():
    """
        获取沪深a股市场的板块列表
        """
    services = get_web_services()
    stock_bkgn = services.stocks_bkgn_factory()
    bkgn_infos = stock_bkgn.file_bkgns()
    all_hy_names = bkgn_infos['hys']
    all_gn_names = bkgn_infos['gns']
    res_bkgn_list = []
    for _hy in all_hy_names:
        res_bkgn_list.append({'type': 'hy', 'bkgn_name': f'行业:{_hy}', 'bkgn_code': _hy})
    for _gn in all_gn_names:
        res_bkgn_list.append({'type': 'gn', 'bkgn_name': f'概念:{_gn}', 'bkgn_code': _gn})
    return {'code': 0, 'msg': '', 'data': res_bkgn_list, 'count': len(res_bkgn_list)}

@settings_bp.route('/a/bkgn_codes', methods=['POST'])
@login_required
def a_bkgn_codes():
    services = get_web_services()
    bkgn_type = request.form['bkgn_type']
    bkgn_code = request.form['bkgn_code']
    stock_bkgn = services.stocks_bkgn_factory()
    if bkgn_type == 'hy':
        codes = stock_bkgn.ths_to_tdx_codes(stock_bkgn.get_codes_by_hy(bkgn_code))
    elif bkgn_type == 'gn':
        codes = stock_bkgn.ths_to_tdx_codes(stock_bkgn.get_codes_by_gn(bkgn_code))
    else:
        codes = []
    ex = services.get_exchange(Market.A)
    stocks = {}
    for _code in codes:
        _stock = ex.stock_info(_code)
        if _stock is not None:
            stocks[_code] = _stock
    return {'code': 0, 'msg': '', 'data': stocks, 'count': len(stocks)}
