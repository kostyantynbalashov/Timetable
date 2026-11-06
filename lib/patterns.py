"""Parse human-friendly pattern columns from the spreadsheet into structured
data, and expand them into calendar dates."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta


class PatternError(ValueError):
    """Raised with a message meant to be shown to the (non-IT) operator."""


def parse_weeks(spec: str, week_from: int, week_to: int) -> set[int]:
    """'1-16' / 'непарні 1-16' / 'парні 2,4,6-10' -> set of week numbers."""
    spec = (spec or "").strip().lower()
    parity = None
    if spec.startswith("непарні"):
        parity, spec = "odd", spec[len("непарні"):].strip()
    elif spec.startswith("парні"):
        parity, spec = "even", spec[len("парні"):].strip()
    weeks: set[int] = set()
    if not spec:
        weeks = set(range(week_from, week_to + 1))
    else:
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                weeks |= set(range(int(a), int(b) + 1))
            else:
                weeks.add(int(part))
    if parity == "odd":
        weeks = {w for w in weeks if w % 2 == 1}
    elif parity == "even":
        weeks = {w for w in weeks if w % 2 == 0}
    return weeks


WEEKDAY_UA = {
    "пн": 0, "понеділок": 0, "вт": 1, "вівторок": 1, "ср": 2, "середа": 2,
    "чт": 3, "четвер": 3, "пт": 4, "п'ятниця": 4, "пятниця": 4,
    "сб": 5, "субота": 5, "нд": 6, "неділя": 6,
}


def parse_weekday(s: str) -> int:
    key = (s or "").strip().lower()
    if key not in WEEKDAY_UA:
        raise PatternError(f"Невідомий день тижня: «{s}». Приклади: Пн, Вт, Ср, Чт, Пт.")
    return WEEKDAY_UA[key]


def weekly_dates(
    semester_start: date, day_of_week: int, period: int, weeks: set[int]
) -> list[dict]:
    """week 1's Monday == semester_start (semester_start must itself be a Monday)."""
    out = []
    for week_no in sorted(weeks):
        monday = semester_start + timedelta(weeks=week_no - 1)
        day = monday + timedelta(days=day_of_week)
        out.append({"date": day, "period": period})
    return out


def cyclic_dates(date_from: date, days: int, periods: list[int]) -> list[dict]:
    out = []
    for d in range(days):
        day = date_from + timedelta(days=d)
        if day.weekday() >= 5:
            continue
        for period in periods:
            out.append({"date": day, "period": period})
    return out


_CUSTOM_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s*:\s*(\d+)")


def parse_custom(spec: str) -> list[dict]:
    """'02.09.2026:2; 09.09.2026:2' -> [{"date": date(...), "period": 2}, ...]"""
    out = []
    for m in _CUSTOM_RE.finditer(spec or ""):
        d, p = m.groups()
        dd, mm, yyyy = d.split(".")
        out.append({"date": date(int(yyyy), int(mm), int(dd)), "period": int(p)})
    if not out and (spec or "").strip():
        raise PatternError(
            f"Не вдалось розпізнати дати «{spec}». Формат: «ДД.ММ.РРРР:пара; ДД.ММ.РРРР:пара»."
        )
    return out


def parse_periods(spec: str) -> list[int]:
    return [int(x.strip()) for x in (spec or "").split(",") if x.strip()]
