from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..workload import DEFAULT_NORM_HOURS_PER_FTE, teacher_workload

router = APIRouter(prefix="/api/workload", tags=["workload"])


@router.get("/teachers")
def get_teacher_workload(
    academic_year: str,
    semester: int,
    norm_hours_per_fte: float = DEFAULT_NORM_HOURS_PER_FTE,
    db: Session = Depends(get_db),
):
    return teacher_workload(db, academic_year, semester, norm_hours_per_fte)
