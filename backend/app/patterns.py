"""Generate concrete (date, period) occurrences from a LessonSeries pattern."""
from datetime import date, timedelta

from .models import PatternType


def generate_occurrences(pattern_type: PatternType, params: dict) -> list[dict]:
    """Returns a list of {"date": date, "period": int}, sorted, deduplicated."""
    if pattern_type == PatternType.WEEKLY:
        return _weekly(params)
    if pattern_type == PatternType.CYCLIC:
        return _cyclic(params)
    if pattern_type == PatternType.CUSTOM:
        return _custom(params)
    raise ValueError(f"Unknown pattern type: {pattern_type}")


def _weekly(p: dict) -> list[dict]:
    """Стрічковий: same weekday + period every week (optionally every-other)."""
    week_from, week_to = p["week_from"], p["week_to"]
    day_of_week, period = p["day_of_week"], p["period"]
    parity = p.get("week_parity", "any")  # any | odd | even
    out = []
    for week_no in range(week_from, week_to + 1):
        if parity == "odd" and week_no % 2 == 0:
            continue
        if parity == "even" and week_no % 2 == 1:
            continue
        out.append({"week_no": week_no, "day_of_week": day_of_week, "period": period})
    return out


def _cyclic(p: dict) -> list[dict]:
    """Цикловий: consecutive calendar days, same period(s), starting a date."""
    start = date.fromisoformat(p["date_from"])
    days, periods = p["days"], p["periods"]
    out = []
    for d in range(days):
        day = start + timedelta(days=d)
        if day.weekday() >= 5:  # skip weekends
            continue
        for period in periods:
            out.append({"date": day.isoformat(), "period": period})
    return out


def _custom(p: dict) -> list[dict]:
    """Довільний: explicit list, as given, after de-dup."""
    seen = set()
    out = []
    for occ in p["occurrences"]:
        key = (occ["date"], occ["period"])
        if key not in seen:
            seen.add(key)
            out.append(occ)
    return out


def resolve_calendar_dates(
    occurrences: list[dict], semester_start: date
) -> list[dict]:
    """WEEKLY pattern output uses week_no/day_of_week; convert to actual dates
    given the semester's first Monday (week 1)."""
    out = []
    for occ in occurrences:
        if "date" in occ:
            out.append(occ)
            continue
        monday = semester_start + timedelta(weeks=occ["week_no"] - 1)
        day = monday + timedelta(days=occ["day_of_week"])
        out.append({"date": day.isoformat(), "period": occ["period"]})
    return out
