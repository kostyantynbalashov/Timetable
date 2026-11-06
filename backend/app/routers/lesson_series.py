from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..patterns import generate_occurrences, resolve_calendar_dates

router = APIRouter(prefix="/api/lesson-series", tags=["lesson-series"])


@router.get("", response_model=list[schemas.LessonSeriesOut])
def list_series(db: Session = Depends(get_db)):
    return db.query(models.LessonSeries).all()


@router.post("", response_model=schemas.LessonSeriesOut, status_code=201)
def create_series(body: schemas.LessonSeriesIn, db: Session = Depends(get_db)):
    """Creates the series AND materializes its Occurrence rows from the pattern.
    For PatternType.WEEKLY, pattern_params must include "semester_start"
    (ISO date of week 1's Monday) to resolve week_no/day_of_week to real dates.
    """
    series = models.LessonSeries(**body.model_dump())
    db.add(series)
    db.flush()  # get series.id without committing

    try:
        raw = generate_occurrences(body.pattern_type, body.pattern_params)
        if body.pattern_type == models.PatternType.WEEKLY:
            semester_start = date.fromisoformat(body.pattern_params["semester_start"])
            raw = resolve_calendar_dates(raw, semester_start)
    except (KeyError, ValueError) as e:
        db.rollback()
        raise HTTPException(422, f"Invalid pattern_params: {e}") from e

    for occ in raw:
        db.add(
            models.Occurrence(
                series_id=series.id,
                occurrence_date=date.fromisoformat(occ["date"]),
                period=occ["period"],
            )
        )
    db.commit()
    db.refresh(series)
    return series


@router.get("/{series_id}/occurrences", response_model=list[schemas.OccurrenceOut])
def list_occurrences(series_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Occurrence)
        .filter(models.Occurrence.series_id == series_id)
        .order_by(models.Occurrence.occurrence_date, models.Occurrence.period)
        .all()
    )


@router.delete("/{series_id}", status_code=204)
def delete_series(series_id: int, db: Session = Depends(get_db)):
    series = db.get(models.LessonSeries, series_id)
    if not series:
        raise HTTPException(404, "Series not found")
    db.delete(series)  # cascades to occurrences
    db.commit()
