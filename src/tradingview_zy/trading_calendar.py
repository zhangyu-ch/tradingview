from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from types import MappingProxyType
from typing import Mapping
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Session:
    """A half-open local market session: ``start <= t < end``."""

    start: time
    end: time

    def contains(self, value: time) -> bool:
        return self.start <= value < self.end


@dataclass(frozen=True)
class CalendarDefinition:
    market: str
    version: str
    timezone_name: str
    covered_years: tuple[int, ...]
    regular_sessions: tuple[Session, ...]
    closed_dates: frozenset[date]
    special_sessions: Mapping[date, tuple[Session, ...]]
    sources: tuple[str, ...]


@dataclass(frozen=True)
class FuturesSessionProfile:
    """Versioned instrument session profile used by futures calendars."""

    name: str
    version: str
    timezone_name: str
    covered_years: tuple[int, ...]
    day_sessions: tuple[Session, ...]
    night_end: time | None
    sources: tuple[str, ...]


_MORNING_A = Session(time(9, 30), time(11, 30))
_AFTERNOON_A = Session(time(13, 0), time(15, 0))
_MORNING_HK = Session(time(9, 30), time(12, 0))
_AFTERNOON_HK = Session(time(13, 0), time(16, 0))
_US_CORE = Session(time(9, 30), time(16, 0))
_US_EARLY = Session(time(9, 30), time(13, 0))

_CN_COMMODITY_DAY = (
    Session(time(9, 0), time(10, 15)),
    Session(time(10, 30), time(11, 30)),
    Session(time(13, 30), time(15, 0)),
)
_CFFEX_INDEX_DAY = (
    Session(time(9, 30), time(11, 30)),
    Session(time(13, 0), time(15, 0)),
)
_CFFEX_TREASURY_DAY = (
    Session(time(9, 30), time(11, 30)),
    Session(time(13, 0), time(15, 15)),
)


def _dates(start: date, end: date) -> frozenset[date]:
    result: set[date] = set()
    current = start
    while current <= end:
        result.add(current)
        current = date.fromordinal(current.toordinal() + 1)
    return frozenset(result)


_SSE_2026_CLOSED = frozenset().union(
    _dates(date(2026, 1, 1), date(2026, 1, 3)),
    _dates(date(2026, 2, 15), date(2026, 2, 23)),
    _dates(date(2026, 4, 4), date(2026, 4, 6)),
    _dates(date(2026, 5, 1), date(2026, 5, 5)),
    _dates(date(2026, 6, 19), date(2026, 6, 21)),
    _dates(date(2026, 9, 25), date(2026, 9, 27)),
    _dates(date(2026, 10, 1), date(2026, 10, 7)),
)

_HK_2026_CLOSED = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 2, 17),
        date(2026, 2, 18),
        date(2026, 2, 19),
        date(2026, 4, 3),
        date(2026, 4, 6),
        date(2026, 4, 7),
        date(2026, 5, 1),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 1),
        date(2026, 10, 1),
        date(2026, 10, 19),
        date(2026, 12, 25),
    }
)
_HK_2026_HALF_DAYS = MappingProxyType(
    {
        date(2026, 2, 16): (_MORNING_HK,),
        date(2026, 12, 24): (_MORNING_HK,),
        date(2026, 12, 31): (_MORNING_HK,),
    }
)

_NYSE_2026_CLOSED = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
)
_NYSE_2026_EARLY_CLOSES = MappingProxyType(
    {
        date(2026, 11, 27): (_US_EARLY,),
        date(2026, 12, 24): (_US_EARLY,),
    }
)

_CALENDARS: Mapping[str, CalendarDefinition] = MappingProxyType(
    {
        "a": CalendarDefinition(
            market="a",
            version="SSE-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            regular_sessions=(_MORNING_A, _AFTERNOON_A),
            closed_dates=_SSE_2026_CLOSED,
            special_sessions=MappingProxyType({}),
            sources=(
                "Shanghai Stock Exchange 2026 holiday notice",
                "Shanghai Stock Exchange trading schedule",
            ),
        ),
        "hk": CalendarDefinition(
            market="hk",
            version="HKEX-2026-v1",
            timezone_name="Asia/Hong_Kong",
            covered_years=(2026,),
            regular_sessions=(_MORNING_HK, _AFTERNOON_HK),
            closed_dates=_HK_2026_CLOSED,
            special_sessions=_HK_2026_HALF_DAYS,
            sources=(
                "Hong Kong Government 2026 general holidays",
                "HKEX securities market trading hours",
            ),
        ),
        "us": CalendarDefinition(
            market="us",
            version="NYSE-2026-v1",
            timezone_name="America/New_York",
            covered_years=(2026,),
            regular_sessions=(_US_CORE,),
            closed_dates=_NYSE_2026_CLOSED,
            special_sessions=_NYSE_2026_EARLY_CLOSES,
            sources=("NYSE 2026 holidays and core trading hours",),
        ),
    }
)

_CN_FUTURES_PROFILES: Mapping[str, FuturesSessionProfile] = MappingProxyType(
    {
        "commodity_day": FuturesSessionProfile(
            name="commodity_day",
            version="CN-FUTURES-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            day_sessions=_CN_COMMODITY_DAY,
            night_end=None,
            sources=("Chinese futures exchange product trading hours",),
        ),
        "night_2300": FuturesSessionProfile(
            name="night_2300",
            version="CN-FUTURES-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            day_sessions=_CN_COMMODITY_DAY,
            night_end=time(23, 0),
            sources=("Chinese futures exchange product trading hours",),
        ),
        "night_0100": FuturesSessionProfile(
            name="night_0100",
            version="CN-FUTURES-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            day_sessions=_CN_COMMODITY_DAY,
            night_end=time(1, 0),
            sources=("Shanghai futures product trading hours",),
        ),
        "night_0230": FuturesSessionProfile(
            name="night_0230",
            version="CN-FUTURES-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            day_sessions=_CN_COMMODITY_DAY,
            night_end=time(2, 30),
            sources=("Precious-metal and crude-oil futures trading hours",),
        ),
        "cffex_index": FuturesSessionProfile(
            name="cffex_index",
            version="CFFEX-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            day_sessions=_CFFEX_INDEX_DAY,
            night_end=None,
            sources=("CFFEX equity-index futures trading hours",),
        ),
        "cffex_treasury": FuturesSessionProfile(
            name="cffex_treasury",
            version="CFFEX-2026-v1",
            timezone_name="Asia/Shanghai",
            covered_years=(2026,),
            day_sessions=_CFFEX_TREASURY_DAY,
            night_end=None,
            sources=("CFFEX treasury futures trading hours",),
        ),
    }
)

_CN_PRODUCTS_BY_PROFILE: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        # This explicit list intentionally covers the repository's configured
        # products and common contracts. New products fail closed until added
        # from an exchange-published schedule.
        "night_2300": frozenset(
            {
                "A", "B", "BU", "C", "CF", "CS", "CY", "EB", "EG",
                "FG", "FU", "HC", "I", "J", "JM", "L", "M", "MA",
                "OI", "P", "PF", "PG", "PP", "PX", "RB", "RM", "RR",
                "RU", "SA", "SF", "SH", "SM", "SP", "SR", "TA", "UR",
                "V", "Y",
            }
        ),
        "night_0100": frozenset(
            {"AL", "AO", "BC", "CU", "NI", "PB", "SN", "SS", "ZN"}
        ),
        "night_0230": frozenset({"AG", "AU", "SC"}),
        "commodity_day": frozenset(
            {
                "AP", "BB", "CJ", "FB", "JD", "JR", "LC", "LH", "LR",
                "PK", "PM", "PS", "RI", "RS", "SI", "WH",
            }
        ),
        "cffex_index": frozenset({"IC", "IF", "IH", "IM"}),
        "cffex_treasury": frozenset({"T", "TF", "TL", "TS"}),
    }
)

_CME_SUPPORTED_ROOTS = frozenset(
    {
        "6A", "6B", "6C", "6E", "6J", "6S", "CL", "DX", "ES", "GC",
        "HE", "HG", "HO", "KE", "LE", "M2K", "MCL", "MES", "MGC",
        "MNQ", "MYM", "NG", "NQ", "PA", "PL", "RB", "RTY", "SI",
        "SIL", "UB", "YM", "ZB", "ZC", "ZF", "ZN", "ZS", "ZT", "ZW",
    }
)
# CME publishes product-specific holiday hours. Until those tables are encoded
# per product, these observed 2026 holiday dates are treated conservatively as
# closed rather than guessed open.
_CME_2026_CONSERVATIVE_CLOSED = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
)

_PRODUCT_ROOT_RE = re.compile(r"^(?:[0-9][A-Z]|[A-Z]+)")
_CONTINUOUS_SUFFIX_RE = re.compile(r"L[0-9]+$")


def _normalise_instant(at: datetime | None) -> datetime:
    if at is None:
        return datetime.now(timezone.utc)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("market calendar requires a timezone-aware datetime")
    return at


def _coerce_legacy_arguments(
    code: str | datetime | None, at: datetime | None
) -> tuple[str | None, datetime | None]:
    """Keep ME-12's historic ``is_market_open(market, at)`` call compatible."""

    if isinstance(code, datetime):
        if at is not None:
            raise TypeError("market calendar instant was supplied twice")
        return None, code
    if code is None:
        return None, at
    return str(code).strip() or None, at


def _extract_product_root(code: str | None) -> str | None:
    if code is None:
        return None
    token = str(code).strip().upper()
    if not token:
        return None
    if "@" in token:
        token = token.rsplit("@", 1)[-1]
    if "." in token:
        token = token.rsplit(".", 1)[-1]
    token = _CONTINUOUS_SUFFIX_RE.sub("", token)
    match = _PRODUCT_ROOT_RE.match(token)
    return match.group(0) if match else None


def _is_cash_market_open(definition: CalendarDefinition, at: datetime) -> bool:
    local = at.astimezone(ZoneInfo(definition.timezone_name))
    local_date = local.date()
    if local_date.year not in definition.covered_years:
        return False
    if local.weekday() >= 5 or local_date in definition.closed_dates:
        return False

    sessions = definition.special_sessions.get(local_date, definition.regular_sessions)
    local_time = local.time().replace(tzinfo=None)
    return any(session.contains(local_time) for session in sessions)


def _is_fx_open(at: datetime) -> bool:
    """Generic spot-FX 24x5 boundary in New York local time."""

    local = at.astimezone(ZoneInfo("America/New_York"))
    weekday = local.weekday()
    local_time = local.time().replace(tzinfo=None)
    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday
        return local_time >= time(17, 0)
    if weekday == 4:  # Friday
        return local_time < time(17, 0)
    return True


def _cn_profile_for_root(root: str | None) -> FuturesSessionProfile | None:
    if root is None:
        return None
    matches = [
        profile_name
        for profile_name, products in _CN_PRODUCTS_BY_PROFILE.items()
        if root in products
    ]
    if len(matches) != 1:
        return None
    return _CN_FUTURES_PROFILES[matches[0]]


def _is_cn_trading_day(value: date) -> bool:
    return (
        value.year == 2026
        and value.weekday() < 5
        and value not in _SSE_2026_CLOSED
    )


def _next_cn_trading_day(value: date) -> date | None:
    for offset in range(1, 16):
        candidate = value + timedelta(days=offset)
        if _is_cn_trading_day(candidate):
            return candidate
    return None


def _cn_night_started_on(start_date: date) -> bool:
    if not _is_cn_trading_day(start_date):
        return False
    next_trading_day = _next_cn_trading_day(start_date)
    if next_trading_day is None:
        return False
    # Friday -> Monday is a valid continuation. A longer gap indicates a
    # statutory-holiday eve and is conservatively closed.
    return (next_trading_day - start_date).days <= 3


def _is_cn_futures_open(code: str | None, at: datetime) -> bool:
    root = _extract_product_root(code)
    profile = _cn_profile_for_root(root)
    if profile is None:
        return False

    local = at.astimezone(ZoneInfo(profile.timezone_name))
    if local.year not in profile.covered_years:
        return False
    local_time = local.time().replace(tzinfo=None)
    local_date = local.date()

    if _is_cn_trading_day(local_date) and any(
        session.contains(local_time) for session in profile.day_sessions
    ):
        return True

    if profile.night_end is None:
        return False
    night_start = time(21, 0)
    if local_time >= night_start:
        # A 23:00 profile closes on the same civil date; 01:00/02:30
        # profiles cross midnight and therefore have no same-date upper bound.
        if profile.night_end > night_start and local_time >= profile.night_end:
            return False
        start_date = local_date
    elif profile.night_end < night_start and local_time < profile.night_end:
        start_date = local_date - timedelta(days=1)
    else:
        return False
    return _cn_night_started_on(start_date)


def _is_cme_futures_open(code: str | None, at: datetime) -> bool:
    root = _extract_product_root(code)
    if root not in _CME_SUPPORTED_ROOTS:
        return False

    local = at.astimezone(ZoneInfo("America/New_York"))
    if local.year != 2026:
        return False
    local_date = local.date()
    local_time = local.time().replace(tzinfo=None)

    if local_date in _CME_2026_CONSERVATIVE_CLOSED:
        return False
    # An evening session belongs to the next trade date. Do not open an
    # unmodelled holiday session merely because the preceding date is open.
    if (
        local_time >= time(18, 0)
        and local_date + timedelta(days=1) in _CME_2026_CONSERVATIVE_CLOSED
    ):
        return False

    weekday = local.weekday()
    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday open
        return local_time >= time(18, 0)
    if weekday == 4:  # Friday close
        return local_time < time(17, 0)
    # Monday through Thursday have a daily 17:00-18:00 ET maintenance break.
    return not (time(17, 0) <= local_time < time(18, 0))


def is_market_open(
    market: str,
    code: str | datetime | None = None,
    at: datetime | None = None,
) -> bool:
    """Return a strict, instrument-aware market-open bool.

    ``code`` is mandatory for futures because session profiles differ by
    product. Cash calendars and futures calendars fail closed outside their
    explicitly versioned 2026 coverage. Unknown instruments also fail closed.
    The legacy two-positional-argument form ``is_market_open(market, at)`` is
    retained for the ME-12 cash/FX contract.
    """

    instrument, instant_arg = _coerce_legacy_arguments(code, at)
    instant = _normalise_instant(instant_arg)
    market_key = str(market).strip().lower()

    if market_key == "fx":
        return _is_fx_open(instant)
    if market_key in {"currency", "currency_spot"}:
        return True
    if market_key == "futures":
        return _is_cn_futures_open(instrument, instant)
    if market_key == "ny_futures":
        return _is_cme_futures_open(instrument, instant)

    definition = _CALENDARS.get(market_key)
    if definition is None:
        raise ValueError(f"unsupported market calendar: {market!r}")
    return _is_cash_market_open(definition, instant)


def market_calendar_metadata(
    market: str, code: str | None = None
) -> dict[str, object]:
    market_key = str(market).strip().lower()
    if market_key == "fx":
        return {
            "market": "fx",
            "version": "FX-24x5-v1",
            "timezone": "America/New_York",
            "covered_years": (),
            "sources": ("generic spot-FX weekly boundary",),
        }
    if market_key in {"currency", "currency_spot"}:
        return {
            "market": market_key,
            "version": "CRYPTO-24x7-v1",
            "timezone": "UTC",
            "covered_years": (),
            "sources": ("continuous digital-asset venue schedule",),
        }
    if market_key == "futures":
        root = _extract_product_root(code)
        profile = _cn_profile_for_root(root)
        if profile is None:
            raise ValueError(f"unsupported futures instrument: {code!r}")
        return {
            "market": market_key,
            "instrument_root": root,
            "profile": profile.name,
            "version": profile.version,
            "timezone": profile.timezone_name,
            "covered_years": profile.covered_years,
            "sources": profile.sources,
        }
    if market_key == "ny_futures":
        root = _extract_product_root(code)
        if root not in _CME_SUPPORTED_ROOTS:
            raise ValueError(f"unsupported NY futures instrument: {code!r}")
        return {
            "market": market_key,
            "instrument_root": root,
            "profile": "globex_1800_1700",
            "version": "CME-GLOBEX-2026-v1",
            "timezone": "America/New_York",
            "covered_years": (2026,),
            "sources": ("CME Group 2026 Globex trading and holiday schedules",),
        }

    definition = _CALENDARS.get(market_key)
    if definition is None:
        raise ValueError(f"unsupported market calendar: {market!r}")
    return {
        "market": definition.market,
        "version": definition.version,
        "timezone": definition.timezone_name,
        "covered_years": definition.covered_years,
        "sources": definition.sources,
    }
