"""Teacher workload (навантаження) computation — MVP.

Ukrainian universities compute workload in *academic hours* (1 pair = 2 ac.
hours) against a norm tied to the FTE ("ставка"), with institution-specific
rules for splitting groups into subgroups for practicals/labs, methodical
work, etc. Those rules differ by university and are NOT hard-coded here.

What IS implemented: contact-hour totals per teacher, per lesson type, from
the scheduled Occurrence rows (the ground truth — not the pattern, so
cancellations/moves are already reflected). The per-FTE norm is a parameter
you pass in (ask the department for the real number), defaulting to 600 h,
a common full-time contact-hour figure — treat it as a placeholder.
"""
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models

HOURS_PER_OCCURRENCE = 2  # 1 пара = 2 академічні години
DEFAULT_NORM_HOURS_PER_FTE = 600.0


def teacher_workload(db: Session, academic_year: str, semester: int, norm_hours_per_fte: float = DEFAULT_NORM_HOURS_PER_FTE) -> list[dict]:
    rows = (
        db.query(
            models.Teacher,
            models.LessonSeries.lesson_type,
            func.count(models.Occurrence.id).label("n"),
        )
        .join(models.LessonSeries, models.LessonSeries.teacher_id == models.Teacher.id)
        .join(models.Occurrence, models.Occurrence.series_id == models.LessonSeries.id)
        .filter(
            models.LessonSeries.academic_year == academic_year,
            models.LessonSeries.semester == semester,
            models.Occurrence.status == models.OccurrenceStatus.SCHEDULED,
        )
        .group_by(models.Teacher.id, models.LessonSeries.lesson_type)
        .all()
    )

    by_teacher: dict[int, dict] = {}
    breakdown: dict[int, dict] = defaultdict(dict)
    for teacher, lesson_type, n in rows:
        by_teacher[teacher.id] = teacher
        breakdown[teacher.id][lesson_type.value] = n * HOURS_PER_OCCURRENCE

    out = []
    for teacher_id, teacher in by_teacher.items():
        total = sum(breakdown[teacher_id].values())
        norm = norm_hours_per_fte * float(teacher.fte)
        out.append(
            {
                "teacher_id": teacher_id,
                "teacher": teacher.full_name,
                "fte": float(teacher.fte),
                "by_lesson_type_hours": breakdown[teacher_id],
                "total_hours": total,
                "norm_hours": norm,
                "load_percentage": round(100 * total / norm, 1) if norm else None,
            }
        )
    return sorted(out, key=lambda r: r["teacher"])
