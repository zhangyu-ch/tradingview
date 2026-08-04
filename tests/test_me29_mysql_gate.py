from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MYSQL_TESTS") != "1",
    reason="real MySQL gate runs only in the dedicated CI service job",
)


def test_real_mysql_migrations_and_long_text_round_trip() -> None:
    from sqlalchemy import URL, create_engine, select
    from sqlalchemy.orm import Session

    from tradingview_zy.db import (
        Base,
        TableByAlertTask,
        TableByTVCharts,
        migrate_alert_strategy_storage,
        migrate_tv_storage_schema,
    )

    url = URL.create(
        "mysql+pymysql",
        username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        database=os.environ["MYSQL_DATABASE"],
        query={"charset": "utf8mb4"},
    )
    engine = create_engine(url, pool_pre_ping=True)
    try:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        migrate_alert_strategy_storage(engine)
        migrate_tv_storage_schema(engine)

        strategy = '{"payload":"' + ("策略参数" * 1500) + '"}'
        chart = "图表布局" * 18000
        now = int(time.time())
        with Session(engine) as session:
            session.add(
                TableByAlertTask(
                    market="a",
                    task_name="mysql-long-content",
                    strategy_config_text=strategy,
                    strategy_memo_text="真实 MySQL TEXT 往返",
                )
            )
            session.add(
                TableByTVCharts(
                    client_id="ci",
                    user_id="ci",
                    chart_type="chart",
                    symbol="SH.000001",
                    resolution="d",
                    content=chart,
                    timestamp=now,
                    name="mysql-mediumtext",
                )
            )
            session.commit()

        with Session(engine) as session:
            stored_strategy = session.scalar(
                select(TableByAlertTask).where(
                    TableByAlertTask.task_name == "mysql-long-content"
                )
            )
            stored_chart = session.scalar(
                select(TableByTVCharts).where(
                    TableByTVCharts.name == "mysql-mediumtext"
                )
            )
            assert stored_strategy is not None
            assert stored_strategy.strategy_config_text == strategy
            assert stored_chart is not None
            assert stored_chart.content == chart
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
