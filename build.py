#!/usr/bin/env python3
"""
Збирає сайт розкладу з Google Таблиці (або локального .xlsx для перевірки).

    Google Sheet / data_samples/sample.xlsx  ->  site/data.js (публічний розклад)
                                              ->  приватна вкладка «Навантаження» (лише в Google Таблиці)

Запуск локально:  python build.py
На GitHub це відбувається автоматично (за розкладом або вручну, Actions).
"""
import json
import os
import sys
from datetime import date

from lib.domain import parse_groups, parse_lessons, parse_settings, parse_teachers
from lib.scheduling import add_cyclic_and_custom, solve_weekly
from lib.sheet_source import load_source, write_private_sheet
from lib.workload import DEFAULT_NORM_HOURS_PER_FTE, compute as compute_workload

OUT = "site/data.js"


def build():
    warnings: list[str] = []
    raw = load_source()

    settings = parse_settings(raw["Налаштування"], warnings)
    teacher_list = parse_teachers(raw["Викладачі"], warnings)
    teachers = {t.key: t for t in teacher_list}
    group_list = parse_groups(raw["Групи"], warnings)
    groups = {g.key: g for g in group_list}
    rooms = []
    from lib.domain import parse_rooms
    rooms = parse_rooms(raw["Аудиторії"], warnings)
    lessons = parse_lessons(raw["Заняття"], teachers, groups, warnings)

    occurrences = solve_weekly(lessons, teachers, groups, rooms, settings, warnings)
    occurrences = add_cyclic_and_custom(occurrences, lessons, teachers, rooms, warnings)
    occurrences.sort(key=lambda o: (o.occurrence_date, o.period))

    # ---- public payload: schedule only, no degree/title/position/fte/workload
    public_occurrences = [
        {
            "date": o.occurrence_date.isoformat(),
            "period": o.period,
            "subject": o.lesson.subject,
            "lesson_type": o.lesson.lesson_type,
            "teacher": teachers[o.lesson.teacher_key].display_short,
            "group": o.lesson.group_key,
            "room": o.room_label,
        }
        for o in occurrences
    ]
    public_groups = [{"code": g.key, "faculty": g.faculty, "specialty": g.specialty_name, "size": g.size} for g in group_list]
    public_teachers = [{"name": t.display_short, "department": t.department} for t in teacher_list]
    public_rooms = [{"label": r.label, "building": r.building, "capacity": r.capacity, "type": r.room_type} for r in rooms]

    # сумарні (фактично заплановані) години по дисциплінах — для картки
    # дисципліни на сайті; не навчальний план, а те, що реально в розкладі.
    subject_hours: dict[str, dict[str, int]] = {}
    for o in occurrences:
        by_type = subject_hours.setdefault(o.lesson.subject, {})
        by_type[o.lesson.lesson_type] = by_type.get(o.lesson.lesson_type, 0) + 2  # 1 пара = 2 акад. год.
    public_subjects = [
        {"name": name, "total_hours": sum(by_type.values()), "by_type": by_type}
        for name, by_type in subject_hours.items()
    ]

    data = {
        "built": date.today().isoformat(),
        "settings": {
            "semester_start": settings.semester_start.isoformat(),
            "weeks": settings.weeks,
        },
        "occurrences": public_occurrences,
        "groups": public_groups,
        "teachers": public_teachers,
        "rooms": public_rooms,
        "subjects": public_subjects,
        "warnings": warnings,
    }
    os.makedirs("site", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.TIMETABLE=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")

    # ---- private payload: workload, written back to the Google Sheet only
    norm = float(os.environ.get("WORKLOAD_NORM_HOURS", DEFAULT_NORM_HOURS_PER_FTE))
    workload_rows = compute_workload(occurrences, teachers, norm)
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sheet_id and creds_json:
        header = ["Викладач", "Кафедра", "Ступінь", "Звання", "Посада", "Ставка",
                   "Усього год.", "Норма год.", "% навантаження", "За типами занять"]
        rows = [header] + [
            [r["teacher"], r["department"], r["degree"], r["title"], r["position"], r["fte"],
             r["total_hours"], r["norm_hours"], r["load_percentage"],
             "; ".join(f"{k}: {v}" for k, v in r["by_lesson_type_hours"].items())]
            for r in workload_rows
        ]
        write_private_sheet(sheet_id, "Навантаження (авто)", rows, creds_json)
        print(f"Навантаження записано у приватну вкладку «Навантаження (авто)» ({len(workload_rows)} викладачів).")
    else:
        # local run: write next to the sample for inspection, never under site/
        with open("data_samples/workload_preview.json", "w", encoding="utf-8") as f:
            json.dump(workload_rows, f, ensure_ascii=False, indent=2)
        print("Локальний запуск: навантаження збережено в data_samples/workload_preview.json (не публікується).")

    print(f"Готово: {len(occurrences)} занять, {len(teacher_list)} викладачів, {len(group_list)} груп, {len(rooms)} аудиторій.")
    for w in warnings:
        print("Увага:", w)
    # Сайт публікується завжди (як і словник) — навіть із зауваженнями;
    # їх видно і в журналі Actions, і на самому сайті (розділ "Зауваження").
    return 0


if __name__ == "__main__":
    sys.exit(build())
