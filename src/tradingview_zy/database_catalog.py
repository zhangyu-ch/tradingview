"""Read-only discovery helpers for database-backed market data."""
from __future__ import annotations

from sqlalchemy import MetaData, Table, inspect, select
from sqlalchemy.engine import Engine


def list_market_kline_codes(engine: Engine, market: str) -> list[str]:
    """Return sorted, distinct instrument codes stored for ``market``.

    K-line tables are partitioned by market and code/group.  The table names are
    discovered through SQLAlchemy's inspector, while values are selected through
    reflected ``Table`` objects so identifiers are quoted by the active dialect.
    Tables that merely share the prefix but do not expose a ``code`` column are
    ignored rather than treated as market-data tables.
    """
    market = str(market).strip().lower()
    if not market:
        raise ValueError("market must not be empty")

    prefix = f"{market}_klines_"
    inspector = inspect(engine)
    table_names = sorted(
        name for name in inspector.get_table_names() if name.startswith(prefix)
    )
    if not table_names:
        return []

    codes: set[str] = set()
    with engine.connect() as connection:
        for table_name in table_names:
            column_names = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            if "code" not in column_names:
                continue
            table = Table(table_name, MetaData(), autoload_with=engine)
            rows = connection.execute(select(table.c.code).distinct()).scalars()
            for value in rows:
                if value is None:
                    continue
                code = str(value).strip()
                if code:
                    codes.add(code)

    return sorted(codes)
