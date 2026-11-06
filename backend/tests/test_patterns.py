from datetime import date

from app.models import PatternType
from app.patterns import generate_occurrences, resolve_calendar_dates


def test_weekly_respects_parity_and_range():
    occs = generate_occurrences(
        PatternType.WEEKLY,
        {"day_of_week": 0, "period": 1, "week_from": 1, "week_to": 6, "week_parity": "odd"},
    )
    assert [o["week_no"] for o in occs] == [1, 3, 5]
    resolved = resolve_calendar_dates(occs, date(2026, 9, 1))  # Tue -> Monday of week1
    assert resolved[0]["date"] == "2026-09-01"


def test_cyclic_skips_weekends():
    occs = generate_occurrences(
        PatternType.CYCLIC, {"date_from": "2026-09-04", "days": 4, "periods": [1, 2]}
    )  # Fri, Sat, Sun, Mon -> Sat/Sun skipped
    dates = {o["date"] for o in occs}
    assert dates == {"2026-09-04", "2026-09-07"}
    assert len(occs) == 4  # 2 days * 2 periods


def test_custom_dedupes():
    occs = generate_occurrences(
        PatternType.CUSTOM,
        {
            "occurrences": [
                {"date": "2026-09-10", "period": 3},
                {"date": "2026-09-10", "period": 3},
                {"date": "2026-09-11", "period": 1},
            ]
        },
    )
    assert len(occs) == 2
