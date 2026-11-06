"""CP-SAT solving for 'стрічковий' (weekly) lessons, plus conflict
validation (not auto-solving) for 'цикловий' and 'довільний' lessons, whose
exact dates/rooms the operator already specified in the spreadsheet."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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
                f"Заняття, рядок {l.row} («{l.subject}»): немає аудиторії з потрібною місткістю/типом."
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

    # exactly one slot per unit (or report infeasible unit)
    for idx, slots in enumerate(cand):
        if not slots:
            continue
        model.add_exactly_one(slots.values())

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
            "Не вдалося розставити стрічкові заняття без накладок — вимог забагато для наявних "
            "аудиторій/часу. Зменшіть кількість занять, додайте аудиторії або розширте «Тижні»."
        )
        return []

    occurrences = []
    for idx, (l, k, weeks) in enumerate(units):
        slots = cand[idx]
        assigned = next((key for key, var in slots.items() if solver.value(var)), None)
        if assigned is None:
            continue
        day, period, room_key = assigned
        for occ in patterns.weekly_dates(settings.semester_start, day, period, weeks):
            occurrences.append(
                Occurrence(
                    lesson=l, occurrence_date=occ["date"], period=occ["period"],
                    room_label=room_by_key[room_key].label,
                )
            )
    return occurrences


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


def add_cyclic_and_custom(
    occurrences: list[Occurrence],
    lessons: list[Lesson],
    teachers: dict[str, Teacher],
    rooms: list[Room],
    warnings: list[str],
) -> list[Occurrence]:
    room_labels = {r.label for r in rooms}
    for l in lessons:
        if l.pattern_type == "цикловий":
            if l.cyclic_room not in room_labels:
                warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): аудиторії «{l.cyclic_room}» немає в аркуші «Аудиторії».")
                continue
            new_occs = [
                Occurrence(lesson=l, occurrence_date=o["date"], period=o["period"], room_label=l.cyclic_room)
                for o in patterns.cyclic_dates(l.cyclic_start, l.cyclic_days, l.cyclic_periods)
            ]
        elif l.pattern_type == "довільний":
            if l.custom_room not in room_labels:
                warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): аудиторії «{l.custom_room}» немає в аркуші «Аудиторії».")
                continue
            try:
                parsed = patterns.parse_custom(l.custom_spec)
            except patterns.PatternError as e:
                warnings.append(f"Заняття, рядок {l.row} («{l.subject}»): {e}")
                continue
            new_occs = [
                Occurrence(lesson=l, occurrence_date=o["date"], period=o["period"], room_label=l.custom_room)
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
                    warnings.append(
                        f"Накладка {occ.occurrence_date.isoformat()}, пара {occ.period}: "
                        f"«{l.subject}» (рядок {l.row}) і «{existing.lesson.subject}» "
                        f"(рядок {existing.lesson.row}) претендують на одну й ту саму {kind}."
                    )
        occurrences.extend(new_occs)
    return occurrences
