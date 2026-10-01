from __future__ import annotations

import pandas as pd
import pytest

from test_support.isolated_web_app import run_web_app_script

from tradingview_zy.web_payloads import KlinePayloadError, prepare_klines_for_market


def frame(**overrides):
    data = {
        "date": ["2026-05-04 09:30:00", "2026-05-04 09:31:00"],
        "open": [10.0, 11.0],
        "close": [11.0, 10.5],
        "high": [12.0, 12.0],
        "low": [9.0, 10.0],
        "volume": [100, 200],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_prepares_market_timezone_and_binds_request_identity():
    source = frame()
    result = prepare_klines_for_market(
        source, "a", expected_code="SH.600000", expected_frequency="1m"
    )
    assert str(result.iloc[0]["date"].tzinfo) == "Asia/Shanghai"
    assert result["code"].tolist() == ["SH.600000", "SH.600000"]
    assert result["frequency"].tolist() == ["1m", "1m"]
    assert "code" not in source.columns


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda value: value.drop(columns=["volume"]), "missing"),
        (lambda value: value.assign(volume=[-1, 2]), "negative"),
        (lambda value: value.assign(open=[float("nan"), 1]), "finite"),
        (lambda value: value.assign(high=[8, 12]), "OHLC"),
        (lambda value: value.iloc[[1, 0]], "increasing"),
        (lambda value: pd.concat([value.iloc[[0]], value.iloc[[0]]]), "unique"),
    ],
)
def test_rejects_malformed_provider_frames(mutator, match):
    with pytest.raises(KlinePayloadError, match=match):
        prepare_klines_for_market(mutator(frame()), "a")


def test_rejects_provider_identity_mismatch():
    with pytest.raises(KlinePayloadError, match="requested code"):
        prepare_klines_for_market(
            frame(code=["OTHER", "OTHER"]), "a", expected_code="SH.600000"
        )


@pytest.mark.parametrize("first_request", [True, False], ids=["backfill", "follow-up"])
def test_history_localizes_naive_provider_dates_before_windowing(tmp_path, first_request):
    run_web_app_script(
        tmp_path,
        """
        import datetime as dt
        from types import SimpleNamespace
        import pandas as pd

        bars = pd.DataFrame(parameters["bars"])
        bars["date"] = pd.to_datetime(bars["date"])
        exchange = SimpleNamespace(
            klines=lambda code, frequency: bars,
            now_trading=lambda code: True,
        )
        cl_app.get_exchange = lambda market: exchange
        app = cl_app.create_app(app_config)
        expected_times = [
            int(dt.datetime(2026, 5, 4, 1, minute, tzinfo=dt.timezone.utc).timestamp())
            for minute in (30, 31)
        ]
        response = app.test_client().get("/tv/history", query_string={
            "symbol": "a:SH.600000", "resolution": "1",
            "from": expected_times[1], "to": expected_times[1],
            "firstDataRequest": str(parameters["first_request"]).lower(),
        })
        assert response.status_code == 200
        first = parameters["first_request"]
        assert response.get_json() == {
            "s": "ok", "update": not first,
            "t": expected_times if first else expected_times[1:],
            "o": [10.0, 11.0] if first else [11.0],
            "c": [11.0, 10.5] if first else [10.5],
            "h": [12.0, 12.0] if first else [12.0],
            "l": [9.0, 10.0] if first else [10.0],
            "v": [100, 200] if first else [200],
        }
        assert bars["date"].dt.tz is None
        assert "code" not in bars.columns
        """,
        bars=frame().to_dict(orient="list"),
        first_request=first_request,
    )


@pytest.mark.parametrize("fault", ["missing-volume", "wrong-code", "wrong-frequency"])
def test_history_returns_stable_error_for_malformed_provider_payload(tmp_path, fault):
    bars = frame()
    if fault == "missing-volume":
        bars = bars.drop(columns=["volume"])
    elif fault == "wrong-code":
        bars["code"] = "OTHER"
    else:
        bars["frequency"] = "5m"
    run_web_app_script(
        tmp_path,
        """
        from types import SimpleNamespace
        import pandas as pd

        calls = []
        def klines(code, frequency):
            calls.append((code, frequency))
            return pd.DataFrame(parameters["bars"])

        cl_app.get_exchange = lambda market: SimpleNamespace(klines=klines)
        app = cl_app.create_app(app_config)
        response = app.test_client().get("/tv/history", query_string={
            "symbol": "a:SH.600000", "resolution": "1",
            "from": 1777856400, "to": 1777860000, "firstDataRequest": "true",
        })
        assert response.status_code == 200
        assert calls == [("SH.600000", "1m")]
        assert response.get_json() == {"s": "error", "errmsg": "invalid_kline_payload"}
        """,
        bars=bars.to_dict(orient="list"),
    )
