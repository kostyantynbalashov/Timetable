"""CP-SAT solving for 'стрічковий' (weekly) lessons, plus conflict
validation (not auto-solving) for 'цикловий' and 'довільний' lessons, whose
exact dates/rooms the operator already specified in the spreadsheet."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ortools.sat.python import cp_model

from . import patterns
from .domain import Group, Lesson, Room, Settings, Teacher


@dataclass
class Occurrence:
    lesson: Lesson
    occurrence_date: date
    period: int
    room_label: str
    week_no: int | None = None  # for weekly lessons, which calendar week


def _eligible_rooms(lesson: Lesson, group: Group, rooms: list[Room]) -> list[Room]:
    need = group.size
    out = [r for r in rooms if r.capacity >= need]
    if lesson.room_type:
        out = [r for r in out if r.room_type == lesson.room_type]
    return out


def _room_shortage_hint(lesson: Lesson, group: Group, rooms: list[Room]) -> str:
    """When no room fits, name the closest one anyway so the operator has a
    concrete next step instead of a dead end."""
    by_type = [r for r in rooms if not lesson.room_type or r.room_type == lesson.room_type]
    if not by_type:
        return (
            f"В аркуші «Аудиторії» взагалі немає аудиторій типу «{lesson.room_type}». "
            "Додайте таку аудиторію або приберіть вимогу до типу."
        )
    best = max(by_type, key=lambda r: r.capacity)
    if best.capacity >= group.size:
        return f"Схоже, підійшла б «{best.label}» ({best.capacity} місць) — перевірте, чому її не підбирає скрипт."
    return (
        f"Найбільша підходяща за типом аудиторія — «{best.label}» ({best.capacity} місць), "
        f"а групі «{group.key}» потрібно {group.size}. Варіанти: збільшити аудиторію, "
        "поділити групу на підгрупи, або додати більшу аудиторію в аркуш «Аудиторії»."
    )


def _teacher_free_at(
    teacher_key: str, occ_date: date, period: int, occurrences: list[Occurrence], teacher: Teacher
) -> bool:
    if occ_date.weekday() in teacher.unavailable_weekdays:
        return False
    return not any(
        o.lesson.teacher_key == teacher_key and o.occurrence_date == occ_date and o.period == period
        for o in occurrences
    )


def _group_free_at(group_key: str, occ_date: date, period: int, occurrences: list[Occurrence]) -> bool:
    return not any(
        o.lesson.group_key == group_key and o.occurrence_date == occ_date and o.period == period
        for o in occurrences
    )


def _room_free_at(room_label: str, occ_date: date, period: int, occurrences: list[Occurrence]) -> bool:
    return not any(
        o.room_label == room_label and o.occurrence_date == occ_date and o.period == period
        for o in occurrences
    )


def suggest_substitute_teachers(
    lesson: Lesson, occ_date: date, period: int, teachers: dict[str, Teacher],
    occurrences: list[Occurrence], max_suggestions: int = 3,
) -> list[str]:
    """Other teachers who teach the same subject and are free at that exact
    date+period — answers "ким я можу його замінити?"."""
    subject_norm = lesson.subject.strip().lower()
    out = []
    for key, t in teachers.items():
        if key == lesson.teacher_key:
            continue
        if not any(s.strip().lower() == subject_norm for s in t.subjects):
            continue
        if _teacher_free_at(key, occ_date, period, occurrences, t):
            out.append(t.display_short)
        if len(out) >= max_suggestions:
            break
    return out


def suggest_alt_dates(
    lesson: Lesson, room_label: str, occ_date: date, period: int, teacher: Teacher,
    occurrences: list[Occurrence], window_days: int = 14, max_suggestions: int = 3,
) -> list[str]:
    """Nearby weekdays, same period, where the lesson's teacher, group and
    room are all free — answers "куди мені краще перемістити цю пару?"."""
    out = []
    for offset in list(range(1, window_days + 1)):
        for d in (occ_date + timedelta(days=offset), occ_date - timedelta(days=offset)):
            if d.weekday() >= 5:
                continue
            if not _teacher_free_at(lesson.teacher_key, d, period, occurrences, teacher):
                continue
            if not _group_free_at(lesson.group_key, d, period, occurrences):
                continue
            if not _room_free_at(room_label, d, period, occurrences):
                continue
            out.append(d.isoformat())
            if len(out) >= max_suggestions:
                return sorted(out)
    return sorted(out)


def solve_weekly(
    lessons: list[Lesson],
    teachers: dict[str, Teacher],
    groups: dict[str, Group],
    rooms: list[Room],
    settings: Settings,
    warnings: list[str],
) -> list[Occurrence]:
    weekly = [l for l in lessons if l.pattern_type == "стрічковий"]
    if not weekly:
        return []

    model = cp_model.CpModel()
    # each (lesson, session-index) is one "unit" needing a fixed weekly slot+room
    units = []  # (lesson, k, weeks:set[int])
    for l in weekly:
        weeks = patterns.parse_weeks(l.weeks_spec, 1, settings.weeks)
        if not weeks:
            warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): порожній список тижнів — пропущено.")
            continue
        for k in range(max(1, l.sessions_per_week)):
            units.append((l, k, weeks))

    # candidate vars: unit_idx -> {(day,period,room_key): var}
    cand: list[dict[tuple[int, int, str], cp_model.IntVar]] = []
    for idx, (l, k, weeks) in enumerate(units):
        group = groups[l.group_key]
        teacher = teachers[l.teacher_key]
        elig_rooms = _eligible_rooms(l, group, rooms)
        if not elig_rooms:
            warnings.append(
                f"Заняття, рядок {l.row} («{l.subject}»): немає аудиторії з потрібною місткістю/типом. "
                + _room_shortage_hint(l, group, rooms)
            )
            cand.append({})
            continue
        slots = {}
        for day in range(settings.days_per_week):
            if day in teacher.unavailable_weekdays:
                continue
            for period in range(1, settings.periods_per_day + 1):
                for room in elig_rooms:
                    var = model.new_bool_var(f"u{idx}_d{day}_p{period}_{room.key}")
                    slots[(day, period, room.key)] = var
        cand.append(slots)

    # one slot per unit, OR leave it unassigned (tracked, not silently dropped) —
    # this way one impossible-to-place lesson never blocks everyone else's schedule.
    unassigned: list[cp_model.IntVar | None] = []
    for idx, slots in enumerate(cand):
        if not slots:
            unassigned.append(None)
            continue
        u = model.new_bool_var(f"unassigned_{idx}")
        model.add_exactly_one(list(slots.values()) + [u])
        unassigned.append(u)
    model.minimize(sum(u for u in unassigned if u is not None))

    def weeks_of(idx):
        return units[idx][2]

    room_by_key = {r.key: r for r in rooms}

    # pairwise conflicts, grouped by (day, period) to limit comparisons
    by_day_period: dict[tuple[int, int], list[tuple[int, tuple[int, int, str]]]] = {}
    for idx, slots in enumerate(cand):
        for key in slots:
            day, period, room_key = key
            by_day_period.setdefault((day, period), []).append((idx, key))

    for (_day, _period), entries in by_day_period.items():
        for a in range(len(entries)):
            idx_a, key_a = entries[a]
            lesson_a, _, weeks_a = units[idx_a]
            for b in range(a + 1, len(entries)):
                idx_b, key_b = entries[b]
                if idx_a == idx_b:
                    continue
                lesson_b, _, weeks_b = units[idx_b]
                if not (weeks_a & weeks_b):
                    continue  # never scheduled on the same actual date
                same_room = key_a[2] == key_b[2]
                same_teacher = lesson_a.teacher_key == lesson_b.teacher_key
                same_group = lesson_a.group_key == lesson_b.group_key
                if same_room or same_teacher or same_group:
                    model.add_bool_or([cand[idx_a][key_a].Not(), cand[idx_b][key_b].Not()])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    solver.parameters.num_workers = 8
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        warnings.append(
            "Не вдалося порахувати стрічковий розклад узагалі — схоже на суперечність у даних "
            "(напр. у викладача не лишилось жодного вільного дня). Перевірте «Недоступні дні»."
        )
        return []

    occurrences = []
    unplaced: list[tuple[Lesson, int, bool]] = []  # (lesson, session, had_candidates)
    for idx, (l, k, weeks) in enumerate(units):
        slots = cand[idx]
        if not slots or solver.value(unassigned[idx]):
            unplaced.append((l, k, bool(slots)))
            continue
        assigned = next((key for key, var in slots.items() if solver.value(var)), None)
        day, period, room_key = assigned
        for occ in patterns.weekly_dates(settings.semester_start, day, period, weeks):
            occurrences.append(
                Occurrence(
                    lesson=l, occurrence_date=occ["date"], period=occ["period"],
                    room_label=room_by_key[room_key].label,
                )
            )

    for l, k, had_candidates in unplaced:
        if not had_candidates:
            continue  # already explained above (no eligible room at all)
        substitutes = suggest_substitute_teachers_by_subject(l.subject, l.teacher_key, teachers)
        msg = (
            f"Заняття, рядок {l.row} («{l.subject}», сесія {k + 1}): не вдалося знайти вільний "
            f"час/аудиторію без накладок із рештою розкладу."
        )
        if substitutes:
            msg += f" Цю дисципліну також веде: {', '.join(substitutes)} — можливо, варто передати йому/їй."
        msg += " Або розширте «Тижні» на менш завантажені тижні, чи додайте аудиторію/час."
        warnings.append(msg)

    return occurrences


def suggest_substitute_teachers_by_subject(
    subject: str, exclude_key: str, teachers: dict[str, Teacher]
) -> list[str]:
    subject_norm = subject.strip().lower()
    return [
        t.display_short
        for key, t in teachers.items()
        if key != exclude_key and any(s.strip().lower() == subject_norm for s in t.subjects)
    ]


def _conflict(a: Occurrence, b: Occurrence) -> str | None:
    if a.occurrence_date != b.occurrence_date or a.period != b.period:
        return None
    if a.room_label == b.room_label:
        return "аудиторію"
    if a.lesson.teacher_key == b.lesson.teacher_key:
        return "викладача"
    if a.lesson.group_key == b.lesson.group_key:
        return "групу"
    return None


def _resolve_room(text: str, rooms: list[Room]) -> tuple[str | None, str | None]:
    """Matches an "Аудиторія" cell against the "Аудиторії" sheet, accepting
    either the full label ("НЛаб-810") or, if it's unambiguous, just the
    room number ("810") — operators naturally drop the building when there's
    only one room with that number. Returns (resolved_label, error_or_None)."""
    by_label = {r.label: r for r in rooms}
    if text in by_label:
        return text, None
    by_number = [r for r in rooms if r.number == text]
    if len(by_number) == 1:
        return by_number[0].label, None
    if len(by_number) > 1:
        options = ", ".join(r.label for r in by_number)
        return None, f"номер «{text}» є в кількох аудиторіях ({options}) — вкажіть разом із корпусом."
    return None, f"аудиторії «{text}» немає в аркуші «Аудиторії»."


def add_cyclic_and_custom(
    occurrences: list[Occurrence],
    lessons: list[Lesson],
    teachers: dict[str, Teacher],
    rooms: list[Room],
    warnings: list[str],
) -> list[Occurrence]:
    for l in lessons:
        if l.pattern_type == "цикловий":
            resolved, err = _resolve_room(l.cyclic_room, rooms)
            if err:
                warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): {err}")
                continue
            new_occs = [
                Occurrence(lesson=l, occurrence_date=o["date"], period=o["period"], room_label=resolved)
                for o in patterns.cyclic_dates(l.cyclic_start, l.cyclic_days, l.cyclic_periods)
            ]
        elif l.pattern_type == "довільний":
            resolved, err = _resolve_room(l.custom_room, rooms)
            if err:
                warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): {err}")
                continue
            try:
                parsed = patterns.parse_custom(l.custom_spec)
            except patterns.PatternError as e:
                warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): {e}")
                continue
            new_occs = [
                Occurrence(lesson=l, occurrence_date=o["date"], period=o["period"], room_label=resolved)
                for o in parsed
            ]
        else:
            continue

        teacher = teachers[l.teacher_key]
        warned_unavail_dates = set()
        for occ in new_occs:
            if occ.occurrence_date.weekday() in teacher.unavailable_weekdays:
                if occ.occurrence_date not in warned_unavail_dates:
                    warned_unavail_dates.add(occ.occurrence_date)
                    warnings.append(
                        f"Заняття, рядок {l.row} («{l.subject}»): {occ.occurrence_date.isoformat()} — "
                        f"викладач позначений недоступним у цей день тижня."
                    )
            for existing in occurrences:
                kind = _conflict(occ, existing)
                if kind:
                    msg = (
                        f"Накладка {occ.occurrence_date.isoformat()}, пара {occ.period}: "
                        f"«{l.subject}» (рядок {l.row}) і «{existing.lesson.subject}» "
                        f"(рядок {existing.lesson.row}) претендують на одну й ту саму {kind}."
                    )
                    if kind == "аудиторію":
                        free_rooms = [
                            r.label for r in rooms
                            if r.label != occ.room_label
                            and (not l.room_type or r.room_type == l.room_type)
                            and _room_free_at(r.label, occ.occurrence_date, occ.period, occurrences)
                        ][:3]
                        if free_rooms:
                            msg += f" Вільні на цей час: {', '.join(free_rooms)}."
                    elif kind == "викладача":
                        subs = suggest_substitute_teachers(l, occ.occurrence_date, occ.period, teachers, occurrences)
                        if subs:
                            msg += f" Вільний(і) на цей час викладач(і) цієї дисципліни: {', '.join(subs)}."
                        alt_dates = suggest_alt_dates(l, occ.room_label, occ.occurrence_date, occ.period, teacher, occurrences)
                        if alt_dates:
                            msg += f" Або перенести на: {', '.join(alt_dates)}."
                    elif kind == "групу":
                        alt_dates = suggest_alt_dates(l, occ.room_label, occ.occurrence_date, occ.period, teacher, occurrences)
                        if alt_dates:
                            msg += f" Вільні дати для цього заняття: {', '.join(alt_dates)}."
                    warnings.append(msg)
        occurrences.extend(new_occs)
    return occurrences
