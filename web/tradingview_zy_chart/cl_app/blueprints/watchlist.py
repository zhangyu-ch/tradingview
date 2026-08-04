from io import BytesIO

from flask import Blueprint, render_template, request, send_file
from flask_login import login_required

from tradingview_zy.base import Market
from tradingview_zy.watchlist_transfer import (
    WatchlistTransferError,
    export_watchlist_text,
    parse_watchlist_stream,
)

from ..web_services import get_web_services

watchlist_bp = Blueprint("watchlist", __name__)

@watchlist_bp.route('/get_zixuan_groups/<market>')
@login_required
def get_zixuan_groups(market):
    services = get_web_services()
    zx = services.zixuan_factory(market)
    groups = zx.get_zx_groups()
    return groups

@watchlist_bp.route('/get_zixuan_stocks/<market>/<group_name>')
@login_required
def get_zixuan_stocks(market, group_name):
    services = get_web_services()
    zx = services.zixuan_factory(market)
    stock_list = zx.zx_stocks(group_name)
    return {'code': 0, 'msg': '', 'count': len(stock_list), 'data': stock_list}

@watchlist_bp.route('/get_stock_zixuan/<market>/<code>')
@login_required
def get_stock_zixuan(market, code: str):
    services = get_web_services()
    code = code.replace('__', '/')
    zx = services.zixuan_factory(market)
    zx_groups = zx.query_code_zx_names(code)
    return zx_groups

@watchlist_bp.route('/zixuan_group/<market>', methods=['GET'])
@login_required
def zixuan_group_view(market):
    services = get_web_services()
    zx = services.zixuan_factory(market)
    zx_groups = zx.get_zx_groups()
    return render_template('zixuan.html', market=market, zx_groups=zx_groups)

@watchlist_bp.route('/opt_zixuan_group/<market>', methods=['POST'])
@login_required
def opt_zixuan_group(market):
    """
        操作自选组
        """
    services = get_web_services()
    opt = request.form['opt']
    zx_group = request.form['zx_group']
    zx = services.zixuan_factory(market)
    if opt == 'DEL':
        return {'ok': zx.del_zx_group(zx_group)}
    else:
        return {'ok': zx.add_zx_group(zx_group)}

@watchlist_bp.route('/zixuan_opt_export', methods=['GET'])
@login_required
def opt_zixuan_export():
    """导出自选组；响应使用请求私有内存流，不写共享临时文件。"""
    services = get_web_services()
    market = request.args.get('market')
    zx_group = request.args.get('zx_group')
    zx = services.zixuan_factory(market)
    output = export_watchlist_text(zx.zx_stocks(zx_group)).encode('utf-8')
    return send_file(BytesIO(output), mimetype='text/plain; charset=utf-8', as_attachment=True, download_name='zixuan_export.txt', max_age=0)

@watchlist_bp.route('/zixuan_opt_import', methods=['POST'])
@login_required
def opt_zixuan_import():
    """导入经过大小、编码、行数与字段边界校验的 UTF-8 文本。"""
    services = get_web_services()
    market = request.form.get('market', '')
    zx_group = request.form.get('zx_group', '').strip()
    upload = request.files.get('file')
    if upload is None or not upload.filename:
        return ({'ok': False, 'msg': '请选择导入文件'}, 400)
    if not upload.filename.lower().endswith('.txt'):
        return ({'ok': False, 'msg': '只允许上传 .txt 文件'}, 422)
    if not zx_group or len(zx_group) > 100:
        return ({'ok': False, 'msg': '自选组名称无效'}, 422)
    try:
        ex = services.get_exchange(Market(market))
        market_all_stocks = ex.all_stocks()
        entries = parse_watchlist_stream(upload.stream, market=market, available_codes=(stock['code'] for stock in market_all_stocks), max_bytes=services.max_upload_bytes, max_lines=services.max_watchlist_lines, max_line_bytes=services.max_watchlist_line_bytes)
    except (ValueError, KeyError, WatchlistTransferError) as exc:
        status_code = getattr(exc, 'status_code', 422)
        return ({'ok': False, 'msg': str(exc) or '导入文件无效'}, status_code)
    zx = services.zixuan_factory(market)
    for entry in entries:
        zx.add_stock(zx_group, entry.code, entry.name)
    return {'ok': True, 'msg': f'成功导入 {len(entries)} 条记录'}

@watchlist_bp.route('/set_stock_zixuan', methods=['POST'])
@login_required
def set_stock_zixuan():
    services = get_web_services()
    market = request.form['market']
    opt = request.form['opt']
    group_name = request.form['group_name']
    code = request.form['code']
    zx = services.zixuan_factory(market)
    if opt == 'DEL':
        res = zx.del_stock(group_name, code)
    elif opt == 'ADD':
        res = zx.add_stock(group_name, code, None)
    elif opt == 'COLOR':
        color = request.form['color']
        res = zx.color_stock(group_name, code, color)
    elif opt == 'SORT':
        direction = request.form['direction']
        if direction == 'top':
            res = zx.sort_top_stock(group_name, code)
        else:
            res = zx.sort_bottom_stock(group_name, code)
    else:
        res = False
    return {'ok': res}
