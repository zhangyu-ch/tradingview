import datetime
import time

from flask import Blueprint, request, session
from flask_login import login_required

from tradingview_zy.base import Market
from tradingview_zy.footprint import SUB_FREQUENCY_MAP, aggregate_footprint
from tradingview_zy.market_metadata import (
    all_market_frequencies,
    market_ui_metadata,
    tradingview_symbol_metadata,
)
from tradingview_zy.tick_request import (
    TickProviderBusyError,
    TickProviderCallError,
    TickProviderTimeoutError,
    TickRateLimitError,
    TickRequestError,
    parse_tick_request,
)
from tradingview_zy.web_api_validation import (
    WebParameterError,
    parse_bounded_text,
    parse_int,
    parse_market,
    parse_resolution,
    parse_strict_bool,
    parse_symbol,
    parse_time_range,
)
from tradingview_zy.web_payloads import (
    KlinePayloadError,
    datetime_to_timestamp_seconds,
    filter_klines_by_timestamp_range,
    klines_to_tv_history,
    market_timezone as resolve_market_timezone,
    prepare_klines_for_market,
)
from tradingview_zy.history_request_tracker import history_request_key

from ..web_services import get_web_services

udf_bp = Blueprint("udf", __name__)

@udf_bp.route('/tv/config')
@login_required
def tv_config():
    """
        配置项
        """
    services = get_web_services()
    frequencys = all_market_frequencies(services.market_frequencies)
    supportedResolutions = [v for k, v in services.frequency_maps.items() if k in frequencys]
    return {'supports_search': True, 'supports_group_request': False, 'supported_resolutions': supportedResolutions, 'supports_marks': True, 'supports_timescale_marks': True, 'supports_time': False, 'exchanges': [{'value': item['value'], 'name': item['name'], 'desc': item['desc']} for item in services.market_catalog]}

@udf_bp.route('/tv/symbol_info')
@login_required
def tv_symbol_info():
    services = get_web_services()
    try:
        group = parse_market(request.args.get('group'), allowed_markets=services.market_frequencies.keys(), field='group')
    except WebParameterError as exc:
        return {'s': 'error', 'errmsg': str(exc)}
    ex = services.get_exchange(Market(group))
    all_symbols = ex.all_stocks()
    return {'symbol': [stock['code'] for stock in all_symbols], 'description': [stock['name'] for stock in all_symbols], 'exchange-listed': group, 'exchange-traded': group}

@udf_bp.route('/tv/symbols')
@login_required
def tv_symbols():
    services = get_web_services()
    try:
        market, code = parse_symbol(request.args.get('symbol'), allowed_markets=services.market_frequencies.keys())
    except WebParameterError as exc:
        return {'s': 'error', 'errmsg': str(exc)}
    ex = services.get_exchange(Market(market))
    stocks = ex.stock_info(code)
    symbol_metadata = tradingview_symbol_metadata(market, stocks['code'])
    sector = ''
    industry = ''
    ui_metadata = market_ui_metadata(market)
    if ui_metadata['plate_panel']:
        try:
            gnbk = ex.stock_owner_plate(code)
            sector = ' / '.join([item['name'] for item in gnbk['GN']])
            industry = ' / '.join([item['name'] for item in gnbk['HY']])
        except Exception:
            pass
    return {'name': stocks['code'], 'ticker': f"{market}:{stocks['code']}", 'full_name': f"{market}:{stocks['code']}", 'description': stocks['name'], 'exchange': market, **symbol_metadata, 'pricescale': stocks.get('precision', 1000), 'visible_plots_set': 'ohlcv', 'supported_resolutions': [value for key, value in services.frequency_maps.items() if key in services.market_frequencies[market]], 'intraday_multipliers': ['1', '2', '3', '5', '10', '15', '20', '30', '60', '120', '240'], 'seconds_multipliers': ['1', '2', '3', '5', '10', '15', '20', '30', '40', '50', '60'], 'daily_multipliers': ['1', '2'], 'minmov': 1, 'minmov2': 0, 'has_intraday': True, 'has_seconds': ui_metadata['has_seconds'], 'has_daily': True, 'has_weekly_and_monthly': True, 'sector': sector, 'industry': industry}

@udf_bp.route('/tv/search')
@login_required
def tv_search():
    import pinyin
    services = get_web_services()
    try:
        query = parse_bounded_text(request.args.get('query', ''), field='query', max_chars=100, allow_empty=True)
        type_value = parse_bounded_text(request.args.get('type', ''), field='type', max_chars=32, allow_empty=True).lower()
        exchange = parse_market(request.args.get('exchange'), allowed_markets=services.market_frequencies.keys(), field='exchange')
        limit = parse_int(request.args.get('limit', '30'), field='limit', minimum=1, maximum=100)
    except WebParameterError as exc:
        return ({'error': 'invalid_search_request', 'message': str(exc)}, 422)
    authoritative_type = tradingview_symbol_metadata(exchange)['type']
    if type_value and type_value != authoritative_type:
        return []
    ex = services.get_exchange(Market(exchange))
    all_stocks = ex.all_stocks()
    query_lower = query.lower()
    ui_metadata = market_ui_metadata(exchange)
    if not ui_metadata['search_name']:
        res_stocks = [stock for stock in all_stocks if query_lower in stock['code'].lower()]
    else:
        res_stocks = [stock for stock in all_stocks if query_lower in stock['code'].lower() or query_lower in stock['name'].lower() or query_lower in ''.join([pinyin.get_initial(char)[0] for char in stock['name']]).lower()]
    infos = []
    for stock in res_stocks[:limit]:
        symbol_metadata = tradingview_symbol_metadata(exchange, stock['code'])
        infos.append({'symbol': stock['code'], 'name': stock['code'], 'full_name': f"{exchange}:{stock['code']}", 'description': stock['name'], 'exchange': exchange, 'ticker': f"{exchange}:{stock['code']}", **symbol_metadata, 'supported_resolutions': [value for key, value in services.frequency_maps.items() if key in services.market_frequencies[exchange]]})
    return infos

@udf_bp.route('/tv/history')
@login_required
def tv_history():
    services = get_web_services()
    try:
        market, code = parse_symbol(request.args.get('symbol'), allowed_markets=services.market_frequencies.keys())
        resolution, frequency = parse_resolution(request.args.get('resolution'), resolution_map=services.resolution_maps)
        first_data_request = parse_strict_bool(request.args.get('firstDataRequest', 'false'), field='firstDataRequest')
        from_timestamp, to_timestamp = parse_time_range(request.args.get('from'), request.args.get('to'))
    except WebParameterError as exc:
        return {'s': 'error', 'errmsg': str(exc)}
    if from_timestamp < 0 and to_timestamp < 0:
        return {'s': 'no_data'}
    symbol = f'{market}:{code}'
    now_time = time.time()
    status = 'ok'
    if not first_data_request:
        status = services.history_request_tracker.record(history_request_key(user_id=session.get('_user_id'), remote_addr=request.remote_addr, market=market, code=code, resolution=resolution))
    ex = services.get_exchange(Market(market))
    if not first_data_request and from_timestamp >= int(now_time - 10 * 60) and (ex.now_trading(code) is False):
        return {'s': 'no_data', 'nextTime': int(now_time + 10 * 60)}
    klines = ex.klines(code, frequency)
    if klines is None or len(klines) == 0:
        return {'s': 'no_data'}
    try:
        klines = prepare_klines_for_market(klines, market, expected_code=code, expected_frequency=frequency)
        if to_timestamp < datetime_to_timestamp_seconds(klines.iloc[0]['date']):
            return {'s': 'no_data'}
        if not first_data_request:
            klines = filter_klines_by_timestamp_range(klines, from_timestamp, to_timestamp, market=market)
            if klines is None or len(klines) == 0:
                return {'s': 'no_data'}
        return klines_to_tv_history(klines, update=not first_data_request, status=status, market=market)
    except KlinePayloadError:
        return {'s': 'error', 'errmsg': 'invalid_kline_payload'}

@udf_bp.route('/tv/footprint')
@login_required
def tv_footprint():
    services = get_web_services()
    try:
        market, code = parse_symbol(request.args.get('symbol'), allowed_markets=services.market_frequencies.keys())
        resolution, frequency = parse_resolution(request.args.get('resolution'), resolution_map=services.resolution_maps)
        from_timestamp, to_timestamp = parse_time_range(request.args.get('from'), request.args.get('to'))
    except WebParameterError as exc:
        return {'s': 'error', 'errmsg': str(exc)}
    sub_frequency = SUB_FREQUENCY_MAP.get(frequency)
    ex = services.get_exchange(Market(market))
    if sub_frequency is None or sub_frequency not in ex.support_frequencys():
        return {'s': 'no_data'}
    symbol = f'{market}:{code}'
    cache_key = (symbol, frequency)
    footprint_bars = services.footprint_cache.get(cache_key)
    if footprint_bars is None:
        display_klines = ex.klines(code, frequency)
        sub_klines = ex.klines(code, sub_frequency)
        footprint_bars = aggregate_footprint(display_klines, sub_klines)
        services.footprint_cache.set(cache_key, footprint_bars)
    return {'s': 'ok', 'bars': {timestamp: bar for timestamp, bar in footprint_bars.items() if from_timestamp <= timestamp <= to_timestamp}}

@udf_bp.route('/tv/timescale_marks')
@login_required
def tv_timescale_marks():
    services = get_web_services()
    try:
        market, code = parse_symbol(request.args.get('symbol'), allowed_markets=services.market_frequencies.keys())
        _, frequency = parse_resolution(request.args.get('resolution'), resolution_map=services.resolution_maps)
        from_timestamp, to_timestamp = parse_time_range(request.args.get('from'), request.args.get('to'))
    except WebParameterError as exc:
        return {'s': 'error', 'errmsg': str(exc)}
    order_type_maps = {'buy': '买入', 'sell': '卖出', 'open_long': '买入开多', 'open_short': '买入开空', 'close_long': '卖出平多', 'close_short': '买入平空'}
    marks = []
    orders = services.database.order_query_by_code(market, code)
    for index, order in enumerate(orders):
        timestamp = services.fun.datetime_to_int(order['datetime'], assume_tz=resolve_market_timezone(market))
        if from_timestamp <= timestamp <= to_timestamp:
            is_buy = order['type'] in ['buy', 'open_long', 'close_short']
            marks.append({'id': index, 'time': timestamp, 'color': 'red' if is_buy else 'green', 'label': 'B' if is_buy else 'S', 'tooltip': [f"{order_type_maps[order['type']]}[{order['price']}/{order['amount']}]", f"{('' if 'info' not in order else order['info'])}"], 'shape': 'earningUp' if is_buy else 'earningDown'})
    for index, mark in enumerate(services.database.marks_query(market, code)):
        if (mark.frequency == '' or mark.frequency == frequency) and from_timestamp <= mark.mark_time <= to_timestamp:
            marks.append({'id': f'm-{index}', 'time': int(mark.mark_time), 'color': mark.mark_color, 'label': mark.mark_label, 'tooltip': mark.mark_tooltip, 'shape': mark.mark_shape})
    return marks

@udf_bp.route('/tv/marks')
@login_required
def tv_marks():
    services = get_web_services()
    try:
        market, code = parse_symbol(request.args.get('symbol'), allowed_markets=services.market_frequencies.keys())
        _, frequency = parse_resolution(request.args.get('resolution'), resolution_map=services.resolution_maps)
        from_timestamp, to_timestamp = parse_time_range(request.args.get('from'), request.args.get('to'))
    except WebParameterError as exc:
        return {'s': 'error', 'errmsg': str(exc)}
    marks = []
    price_marks = services.database.marks_query_by_price(market, code, start_date=from_timestamp)
    for index, mark in enumerate(price_marks):
        if (mark.frequency == '' or mark.frequency == frequency) and from_timestamp <= mark.mark_time <= to_timestamp:
            marks.append({'id': f'm-{index}', 'time': int(mark.mark_time), 'color': mark.mark_color, 'text': mark.mark_text, 'label': mark.mark_label, 'labelFontColor': mark.mark_label_font_color, 'minSize': mark.mark_min_size})
    return marks

@udf_bp.route('/tv/del_marks', methods=['POST'])
@login_required
def tv_del_marks():
    services = get_web_services()
    try:
        market, code = parse_symbol(request.form.get('symbol'), allowed_markets=services.market_frequencies.keys())
    except WebParameterError as exc:
        return ({'error': 'invalid_marks_request', 'message': str(exc)}, 422)
    services.database.marks_del_all_by_code(market, code)
    return {'status': 'ok'}

@udf_bp.route('/tv/time')
@login_required
def tv_time():
    """
        服务器时间
        """
    services = get_web_services()
    return services.fun.datetime_to_int(datetime.datetime.now(datetime.timezone.utc))

@udf_bp.route('/ticks', methods=['POST'])
@login_required
def ticks():
    services = get_web_services()
    try:
        tick_request = parse_tick_request(request.form.get('market'), request.form.get('codes'), allowed_markets=services.market_frequencies.keys(), max_codes=int(services.security_overrides.get('WEB_TICKS_MAX_CODES', getattr(services.config, 'WEB_TICKS_MAX_CODES', 200))), max_code_bytes=int(services.security_overrides.get('WEB_TICKS_MAX_CODE_BYTES', getattr(services.config, 'WEB_TICKS_MAX_CODE_BYTES', 128))))
        services.tick_rate_limiter.check(request.remote_addr or 'unknown')
    except TickRateLimitError as exc:
        return ({'error': exc.code, 'message': str(exc)}, exc.http_status)
    except TickRequestError as exc:
        return ({'error': exc.code, 'message': str(exc)}, exc.http_status)
    try:
        ex = services.get_exchange(Market(tick_request.market))
        stock_ticks = services.tick_provider_caller.call(ex.ticks, list(tick_request.codes))
        now_trading = any((ex.now_trading(code) for code in tick_request.codes))
        res_ticks = [{'code': code, 'price': tick.last, 'rate': None if tick.rate is None else round(float(tick.rate), 2)} for code, tick in stock_ticks.items()]
        return {'now_trading': now_trading, 'ticks': res_ticks}
    except (TickProviderBusyError, TickProviderTimeoutError) as exc:
        return ({'error': exc.code, 'message': str(exc), 'now_trading': False, 'ticks': []}, exc.http_status)
    except TickProviderCallError as exc:
        services.logger.exception('tick provider call failed')
        return ({'error': exc.code, 'message': 'tick provider call failed', 'now_trading': False, 'ticks': []}, exc.http_status)
    except Exception:
        services.logger.exception('tick response conversion failed')
        return ({'error': 'tick_provider_failed', 'message': 'tick provider call failed', 'now_trading': False, 'ticks': []}, 502)
