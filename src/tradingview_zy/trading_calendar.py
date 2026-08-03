from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
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


_MORNING_A = Session(time(9, 30), time(11, 30))
_AFTERNOON_A = Session(time(13, 0), time(15, 0))
_MORNING_HK = Session(time(9, 30), time(12, 0))
_AFTERNOON_HK = Session(time(13, 0), time(16, 0))
_US_CORE = Session(time(9, 30), time(16, 0))
_US_EARLY = Session(time(9, 30), time(13, 0))


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


def _normalise_instant(at: datetime | None) -> datetime:
    if at is None:
        return datetime.now(timezone.utc)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("market calendar requires a timezone-aware datetime")
    return at


def _is_fx_open(at: datetime) -> bool:
    """Generic spot-FX 24x5 boundary in New York local time.

    This deliberately models only the global weekly boundary. Venue-specific
    maintenance and holiday exceptions require an instrument/venue identifier
    and are handled by the broader calendar-governance work rather than being
    guessed here.
    """
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


def is_market_open(market: str, at: datetime | None = None) -> bool:
    """Return a strict bool using a timezone-aware, versioned market calendar.

    Cash-market calendars fail closed outside their explicitly versioned year;
    this avoids silently treating an unknown future holiday as an open session.
    """
    instant = _normalise_instant(at)
    market_key = str(market).strip().lower()
    if market_key == "fx":
        return _is_fx_open(instant)

    definition = _CALENDARS.get(market_key)
    if definition is None:
        raise ValueError(f"unsupported market calendar: {market!r}")

    local = instant.astimezone(ZoneInfo(definition.timezone_name))
    local_date = local.date()
    if local_date.year not in definition.covered_years:
        return False
    if local.weekday() >= 5 or local_date in definition.closed_dates:
        return False

    sessions = definition.special_sessions.get(
        local_date, definition.regular_sessions
    )
    local_time = local.time().replace(tzinfo=None)
    return any(session.contains(local_time) for session in sessions)


def market_calendar_metadata(market: str) -> dict[str, object]:
    market_key = str(market).strip().lower()
    if market_key == "fx":
        return {
            "market": "fx",
            "version": "FX-24x5-v1",
            "timezone": "America/New_York",
            "covered_years": (),
            "sources": ("generic spot-FX weekly boundary",),
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
