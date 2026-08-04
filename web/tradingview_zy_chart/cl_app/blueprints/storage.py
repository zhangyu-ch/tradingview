import json
import uuid

from flask import Blueprint, request
from flask_login import current_user, login_required

from tradingview_zy.tv_storage import (
    TVStorageError,
    normalize_chart_payload,
    normalize_drawing_payload,
    resolve_storage_owner,
)
from tradingview_zy.web_api_validation import (
    WebParameterError,
    parse_bounded_text,
    parse_positive_int,
)

from ..web_services import get_web_services

storage_bp = Blueprint("tv_storage", __name__)

@storage_bp.route('/tv/<version>/charts', methods=['GET', 'POST', 'DELETE'])
@login_required
def tv_charts(version):
    """TradingView chart layout storage."""
    services = get_web_services()
    try:
        client_id, user_id = resolve_storage_owner(request.args.get('client'), request.args.get('user'), current_user.get_id())
    except TVStorageError as error:
        return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)
    raw_chart_id = request.args.get('chart')
    if request.method == 'GET':
        if raw_chart_id is None:
            chart_list = services.database.tv_chart_list('chart', client_id, user_id)
            return {'status': 'ok', 'data': [{'timestamp': chart.timestamp, 'symbol': chart.symbol, 'resolution': chart.resolution, 'id': chart.id, 'name': chart.name} for chart in chart_list]}
        try:
            chart_id = parse_positive_int(raw_chart_id, field='chart')
        except WebParameterError as exc:
            return ({'status': 'error', 'error': 'invalid_chart_id', 'message': str(exc)}, 422)
        chart = services.database.tv_chart_get('chart', chart_id, client_id, user_id)
        if chart is None:
            return ({'status': 'error', 'error': 'chart_not_found'}, 404)
        return {'status': 'ok', 'data': {'content': chart.content, 'timestamp': chart.timestamp, 'name': chart.name, 'id': chart.id}}
    if request.method == 'DELETE':
        try:
            chart_id = parse_positive_int(raw_chart_id, field='chart')
        except WebParameterError as exc:
            return ({'status': 'error', 'error': 'invalid_chart_id', 'message': str(exc)}, 422)
        services.database.tv_chart_del('chart', chart_id, client_id, user_id)
        return {'status': 'ok'}
    chart_id = None
    if raw_chart_id is not None:
        try:
            chart_id = parse_positive_int(raw_chart_id, field='chart')
        except WebParameterError as exc:
            return ({'status': 'error', 'error': 'invalid_chart_id', 'message': str(exc)}, 422)
    try:
        payload = normalize_chart_payload(services.database.tv_storage_policy, chart_type='chart', client_id=client_id, user_id=user_id, name=request.form.get('name'), content=request.form.get('content'), symbol=request.form.get('symbol'), resolution=request.form.get('resolution'))
        if chart_id is None:
            saved_id = services.database.tv_chart_save(**payload)
            return {'status': 'ok', 'id': saved_id}
        updated = services.database.tv_chart_update(id=chart_id, **payload)
        if updated is not True:
            return ({'status': 'error', 'error': 'chart_not_found'}, 404)
        return {'status': 'ok'}
    except TVStorageError as error:
        return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)

@storage_bp.route('/tv/<version>/study_templates', methods=['GET', 'POST', 'DELETE'])
@login_required
def tv_study_templates(version):
    """TradingView indicator template storage."""
    services = get_web_services()
    try:
        client_id, user_id = resolve_storage_owner(request.args.get('client'), request.args.get('user'), current_user.get_id())
    except TVStorageError as error:
        return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)
    if request.method == 'GET':
        raw_name = request.args.get('template')
        if raw_name is None:
            template_list = services.database.tv_chart_list('template', client_id, user_id)
            return {'status': 'ok', 'data': [{'name': template.name} for template in template_list]}
        try:
            name = parse_bounded_text(raw_name, field='template', max_chars=200)
        except WebParameterError as exc:
            return ({'status': 'error', 'error': 'invalid_template_name', 'message': str(exc)}, 422)
        template = services.database.tv_chart_get_by_name('template', name, client_id, user_id)
        if template is None:
            return ({'status': 'error', 'error': 'template_not_found'}, 404)
        return {'status': 'ok', 'data': {'name': template.name, 'content': template.content}}
    if request.method == 'DELETE':
        try:
            name = parse_bounded_text(request.args.get('template'), field='template', max_chars=200)
        except WebParameterError as exc:
            return ({'status': 'error', 'error': 'invalid_template_name', 'message': str(exc)}, 422)
        services.database.tv_chart_del_by_name('template', name, client_id, user_id)
        return {'status': 'ok'}
    try:
        payload = normalize_chart_payload(services.database.tv_storage_policy, chart_type='template', client_id=client_id, user_id=user_id, name=request.form.get('name'), content=request.form.get('content'), symbol='', resolution='')
        saved_id = services.database.tv_chart_save(**payload)
    except TVStorageError as error:
        return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)
    return {'status': 'ok', 'id': saved_id}

@storage_bp.route('/tv/<version>/drawings', methods=['GET', 'POST'])
@login_required
def tv_drawings(version):
    """TradingView drawing persistence with explicit failure semantics."""
    services = get_web_services()
    protocol_client_id = str(request.args.get('client') or '')
    protocol_user_id = str(request.args.get('user') or '')
    chart_id = str(request.args.get('chart') or '')
    layout_id = str(request.args.get('layout') or '')
    symbol = str(request.args.get('symbol') or '')
    if request.method == 'GET':
        if protocol_client_id == '' or protocol_user_id == '' or chart_id == '' or (layout_id == ''):
            return {'status': 'ok', 'data': {'state': ''}}
        try:
            client_id, user_id = resolve_storage_owner(protocol_client_id, protocol_user_id, current_user.get_id())
        except TVStorageError as error:
            return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)
        state = services.database.tv_drawing_get(client_id, user_id, layout_id, chart_id, symbol)
        return {'status': 'ok', 'data': {'state': state or ''}}
    state = request.form.get('state')
    if state is None:
        data = request.get_json(silent=True) or {}
        state = data.get('state')
    if state is not None and symbol == '':
        try:
            state_obj = json.loads(state) if isinstance(state, str) else state
            if isinstance(state_obj, dict):
                symbol = str(state_obj.get('symbol') or '')
        except (TypeError, ValueError, json.JSONDecodeError):
            symbol = ''
    if protocol_client_id == '' or protocol_user_id == '' or chart_id == '' or (layout_id == '') or (state is None):
        return ({'status': 'error', 'error': 'invalid_drawing_request', 'message': 'client, user, chart, layout and state are required'}, 422)
    try:
        client_id, user_id = resolve_storage_owner(protocol_client_id, protocol_user_id, current_user.get_id())
        payload = normalize_drawing_payload(services.database.tv_storage_policy, client_id=client_id, user_id=user_id, layout_id=layout_id, chart_id=chart_id, symbol=symbol, state=state)
    except TVStorageError as error:
        return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)
    request_id = uuid.uuid4().hex
    try:
        saved = services.database.tv_drawing_save_or_update(**payload)
    except TVStorageError as error:
        return ({'status': 'error', 'error': error.code, 'message': str(error)}, 422)
    except Exception:
        services.logger.exception('drawing save failed request_id=%s', request_id)
        return ({'status': 'error', 'error': 'drawing_save_failed', 'request_id': request_id}, 500)
    if saved is not True:
        services.logger.error('drawing save was not confirmed request_id=%s', request_id)
        return ({'status': 'error', 'error': 'drawing_save_failed', 'request_id': request_id}, 500)
    return {'status': 'ok'}
