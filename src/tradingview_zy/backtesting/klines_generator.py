from __future__ import annotations

import pandas as pd


class KlinesGenerator:
    """Incrementally aggregate minute bars without mutating caller data.

    ``bob`` labels a bar with the beginning of its half-open interval
    ``[start, end)``. ``eob`` labels a bar with the end of its interval
    ``(start, end]``. Recomputing from the retained source bars makes the
    incremental path deterministic and identical to a one-shot aggregation.
    """

    _MAX_SOURCE_ROWS = 40_000
    _MAX_OUTPUT_ROWS = 20_000

    def __init__(self, minute: int, dt_align_type: str = "eob"):
        if not isinstance(minute, int) or isinstance(minute, bool) or minute <= 0:
            raise ValueError("minute 必须是正整数")
        if dt_align_type not in {"bob", "eob"}:
            raise ValueError("dt_align_type 只支持 bob 或 eob")

        self.minute = minute
        self.dt_align_type = dt_align_type
        self.to_klines: pd.DataFrame | None = None
        self._source_klines: pd.DataFrame | None = None

    def _merge_source(self, from_klines: pd.DataFrame) -> pd.DataFrame:
        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required.difference(from_klines.columns)
        if missing:
            raise ValueError(f"源 K 线缺少字段：{sorted(missing)}")

        incoming = from_klines.copy(deep=True)
        incoming["date"] = pd.to_datetime(incoming["date"], errors="raise")

        if self._source_klines is None:
            merged = incoming
        else:
            merged = pd.concat([self._source_klines, incoming], ignore_index=True)

        duplicate_key = ["date"]
        if "code" in merged.columns:
            duplicate_key.insert(0, "code")
        merged = (
            merged.drop_duplicates(duplicate_key, keep="last")
            .sort_values(duplicate_key)
            .reset_index(drop=True)
        )
        if len(merged) > self._MAX_SOURCE_ROWS:
            merged = merged.iloc[-self._MAX_SOURCE_ROWS :].reset_index(drop=True)
        self._source_klines = merged
        return merged

    def _aggregate(self, source: pd.DataFrame) -> pd.DataFrame:
        indexed = source.copy(deep=True).set_index("date", drop=False)
        period = f"{self.minute}min"
        if self.dt_align_type == "bob":
            label, closed = "left", "left"
        else:
            label, closed = "right", "right"

        aggregations: dict[str, str] = {
            "date": "first",
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        for column in ("code", "position"):
            if column in indexed.columns:
                aggregations[column] = "last" if column == "position" else "first"

        result = indexed.resample(
            period,
            label=label,
            closed=closed,
            origin="start_day",
        ).agg(aggregations)
        result = result.dropna(subset=["open", "high", "low", "close"])
        result["date"] = result.index
        if "frequency" in source.columns:
            result["frequency"] = f"{self.minute}m"

        result = result.reset_index(drop=True)
        preferred = [
            column
            for column in (
                "date",
                "frequency",
                "code",
                "open",
                "close",
                "high",
                "low",
                "volume",
                "position",
            )
            if column in result.columns
        ]
        remaining = [column for column in result.columns if column not in preferred]
        result = result[preferred + remaining]
        if len(result) > self._MAX_OUTPUT_ROWS:
            result = result.iloc[-self._MAX_OUTPUT_ROWS :].reset_index(drop=True)
        return result

    def update_klines(self, from_klines: pd.DataFrame) -> pd.DataFrame | None:
        if from_klines is None or len(from_klines) == 0:
            return None if self.to_klines is None else self.to_klines.copy(deep=True)

        source = self._merge_source(from_klines)
        self.to_klines = self._aggregate(source)
        return self.to_klines.copy(deep=True)


if __name__ == "__main__":
    from tradingview_zy.exchange.exchange_db import ExchangeDB

    ex = ExchangeDB("futures")
    klines = ex.klines("SHFE.RB", "1m")
    print(KlinesGenerator(30, "eob").update_klines(klines).tail())
