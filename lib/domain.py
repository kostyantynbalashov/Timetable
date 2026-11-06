"""Parses raw spreadsheet rows (dicts of Ukrainian column name -> value) into
clean entities. Bad rows are skipped and reported in `warnings`, mirroring
the latin-dictionary build's "report, don't fail" approach."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from . import patterns


def _s(v) -> str:
    return str(v).strip() if v is not None else ""


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
        return f"{self.building}-{self.number}"


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
        if not building or not number or not capacity:
            warnings.append(f"Аудиторії, рядок {i}: пропущено — потрібні корпус, номер і місткість.")
            continue
        room = Room(
            key=f"{building}-{number}", building=building, floor=int(_num(r.get("поверх"), 0)),
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
