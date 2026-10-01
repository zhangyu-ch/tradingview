from __future__ import annotations

import importlib
import sys
import types

import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def database(tmp_path, monkeypatch):
    package = importlib.import_module("tradingview_zy")
    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "rv01"
    config.get_data_path = lambda: tmp_path
    with monkeypatch.context() as patch:
        patch.setitem(sys.modules, "tradingview_zy.config", config)
        patch.setattr(package, "config", config, raising=False)
        # Record even an absent module so teardown restores both import surfaces.
        patch.setitem(sys.modules, "tradingview_zy.db", None)
        patch.delitem(sys.modules, "tradingview_zy.db")
        patch.setattr(package, "db", None, raising=False)
        module = importlib.import_module("tradingview_zy.db")
        try:
            yield module
        finally:
            module.db.engine.dispose()


def _rows(module, market):
    with module.db.Session() as session:
        return [
            (row.stock_code, row.stock_name, row.position)
            for row in session.query(module.TableByZixuan)
            .filter(module.TableByZixuan.market == market)
            .filter(module.TableByZixuan.zx_group == "我的关注")
            .order_by(module.TableByZixuan.position, module.TableByZixuan.id)
            .all()
        ]


def test_top_insert_only_moves_same_market(database):
    module = database
    module.db.zx_add_group_stock("a", "我的关注", "A1", "A1")
    module.db.zx_add_group_stock("a", "我的关注", "A2", "A2")
    module.db.zx_add_group_stock("hk", "我的关注", "HK1", "HK1")
    module.db.zx_add_group_stock("hk", "我的关注", "HK2", "HK2")
    hk_before = _rows(module, "hk")

    module.db.zx_add_group_stock("a", "我的关注", "A0", "A0", location="top")

    assert _rows(module, "a") == [("A0", "A0", 0), ("A1", "A1", 1), ("A2", "A2", 2)]
    assert _rows(module, "hk") == hk_before


def test_top_insert_rolls_back_delete_and_shift_when_insert_fails(database):
    module = database
    module.db.zx_add_group_stock("a", "我的关注", "A1", "A1")
    module.db.zx_add_group_stock("a", "我的关注", "KEEP", "Old")
    module.db.zx_add_group_stock("a", "我的关注", "A2", "A2")
    module.db.zx_add_group_stock("hk", "我的关注", "HK", "HK")
    before_a = _rows(module, "a")
    before_hk = _rows(module, "hk")
    with module.db.engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TRIGGER fail_watchlist_insert
            BEFORE INSERT ON cl_zixuan_watchlist
            WHEN NEW.stock_code = 'KEEP'
            BEGIN
              SELECT RAISE(ABORT, 'injected insert failure');
            END;
            """
        )

    with pytest.raises(IntegrityError, match="injected insert failure"):
        module.db.zx_add_group_stock("a", "我的关注", "KEEP", "New", location="top")

    assert _rows(module, "a") == before_a
    assert _rows(module, "hk") == before_hk


def test_readding_existing_stock_moves_it_to_top_without_duplicates(database):
    module = database
    module.db.zx_add_group_stock("a", "我的关注", "A1", "Old")
    module.db.zx_add_group_stock("a", "我的关注", "A2", "A2")
    module.db.zx_add_group_stock("a", "我的关注", "A1", "New", location="top")
    rows = _rows(module, "a")
    assert rows == [("A1", "New", 0), ("A2", "A2", 1)]
