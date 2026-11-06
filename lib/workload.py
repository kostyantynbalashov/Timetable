"""Teacher workload (навантаження) — MVP. See backend README notes carried
over: contact hours only (1 pair = 2 academic hours), norm is a placeholder
you should replace with your institution's real figure."""
from __future__ import annotations

from collections import defaultdict

from .domain import Teacher
from .scheduling import Occurrence

HOURS_PER_OCCURRENCE = 2
DEFAULT_NORM_HOURS_PER_FTE = 600.0


def compute(
    occurrences: list[Occurrence], teachers: dict[str, Teacher], norm_hours_per_fte: float = DEFAULT_NORM_HOURS_PER_FTE
) -> list[dict]:
    by_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for occ in occurrences:
        by_type[occ.lesson.teacher_key][occ.lesson.lesson_type] += HOURS_PER_OCCURRENCE

    out = []
    for key, teacher in teachers.items():
        hours = by_type.get(key, {})
        total = sum(hours.values())
        norm = norm_hours_per_fte * teacher.fte
        out.append(
            {
                "teacher": teacher.full_name,
                "degree": teacher.degree,
                "title": teacher.title,
                "position": teacher.position,
                "fte": teacher.fte,
                "department": teacher.department,
                "by_lesson_type_hours": dict(hours),
                "total_hours": total,
                "norm_hours": norm,
                "load_percentage": round(100 * total / norm, 1) if norm else None,
            }
        )
    return sorted(out, key=lambda r: r["teacher"])
