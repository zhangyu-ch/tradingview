import pandas as pd
import pytest

from tradingview_zy.domain import DataContractError
from tradingview_zy.kline_schema import normalize_kline_frame, validate_kline_frame


def frame():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02 09:30", "2026-01-02 09:31"]).tz_localize("Asia/Shanghai"),
            "code": ["SH.600000", "SH.600000"],
            "open": [10.0, 10.2],
            "high": [10.5, 10.4],
            "low": [9.8, 10.0],
            "close": [10.2, 10.3],
            "volume": [100, 200],
        }
    )


def test_valid_frame_is_copied_and_normalized_without_mutating_input():
    source = frame()
    result = normalize_kline_frame(source, market="a", code="SH.600000", frequency="1m")
    assert result is not source
    assert "frequency" not in source.columns
    assert result["frequency"].tolist() == ["1m", "1m"]
    assert validate_kline_frame(result, market="a", code="SH.600000").rows == 2


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda df: df.drop(columns=["close"]), "缺少字段"),
        (lambda df: df.assign(volume=[-1, 2]), "volume 不得为负"),
        (lambda df: df.assign(high=[9.0, 10.4]), "OHLC"),
        (lambda df: df.iloc[::-1].reset_index(drop=True), "严格升序"),
    ],
)
def test_invalid_frames_fail_closed(mutation, message):
    with pytest.raises(DataContractError, match=message):
        normalize_kline_frame(mutation(frame()), market="a", code="SH.600000")


def test_duplicate_and_naive_dates_are_rejected():
    duplicated = frame()
    duplicated.loc[1, "date"] = duplicated.loc[0, "date"]
    with pytest.raises(DataContractError, match="重复"):
        normalize_kline_frame(duplicated)
    naive = frame()
    naive["date"] = naive["date"].dt.tz_localize(None)
    with pytest.raises(DataContractError, match="带时区"):
        normalize_kline_frame(naive)


def test_tradingview_history_strict_path_rejects_wrong_code():
    from tradingview_zy.web_payloads import klines_to_tv_history

    with pytest.raises(DataContractError, match="code"):
        klines_to_tv_history(
            frame(), update=False, market="a", code="SH.000001", frequency="1m"
        )


def test_tradingview_history_route_uses_strict_market_contract():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "web"
        / "tradingview_zy_chart"
        / "cl_app"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    call = source[source.index("return klines_to_tv_history(") :]
    call = call[: call.index(")", call.index("frequency=frequency")) + 1]
    assert "market=market" in call
    assert "code=code" in call
    assert "frequency=frequency" in call
