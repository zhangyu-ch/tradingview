import json

from flask import Blueprint, render_template, request
from flask_login import login_required

from tradingview_zy.alert_strategy_storage import (
    StrategyStorageValidationError,
    build_strategy_config,
    normalize_strategy_memo,
    parse_strategy_kwargs,
    parse_strategy_parameters,
)
from tradingview_zy.base import Market
from tradingview_zy.data_contracts import StrategyParameters
from tradingview_zy.strategies.loader import (
    StrategyRegistryError,
    find_registered_strategy_id_by_path,
    registered_strategy_choices,
    validate_registered_strategy,
)

from ..web_services import get_web_services

tasks_bp = Blueprint("tasks", __name__)

@tasks_bp.route('/alert_list/<market>')
@login_required
def alert_list(market):
    services = get_web_services()
    alert_tasks, task_error = services.alert_tasks.resolve()
    if task_error is not None:
        payload = task_error.to_payload()
        payload.update({'code': 1, 'count': 0, 'data': []})
        return payload, 503
    al = alert_tasks.task_list(market)
    al = [{'id': _l.id, 'market': _l.market, 'task_name': _l.task_name, 'zx_group': _l.zx_group, 'interval_minutes': _l.interval_minutes, 'frequency': _l.frequency, 'strategy_config': _l.strategy_config, 'strategy_memo': _l.strategy_memo, 'is_send_msg': _l.is_send_msg, 'is_run': _l.is_run} for _l in al]
    return {'code': 0, 'msg': '', 'count': len(al), 'data': al}

@tasks_bp.route('/alert_edit/<market>/<id>')
@login_required
def alert_edit(market, id):
    services = get_web_services()
    alert_tasks, task_error = services.alert_tasks.resolve()
    if task_error is not None:
        return task_error.to_payload(), 503
    strategy_registry = getattr(services.config, 'ALERT_STRATEGIES', {})
    try:
        alert_strategies = registered_strategy_choices(strategy_registry)
    except (StrategyRegistryError, ValueError, TypeError) as error:
        return {'ok': False, 'msg': f'ALERT_STRATEGIES 配置错误：{error}'}
    default_strategy_id = alert_strategies[0].strategy_id if alert_strategies else ''
    alert_config = {'id': '', 'market': market, 'task_name': '', 'zx_group': '我的关注', 'interval_minutes': 5, 'frequency': '5m', 'strategy_id': default_strategy_id, 'strategy_kwargs': '{}', 'strategy_memo': '', 'legacy_strategy_path': '', 'unavailable_strategy_id': '', 'is_send_msg': 1, 'is_run': 1}
    if id != '0':
        _alert_config = alert_tasks.alert_get(id)
        if _alert_config is not None:
            try:
                parameters = parse_strategy_parameters(_alert_config.strategy_config or '{}')
            except StrategyStorageValidationError:
                parameters = StrategyParameters()
            strategy_id = parameters.strategy_id
            legacy_strategy_path = parameters.strategy_path
            unavailable_strategy_id = ''
            if strategy_id and strategy_id not in strategy_registry:
                unavailable_strategy_id = str(strategy_id)
                strategy_id = ''
            if not strategy_id and legacy_strategy_path:
                strategy_id = find_registered_strategy_id_by_path(strategy_registry, legacy_strategy_path) or ''
            alert_config = {'id': _alert_config.id, 'market': _alert_config.market, 'task_name': _alert_config.task_name, 'zx_group': _alert_config.zx_group, 'interval_minutes': _alert_config.interval_minutes, 'frequency': _alert_config.frequency, 'strategy_id': strategy_id, 'strategy_kwargs': json.dumps(parameters.kwargs, ensure_ascii=False), 'strategy_memo': _alert_config.strategy_memo, 'legacy_strategy_path': legacy_strategy_path if not strategy_id else '', 'unavailable_strategy_id': unavailable_strategy_id, 'is_send_msg': _alert_config.is_send_msg, 'is_run': _alert_config.is_run}
    zx = services.zixuan_factory(market)
    zixuan_groups = zx.zixuan_list
    frequencys = services.get_exchange(Market(market)).support_frequencys()
    return render_template('alert.html', zixuan_groups=zixuan_groups, frequencys=frequencys, alert_strategies=alert_strategies, **alert_config)

@tasks_bp.route('/alert_save', methods=['POST'])
@login_required
def alert_save():
    services = get_web_services()
    alert_tasks, task_error = services.alert_tasks.resolve()
    if task_error is not None:
        return task_error.to_payload(), 503
    strategy_id = request.form.get('strategy_id', '').strip()
    if strategy_id == '':
        return {'ok': False, 'msg': '请选择已注册策略'}
    try:
        strategy_kwargs = parse_strategy_kwargs(request.form.get('strategy_kwargs'))
    except StrategyStorageValidationError as error:
        return {'ok': False, 'msg': str(error)}
    strategy_registry = getattr(services.config, 'ALERT_STRATEGIES', {})
    try:
        validate_registered_strategy(strategy_registry, strategy_id, strategy_kwargs)
    except Exception as error:
        return {'ok': False, 'msg': f'策略配置无效：{error}'}
    try:
        interval_minutes = int(request.form.get('interval_minutes', '5'))
        is_send_msg = int(request.form.get('is_send_msg', '1'))
        is_run = int(request.form.get('is_run', '1'))
    except ValueError as error:
        return {'ok': False, 'msg': f'数值字段格式错误：{error}'}
    try:
        strategy_config = build_strategy_config(strategy_id, strategy_kwargs)
        strategy_memo = normalize_strategy_memo(request.form.get('strategy_memo', ''))
    except StrategyStorageValidationError as error:
        return {'ok': False, 'msg': str(error)}
    alert_config = {'id': request.form.get('id', ''), 'market': request.form.get('market', ''), 'task_name': request.form.get('task_name', ''), 'interval_minutes': interval_minutes, 'zx_group': request.form.get('zx_group', ''), 'frequency': request.form.get('frequency', ''), 'strategy_config': strategy_config, 'strategy_memo': strategy_memo, 'is_send_msg': is_send_msg, 'is_run': is_run}
    alert_tasks.alert_save(alert_config)
    return {'ok': True}

@tasks_bp.route('/alert_del/<id>', methods=['POST'])
@login_required
def alert_del(id):
    services = get_web_services()
    alert_tasks, task_error = services.alert_tasks.resolve()
    if task_error is not None:
        return task_error.to_payload(), 503
    res = alert_tasks.alert_del(id)
    return {'ok': res}

@tasks_bp.route('/alert_records/<market>')
@login_required
def alert_records(market):
    services = get_web_services()
    task_name = request.args.get('task_name')
    records = services.database.alert_record_query(market, task_name)
    rls = [{'event_type': _r.event_type, 'action': _r.action, 'score': _r.score, 'event_time': _r.event_time, 'msg': _r.alert_msg, 'code': _r.stock_code, 'name': _r.stock_name, 'frequency': _r.frequency, 'task_name': _r.task_name, 'datetime_str': services.fun.datetime_to_str(_r.alert_dt)} for _r in records]
    return {'code': 0, 'msg': '', 'count': len(rls), 'data': rls}

@tasks_bp.route('/jobs')
@login_required
def jobs():
    services = get_web_services()
    return render_template('jobs.html', jobs=services.scheduler_status_store.read())

@tasks_bp.route('/xuangu/task_list/<market>')
@login_required
def xuangu_task_list(market):
    services = get_web_services()
    xuangu_tasks, task_error = services.xuangu_tasks.resolve()
    if task_error is not None:
        return task_error.to_payload(), 503
    zx = services.zixuan_factory(market)
    zixuan_groups = zx.zixuan_list
    frequencys = services.get_exchange(Market(market)).support_frequencys()
    xuangu_task_configs = xuangu_tasks.xuangu_task_config_list()
    xuangu_task_list = {_k: {**_v, 'name': _v.get('name', _k)} for _k, _v in xuangu_task_configs.items()}
    task_infos = {_k: {'task_memo': _v.get('task_memo', _v.get('description', '')), 'frequency_memo': _v.get('frequency_memo', '自定义策略周期')} for _k, _v in xuangu_task_list.items()}
    return render_template('xuangu_list.html', market=market, tasks=xuangu_task_list, task_infos=task_infos, zixuan_groups=zixuan_groups, frequencys=frequencys)

@tasks_bp.route('/xuangu/task_add', methods=['POST'])
@login_required
def xuangu_task_add():
    services = get_web_services()
    xuangu_tasks, task_error = services.xuangu_tasks.resolve()
    if task_error is not None:
        return task_error.to_payload(), 503
    market = request.form['market']
    task_name = request.form['task_name']
    frequencys = request.form['frequencys']
    src_zx_group = request.form['src_zx_group']
    target_zx_group = request.form.get('target_zx_group', '').strip()
    frequencys = frequencys.split(',')
    if task_name not in xuangu_tasks.xuangu_task_config_list().keys():
        return {'ok': False, 'msg': '选股任务不存在'}
    allow_freq_num = xuangu_tasks.xuangu_task_config_list()[task_name].get('frequency_num', len(frequencys))
    if len(frequencys) != allow_freq_num:
        return {'ok': False, 'msg': f'选股周期错误，该任务可选周期数量 : {allow_freq_num}'}
    run_res = xuangu_tasks.run_xuangu(market, task_name, frequencys, src_zx_group, target_zx_group)
    return {'ok': run_res, 'msg': '选股任务已存在，请在当前任务中查看任务' if run_res is False else ''}
