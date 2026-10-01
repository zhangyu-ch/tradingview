from __future__ import annotations

from test_support.isolated_web_app import run_web_app_script

from tradingview_zy.market_metadata import all_market_frequencies, market_frequencies


def test_frequency_union_includes_every_market_and_future_unique_values() -> None:
    markets = market_frequencies()
    markets["ny_futures"] = [*markets["ny_futures"], "10s"]
    union = all_market_frequencies(markets)
    assert "10s" in union
    for frequencies in markets.values():
        assert set(frequencies) <= set(union)
    assert len(union) == len(set(union))


def test_tv_config_returns_resolutions_from_every_configured_market(tmp_path):
    run_web_app_script(
        tmp_path,
        """
        cl_app.market_frequencies = lambda: {
            "a": ["d"], "ny_futures": ["10s", "d"], "future_market": ["3h"],
        }
        app = cl_app.create_app(app_config)
        response = app.test_client().get("/tv/config")
        assert response.status_code == 200
        resolutions = response.get_json()["supported_resolutions"]
        assert set(resolutions) == {"10S", "180", "1D"}
        assert len(resolutions) == 3
        """,
    )
