from __future__ import annotations

import ast
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reliability = _load(
    ROOT / "src/tradingview_zy/exchange/tdx_reliability.py",
    "lo02_tdx_reliability",
)
us_history = _load(
    ROOT / "src/tradingview_zy/exchange/us_history.py",
    "lo02_us_history",
)
sync = _load(ROOT / "src/tradingview_zy/sync_batch.py", "lo02_sync_batch")

TDX_ADAPTERS = {
    "exchange_tdx_futures.py": {"category": 3, "market_ids": {23, 28, 29, 30, 42, 47, 66}},
    "exchange_tdx_fx.py": {"category": 4, "market_ids": None},
    "exchange_tdx_hk.py": {"category": 2, "market_ids": None},
    "exchange_tdx_ny_futures.py": {"category": 3, "market_ids": {16, 17}},
    "exchange_tdx_us.py": {"category": None, "market_ids": None},
}
WRAPPERS = [
    ROOT / f"script/crontab/reboot_sync_{market}_klines.py"
    for market in ["a", "us", "currency", "currency_spot", "hk", "futures"]
]


class FakeConnectionError(RuntimeError):
    pass


class FakeCache:
    def __init__(self, cached=None) -> None:
        self.cached = cached
        self.writes: list[tuple[str, dict[str, object], int]] = []

    def cache_get(self, key: str):
        assert key == "tdxex_connect_ip"
        return self.cached

    def cache_set(self, key: str, value: dict[str, object], expire: int = 0):
        self.cached = dict(value)
        self.writes.append((key, dict(value), expire))
        return True


class FakeSelector:
    def __init__(self, *nodes: dict[str, object]) -> None:
        self.nodes = list(nodes)
        self.calls = 0

    def select_best_ip(self, node_type: str):
        assert node_type == "future"
        self.calls += 1
        return self.nodes.pop(0)

    @staticmethod
    def cache_expiry_epoch() -> int:
        return 9_999


class FakeClient:
    def __init__(self, action, connect_calls: list[tuple[str, int, float]]) -> None:
        self.action = action
        self.connect_calls = connect_calls

    def connect(self, ip: str, port: int, *, time_out: float):
        self.connect_calls.append((ip, port, time_out))
        if isinstance(self.action, BaseException):
            raise self.action
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_markets(self):
        return self.action


class Lifecycle(reliability.TdxExHqLifecycleMixin):
    pass


def test_shared_exhq_lifecycle_replaces_invalid_cache_and_filters_markets() -> None:
    cache = FakeCache({"ip": "", "port": 0})
    selector = FakeSelector({"ip": "node-1", "port": "7727"})
    kwargs_seen: list[dict[str, object]] = []
    connect_calls: list[tuple[str, int, float]] = []
    markets = [
        {"short_name": "QS", "market": 23, "category": 3, "name": "SHFE"},
        {"short_name": "CO", "market": 16, "category": 3, "name": "COMEX"},
        {"short_name": "FX", "market": 10, "category": 4, "name": "FX"},
    ]

    def factory(**kwargs):
        kwargs_seen.append(kwargs)
        return FakeClient(markets, connect_calls)

    lifecycle = Lifecycle()
    lifecycle._initialize_tdx_exhq(
        cache_backend=cache,
        selector=selector,
        client_factory=factory,
        connection_errors=(FakeConnectionError,),
        description="test futures",
        market_category=3,
        market_ids={23},
        client_kwargs={"multithread": True},
        retry_options={"base_delay_seconds": 0, "max_delay_seconds": 0},
    )

    assert lifecycle.connect_info == {"ip": "node-1", "port": 7727}
    assert lifecycle.market_maps == {
        "QS": {"market": 23, "category": 3, "name": "SHFE"}
    }
    assert cache.writes == [
        ("tdxex_connect_ip", {"ip": "node-1", "port": 7727}, 9_999)
    ]
    assert kwargs_seen == [
        {"raise_exception": True, "auto_retry": True, "multithread": True}
    ]
    assert connect_calls[0][0:2] == ("node-1", 7727)
    assert 0.1 <= connect_calls[0][2] <= 4.0


def test_shared_exhq_lifecycle_recovers_to_a_new_node_with_bounded_retry() -> None:
    cache = FakeCache({"ip": "old-node", "port": 7727})
    selector = FakeSelector({"ip": "new-node", "port": 7727})
    actions = [
        FakeConnectionError("first node failed"),
        [{"short_name": "KH", "market": 31, "category": 2, "name": "HK"}],
    ]
    connect_calls: list[tuple[str, int, float]] = []

    def factory(**_kwargs):
        return FakeClient(actions.pop(0), connect_calls)

    lifecycle = Lifecycle()
    lifecycle._initialize_tdx_exhq(
        cache_backend=cache,
        selector=selector,
        client_factory=factory,
        connection_errors=(FakeConnectionError,),
        description="test hk",
        market_category=2,
        retry_options={
            "base_delay_seconds": 0,
            "max_delay_seconds": 0,
            "deadline_seconds": 1,
        },
    )

    assert [call[0] for call in connect_calls] == ["old-node", "new-node"]
    assert selector.calls == 1
    assert lifecycle.market_maps["KH"]["market"] == 31


def test_shared_exhq_lifecycle_fails_closed_on_empty_supported_map() -> None:
    lifecycle = Lifecycle()
    cache = FakeCache({"ip": "node", "port": 7727})

    with pytest.raises(reliability.ProviderUnavailableError, match="no supported markets"):
        lifecycle._initialize_tdx_exhq(
            cache_backend=cache,
            selector=FakeSelector(),
            client_factory=lambda **_kwargs: FakeClient(
                [{"short_name": "FX", "market": 10, "category": 4, "name": "FX"}],
                [],
            ),
            connection_errors=(FakeConnectionError,),
            description="test futures",
            market_category=3,
            market_ids={23},
            retry_options={"base_delay_seconds": 0, "max_delay_seconds": 0},
        )


def test_five_exhq_adapters_use_only_the_shared_lifecycle() -> None:
    for filename in TDX_ADAPTERS:
        path = ROOT / "src/tradingview_zy/exchange" / filename
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        assert "TdxExHqLifecycleMixin" in {ast.unparse(base) for base in class_node.bases}
        assert not any(
            isinstance(node, ast.FunctionDef) and node.name == "reset_tdx_ip"
            for node in class_node.body
        )
        init = next(
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_initialize_tdx_exhq"
            for node in ast.walk(init)
        )
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "TdxExHq_API"
            for node in ast.walk(tree)
        )
        assert "self._new_tdx_client()" in source


def test_us_history_window_is_timezone_aware_and_independently_parses_bounds() -> None:
    winter_start, winter_end = us_history.parse_us_history_window(
        "d",
        start_date="2026-01-05 09:30:00",
        end_date="2026-01-06",
    )
    summer_start, summer_end = us_history.parse_us_history_window(
        "60m",
        start_date=datetime(2026, 7, 6, 9, 30),
        end_date=datetime(2026, 7, 6, 16, 0),
    )
    assert winter_start.utcoffset().total_seconds() == -5 * 3600
    assert winter_end.utcoffset().total_seconds() == -5 * 3600
    assert summer_start.utcoffset().total_seconds() == -4 * 3600
    assert summer_end.utcoffset().total_seconds() == -4 * 3600
    with pytest.raises(us_history.UsHistoryPayloadError, match="must not be after"):
        us_history.parse_us_history_window(
            "d", start_date="2026-02-02", end_date="2026-02-01"
        )


def test_us_history_default_window_applies_provider_day_offset() -> None:
    start, end = us_history.parse_us_history_window(
        "1m",
        now=datetime.fromisoformat("2026-01-05T12:00:00-05:00"),
        end_day_offset=-1,
    )
    assert end.isoformat() == "2026-01-04T00:00:00-05:00"
    assert (end - start).days == 15


def test_us_history_frame_sorts_deduplicates_and_uses_market_time() -> None:
    first = pd.Timestamp("2026-07-06T13:30:00Z").value // 1_000_000
    second = pd.Timestamp("2026-07-06T13:31:00Z").value // 1_000_000
    records = [
        {"timestamp": second, "open": 2, "close": 2, "high": 2, "low": 2, "volume": 20},
        {"timestamp": first, "open": 1, "close": 1, "high": 1, "low": 1, "volume": 10},
        {"timestamp": first, "open": 1.5, "close": 1.5, "high": 1.5, "low": 1.5, "volume": 15},
    ]
    frame = us_history.build_us_history_frame(
        records, code="aapl", frequency="1m", timestamp_unit="ms"
    )
    assert frame["code"].tolist() == ["AAPL", "AAPL"]
    assert frame["open"].tolist() == [1.5, 2.0]
    assert frame["date"].dt.tz.key == "America/New_York"
    assert frame["date"].dt.strftime("%H:%M").tolist() == ["09:30", "09:31"]


def test_us_daily_history_is_anchored_at_market_close() -> None:
    frame = us_history.build_us_history_frame(
        [
            {
                "timestamp": "2026-01-05T12:00:00Z",
                "open": 1,
                "close": 2,
                "high": 2,
                "low": 1,
                "volume": 3,
            }
        ],
        code="AAPL",
        frequency="d",
    )
    assert frame.iloc[0]["date"].hour == 16
    assert frame.iloc[0]["date"].utcoffset().total_seconds() == -5 * 3600


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("volume", -1, "negative volume"),
        ("open", float("inf"), "non-finite"),
        ("high", 0, "inconsistent OHLC"),
    ],
)
def test_us_history_rejects_invalid_ohlcv(field: str, value: float, message: str) -> None:
    row = {
        "timestamp": "2026-01-05T14:30:00Z",
        "open": 1,
        "close": 1,
        "high": 1,
        "low": 1,
        "volume": 1,
    }
    row[field] = value
    with pytest.raises(us_history.UsHistoryPayloadError, match=message):
        us_history.build_us_history_frame([row], code="AAPL", frequency="1m")


def test_alpaca_and_polygon_use_shared_us_history_boundary() -> None:
    for filename in ["exchange_alpaca.py", "exchange_polygon.py"]:
        source = (
            ROOT / "src/tradingview_zy/exchange" / filename
        ).read_text(encoding="utf-8")
        assert "parse_us_history_window" in source
        assert "build_us_history_frame" in source
        assert "len(end_date)" not in source


def test_universe_filters_are_stable_bounded_and_fail_closed() -> None:
    universe = {
        "type": "provider_all_stocks",
        "include_contains": ["KQ.m@"],
        "exclude_contains": ["bad"],
        "max_codes": 2,
    }
    assert sync._filter_universe_codes(
        ["KQ.m@SHFE.rb", "other", "KQ.m@bad", "KQ.m@DCE.i", "KQ.m@CZCE.SR"],
        universe,
    ) == ["KQ.m@SHFE.rb", "KQ.m@DCE.i"]
    with pytest.raises(sync.SyncBatchError, match="empty after filters"):
        sync._filter_universe_codes(["other"], universe)


def test_explicit_safe_empty_universe_does_not_import_providers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "schema_version": 1,
        "market": "hk",
        "mode": "incremental",
        "source": {"module": "must.not.import", "class": "Source"},
        "destination": {"module": "must.not.import", "class": "Destination"},
        "universe": {"type": "list", "codes": [], "allow_empty": True},
        "frequencies": {"d": {"start_date": "2020-01-01"}},
    }
    config_path = tmp_path / "config.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(
        sync,
        "_instantiate",
        lambda _spec: (_ for _ in ()).throw(AssertionError("provider imported")),
    )

    result = sync.run_configured_sync(
        config_path=config_path,
        checkpoint_path=checkpoint_path,
        batch_deadline_seconds=2,
        per_call_timeout=0.2,
    )
    state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert result.status == "completed"
    assert result.completed == result.failed == result.pending == 0
    assert state["items"] == {}


def test_six_sync_scripts_are_thin_and_configs_remove_stale_inline_universes() -> None:
    for wrapper in WRAPPERS:
        source = wrapper.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(wrapper))
        assert len(source.splitlines()) < 30
        assert "while True" not in source
        assert not any(
            isinstance(node, (ast.For, ast.While, ast.With, ast.Try))
            for node in tree.body
        )
        assert "tradingview_zy.exchange." not in source

    config_root = ROOT / "script/crontab/sync_configs"
    spot = json.loads((config_root / "currency_spot_klines.json").read_text())
    hk = json.loads((config_root / "hk_klines.json").read_text())
    futures = json.loads((config_root / "futures_klines.json").read_text())
    assert spot["universe"]["codes"] == ["BTC/USDT"]
    assert hk["universe"] == {"type": "list", "codes": [], "allow_empty": True}
    assert futures["universe"]["include_contains"] == ["KQ.m@"]
    assert futures["universe"]["max_codes"] == 200
    assert "2022" not in json.dumps(futures)
