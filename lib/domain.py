"""Parses raw spreadsheet rows (dicts of Ukrainian column name -> value) into
clean entities. Bad rows are skipped and reported in `warnings`, mirroring
the latin-dictionary build's "report, don't fail" approach."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from . import patterns

_WS_RE = re.compile(r"\s+")
HOURS_PER_SESSION = 2  # 1 пара = 2 академічні години


def _s(v) -> str:
    """To text, with whitespace normalized: non-breaking spaces and runs of
    spaces/tabs collapse to one regular space, and the ends are trimmed.
    Matters because spreadsheet formulas (e.g. a "ПІБ" helper column built
    with =A2&" "&B2&" "&C2) can introduce a non-breaking space or doubled
    space that looks identical to a plain space but breaks exact-match
    lookups (teacher/group/room cross-references) without this."""
    if v is None:
        return ""
    s = str(v).replace("\xa0", " ").replace("​", "")
    return _WS_RE.sub(" ", s).strip()


def _num(v, default=None):
    if v in (None, ""):
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _as_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _s(v)
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class Settings:
    semester_start: date
    weeks: int
    days_per_week: int
    periods_per_day: int


@dataclass
class Teacher:
    key: str  # full name, used to cross-reference from "Заняття"
    last_name: str
    first_name: str
    middle_name: str
    degree: str
    title: str
    position: str
    fte: float
    department: str
    faculty: str
    subjects: list[str]
    unavailable_weekdays: set[int] = field(default_factory=set)

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    @property
    def display_short(self) -> str:
        initials = "".join(f"{p[0]}." for p in (self.first_name, self.middle_name) if p)
        return f"{self.last_name} {initials}"


@dataclass
class Room:
    key: str  # "building-number", used to cross-reference
    building: str
    floor: int
    number: str
    capacity: int
    room_type: str
    department: str

    @property
    def label(self) -> str:
        return f"{self.building}-{self.number}" if self.building else self.number


@dataclass
class Group:
    key: str  # code
    faculty: str
    specialty_code: str
    specialty_name: str
    program: str
    enrollment_year: int
    size: int


@dataclass
class Discipline:
    """Рядок аркуша «Дисципліни» — навчальний план: скільки годин лекцій/
    практичних/СРС передбачено. «Опис» — те саме, що «Дисципліна» в
    «Заняттях» (ключ для зіставлення)."""
    key: str  # "Опис"
    name: str
    specialty: str
    course: int
    lecture_hours: float
    practical_hours: float
    srs_hours: float


@dataclass
class Lesson:
    row: int
    subject: str
    teacher_key: str
    group_key: str
    lesson_type: str
    pattern_type: str  # weekly | cyclic | custom
    room_type: str = ""
    min_capacity: int = 0
    # weekly
    sessions_per_week: int = 1
    weeks_spec: str = ""
    # cyclic
    cyclic_start: date | None = None
    cyclic_days: int = 0
    cyclic_periods: list[int] = field(default_factory=list)
    cyclic_room: str = ""
    # custom
    custom_room: str = ""
    custom_spec: str = ""


def parse_settings(rows: list[dict], warnings: list[str]) -> Settings:
    kv = {_s(r.get("параметр")).lower(): r.get("значення") for r in rows}
    start = _as_date(kv.get("дата початку семестру"))
    if start is None:
        warnings.append("Налаштування: не вказано «Дата початку семестру» — взято сьогодні.")
        start = date.today()
    if start.weekday() != 0:
        warnings.append(
            f"Налаштування: «Дата початку семестру» ({start.isoformat()}) — не понеділок; "
            "тиждень 1 однаково рахується від найближчого понеділка."
        )
        start = start - __import__("datetime").timedelta(days=start.weekday())
    return Settings(
        semester_start=start,
        weeks=int(_num(kv.get("кількість тижнів"), 16)),
        days_per_week=int(_num(kv.get("днів на тиждень"), 5)),
        periods_per_day=int(_num(kv.get("пар на день"), 6)),
    )


def parse_teachers(rows: list[dict], warnings: list[str]) -> list[Teacher]:
    out = []
    for i, r in enumerate(rows, start=2):
        last = _s(r.get("прізвище"))
        first = _s(r.get("ім'я") or r.get("імя"))
        if not last or not first:
            warnings.append(f"Викладачі, рядок {i}: пропущено — немає прізвища або імені.")
            continue
        subjects = [x.strip() for x in _s(r.get("предмети")).split(",") if x.strip()]
        unavail = set()
        for token in _s(r.get("недоступні дні")).split(","):
            token = token.strip()
            if token:
                try:
                    unavail.add(patterns.parse_weekday(token))
                except patterns.PatternError as e:
                    warnings.append(f"Викладачі, рядок {i}: {e}")
        t = Teacher(
            key="", last_name=last, first_name=first, middle_name=_s(r.get("по батькові")),
            degree=_s(r.get("ступінь")) or "немає", title=_s(r.get("звання")) or "немає",
            position=_s(r.get("посада")), fte=_num(r.get("ставка"), 1.0),
            department=_s(r.get("кафедра")), faculty=_s(r.get("факультет")),
            subjects=subjects, unavailable_weekdays=unavail,
        )
        t.key = t.full_name
        out.append(t)
    dupes = {t.key for t in out if sum(1 for x in out if x.key == t.key) > 1}
    for d in dupes:
        warnings.append(f"Викладачі: ПІБ «{d}» повторюється — у «Заняттях» буде обрано перший збіг.")
    return out


def parse_rooms(rows: list[dict], warnings: list[str]) -> list[Room]:
    out = []
    for i, r in enumerate(rows, start=2):
        building, number = _s(r.get("корпус")), _s(r.get("номер"))
        capacity = _num(r.get("місткість"))
        if not number or not capacity:
            warnings.append(f"Аудиторії, рядок {i}: пропущено — потрібні принаймні номер і місткість.")
            continue
        key = f"{building}-{number}" if building else number
        room = Room(
            key=key, building=building, floor=int(_num(r.get("поверх"), 0)),
            number=number, capacity=int(capacity), room_type=_s(r.get("тип")) or "інше",
            department=_s(r.get("кафедра")),
        )
        out.append(room)
    return out


def parse_groups(rows: list[dict], warnings: list[str]) -> list[Group]:
    out = []
    for i, r in enumerate(rows, start=2):
        code = _s(r.get("код групи"))
        if not code:
            warnings.append(f"Групи, рядок {i}: пропущено — немає коду групи.")
            continue
        out.append(
            Group(
                key=code, faculty=_s(r.get("факультет")),
                specialty_code=_s(r.get("спеціальність (код)")),
                specialty_name=_s(r.get("спеціальність (назва)")),
                program=_s(r.get("освітня програма")),
                enrollment_year=int(_num(r.get("рік зарахування"), 0)),
                size=int(_num(r.get("чисельність"), 0)),
            )
        )
    return out


def parse_disciplines(rows: list[dict], warnings: list[str]) -> dict[str, Discipline]:
    out = {}
    for i, r in enumerate(rows, start=2):
        key = _s(r.get("опис"))
        name = _s(r.get("назва"))
        if not key or not name:
            continue  # допоміжний аркуш, порожні/недозаповнені рядки просто ігноруємо
        if key in out:
            warnings.append(f"Дисципліни, рядок {i}: «Опис» «{key}» повторюється — взято перший збіг.")
            continue
        out[key] = Discipline(
            key=key, name=name, specialty=_s(r.get("спеціальність")),
            course=int(_num(r.get("курс"), 0)),
            lecture_hours=_num(r.get("лекції (год)"), 0) or 0,
            practical_hours=_num(r.get("практичні (год.)") or r.get("практичні (год)"), 0) or 0,
            srs_hours=_num(r.get("срс"), 0) or 0,
        )
    return out


LESSON_TYPE_TO_PLAN_FIELD = {"лекція": "lecture_hours", "практичне": "practical_hours"}


def _weeks_for_count(week_from: int, parity: str | None, count: int, max_week: int) -> int:
    """Last week number such that [week_from..result] filtered by parity has
    exactly `count` weeks (or runs out at max_week)."""
    picked = 0
    w = week_from
    last = week_from
    while w <= max_week and picked < count:
        if parity == "odd" and w % 2 == 0:
            w += 1
            continue
        if parity == "even" and w % 2 == 1:
            w += 1
            continue
        last = w
        picked += 1
        w += 1
    return last


def apply_discipline_plans(
    lessons: list["Lesson"], disciplines: dict[str, Discipline], settings: Settings, warnings: list[str]
) -> None:
    """For 'стрічковий' lessons matching a 'Дисципліни' row (by subject text
    == «Опис»): the planned hours (lecture/practical) decide how long the
    lesson runs — it stops once the topic's hours are used up — regardless
    of what's in «Тижні» (which, in practice, is often filled in out of habit
    rather than as a deliberate override). Only the *start* week and
    odd/even parity are taken from «Тижні», if given; the end is always
    recomputed from the plan. A mismatch is reported either way, so nothing
    changes silently."""
    for l in lessons:
        if l.pattern_type != "стрічковий":
            continue
        disc = disciplines.get(l.subject)
        field_name = LESSON_TYPE_TO_PLAN_FIELD.get(l.lesson_type.lower())
        if not disc or not field_name:
            continue
        planned_hours = getattr(disc, field_name)
        if not planned_hours:
            continue
        planned_sessions = math.ceil(planned_hours / HOURS_PER_SESSION)
        per_week = max(1, l.sessions_per_week)
        weeks_needed = math.ceil(planned_sessions / per_week)

        spec = l.weeks_spec.strip().lower()
        parity = "odd" if spec.startswith("непарні") else "even" if spec.startswith("парні") else None
        prior_weeks = patterns.parse_weeks(l.weeks_spec, 1, settings.weeks) if l.weeks_spec else set()
        week_from = min(prior_weeks) if prior_weeks else 1

        week_to = _weeks_for_count(week_from, parity, weeks_needed, settings.weeks)
        new_spec = (("непарні " if parity == "odd" else "парні " if parity == "even" else "")
                    + f"{week_from}-{week_to}")

        if l.weeks_spec and l.weeks_spec.strip().lower() != new_spec.strip().lower():
            actual_hours = len(prior_weeks) * per_week * HOURS_PER_SESSION if prior_weeks else None
            msg = (
                f"Заняття, рядок {l.row} («{l.subject}», {l.lesson_type}): «Тижні» ("
                f"{l.weeks_spec}"
                + (f" → {actual_hours:.0f} год." if actual_hours is not None else "")
                + f") не відповідає навчальному плану ({planned_hours:.0f} год.) — узято з плану: «{new_spec}»."
            )
            warnings.append(msg)
        l.weeks_spec = new_spec

        if week_from + (2 if parity else 1) * (weeks_needed - 1) > settings.weeks:
            warnings.append(
                f"Заняття, рядок {l.row} («{l.subject}», {l.lesson_type}): за навчальним планом "
                f"({planned_hours:.0f} год.) треба {weeks_needed} тижнів при {per_week} пар(ах)/тиждень, "
                f"а в семестрі (з тижня {week_from}) стільки не вміщається. Збільшіть «Пар на тиждень» "
                "або кількість тижнів семестру в «Налаштуваннях»."
            )


VALID_PATTERNS = {"стрічковий", "цикловий", "довільний"}


def parse_lessons(
    rows: list[dict], teachers: dict[str, Teacher], groups: dict[str, Group], warnings: list[str]
) -> list[Lesson]:
    out = []
    for i, r in enumerate(rows, start=2):
        subject = _s(r.get("дисципліна"))
        teacher_key = _s(r.get("викладач"))
        group_key = _s(r.get("група"))
        lesson_type = _s(r.get("тип заняття"))
        pattern_type = _s(r.get("тип розкладу")).lower()
        if not subject or not teacher_key or not group_key or not lesson_type:
            warnings.append(f"Заняття, рядок {i}: пропущено — не заповнені обов'язкові поля.")
            continue
        if teacher_key not in teachers:
            warnings.append(f"Заняття, рядок {i} («{subject}»): викладача «{teacher_key}» немає в аркуші «Викладачі».")
            continue
        if group_key not in groups:
            warnings.append(f"Заняття, рядок {i} («{subject}»): групи «{group_key}» немає в аркуші «Групи».")
            continue
        if pattern_type not in VALID_PATTERNS:
            warnings.append(
                f"Заняття, рядок {i} («{subject}»): невідомий «Тип розкладу» — «{pattern_type}». "
                "Очікується: стрічковий / цикловий / довільний."
            )
            continue

        lesson = Lesson(
            row=i, subject=subject, teacher_key=teacher_key, group_key=group_key,
            lesson_type=lesson_type, pattern_type=pattern_type,
            room_type=_s(r.get("тип аудиторії")),
        )
        try:
            if pattern_type == "стрічковий":
                lesson.sessions_per_week = int(_num(r.get("пар на тиждень"), 1))
                lesson.weeks_spec = _s(r.get("тижні"))
            elif pattern_type == "цикловий":
                start = _as_date(r.get("дата початку"))
                if start is None:
                    raise patterns.PatternError("не вказано «Дата початку» для циклового заняття")
                lesson.cyclic_start = start
                lesson.cyclic_days = int(_num(r.get("к-сть днів"), 0))
                lesson.cyclic_periods = patterns.parse_periods(_s(r.get("пари")))
                lesson.cyclic_room = _s(r.get("аудиторія"))
                if not lesson.cyclic_room:
                    raise patterns.PatternError("не вказано «Аудиторія» для циклового заняття")
            else:  # довільний
                lesson.custom_room = _s(r.get("аудиторія"))
                lesson.custom_spec = _s(r.get("дати та пари"))
                if not lesson.custom_room:
                    raise patterns.PatternError("не вказано «Аудиторія» для довільного заняття")
        except patterns.PatternError as e:
            warnings.append(f"Заняття, рядок {i} («{subject}»): {e}")
            continue
        out.append(lesson)
    return out
