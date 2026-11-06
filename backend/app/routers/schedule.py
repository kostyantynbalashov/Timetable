"""Read-only schedule views for end users: by group, by teacher, by room."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


def _occurrences_query(db: Session, date_from: date, date_to: date):
    return (
        db.query(models.Occurrence)
        .join(models.LessonSeries)
        .options(
            joinedload(models.Occurrence.series).joinedload(models.LessonSeries.subject),
            joinedload(models.Occurrence.series).joinedload(models.LessonSeries.teacher),
            joinedload(models.Occurrence.series).joinedload(models.LessonSeries.group),
            joinedload(models.Occurrence.room),
        )
        .filter(
            models.Occurrence.occurrence_date >= date_from,
            models.Occurrence.occurrence_date <= date_to,
            models.Occurrence.status == models.OccurrenceStatus.SCHEDULED,
        )
    )


def _serialize(occ: models.Occurrence) -> dict:
    s = occ.series
    return {
        "date": occ.occurrence_date.isoformat(),
        "period": occ.period,
        "subject": s.subject.name,
        "lesson_type": s.lesson_type.value,
        "teacher": s.teacher.full_name,
        "group": s.group.code,
        "room": occ.room.label if occ.room else None,
    }


@router.get("/group/{group_id}")
def schedule_for_group(
    group_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    q = _occurrences_query(db, date_from, date_to).filter(models.LessonSeries.group_id == group_id)
    return [_serialize(o) for o in q.order_by(models.Occurrence.occurrence_date, models.Occurrence.period)]


@router.get("/teacher/{teacher_id}")
def schedule_for_teacher(
    teacher_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    q = _occurrences_query(db, date_from, date_to).filter(
        models.LessonSeries.teacher_id == teacher_id
    )
    return [_serialize(o) for o in q.order_by(models.Occurrence.occurrence_date, models.Occurrence.period)]


@router.get("/department/{department_id}")
def schedule_for_department(
    department_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    """Для зав. кафедри: усі заняття викладачів кафедри."""
    q = (
        _occurrences_query(db, date_from, date_to)
        .join(models.Teacher, models.LessonSeries.teacher_id == models.Teacher.id)
        .filter(models.Teacher.department_id == department_id)
    )
    return [_serialize(o) for o in q.order_by(models.Occurrence.occurrence_date, models.Occurrence.period)]
