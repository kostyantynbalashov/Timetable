"""Excel import for operators: one file per entity type, Ukrainian headers.
Unknown reference values (кафедра/факультет/спеціальність/предмет) are
created on the fly so operators don't need to pre-populate lookup tables.
Rows with missing required fields are skipped and reported, the rest import.
"""
import io

import pandas as pd
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db

router = APIRouter(prefix="/api/import", tags=["import"])


def _read(file: UploadFile) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file.file.read()))


def _get_or_create(db: Session, model, **filters):
    obj = db.query(model).filter_by(**filters).first()
    if not obj:
        obj = model(**filters)
        db.add(obj)
        db.flush()
    return obj


@router.post("/teachers")
async def import_teachers(file: UploadFile, db: Session = Depends(get_db)):
    """Columns: Прізвище*, Ім'я*, По батькові, Ступінь, Звання, Посада*,
    Ставка, Кафедра, Факультет, Предмети (через кому)."""
    df = _read(file)
    created, errors = 0, []
    for i, row in df.iterrows():
        try:
            dept = None
            if pd.notna(row.get("Кафедра")) and pd.notna(row.get("Факультет")):
                faculty = _get_or_create(db, models.Faculty, name=str(row["Факультет"]).strip())
                dept = _get_or_create(
                    db, models.Department, faculty_id=faculty.id, name=str(row["Кафедра"]).strip()
                )
            teacher = models.Teacher(
                last_name=str(row["Прізвище"]).strip(),
                first_name=str(row["Ім'я"]).strip(),
                middle_name=(str(row["По батькові"]).strip() if pd.notna(row.get("По батькові")) else None),
                degree=models.Degree(row["Ступінь"]) if pd.notna(row.get("Ступінь")) else models.Degree.NONE,
                academic_title=(
                    models.AcademicTitle(row["Звання"])
                    if pd.notna(row.get("Звання"))
                    else models.AcademicTitle.NONE
                ),
                position=models.Position(str(row["Посада"]).strip()),
                fte=float(row["Ставка"]) if pd.notna(row.get("Ставка")) else 1.0,
                department_id=dept.id if dept else None,
            )
            if pd.notna(row.get("Предмети")):
                names = [s.strip() for s in str(row["Предмети"]).split(",") if s.strip()]
                teacher.subjects = [
                    _get_or_create(db, models.Subject, name=name) for name in names
                ]
            db.add(teacher)
            created += 1
        except (KeyError, ValueError) as e:
            errors.append({"row": int(i) + 2, "error": str(e)})
    db.commit()
    return {"created": created, "errors": errors}


@router.post("/rooms")
async def import_rooms(file: UploadFile, db: Session = Depends(get_db)):
    """Columns: Корпус*, Поверх*, Номер*, Місткість*, Тип, Кафедра, Факультет."""
    df = _read(file)
    created, errors = 0, []
    for i, row in df.iterrows():
        try:
            dept = None
            if pd.notna(row.get("Кафедра")) and pd.notna(row.get("Факультет")):
                faculty = _get_or_create(db, models.Faculty, name=str(row["Факультет"]).strip())
                dept = _get_or_create(
                    db, models.Department, faculty_id=faculty.id, name=str(row["Кафедра"]).strip()
                )
            room = models.Room(
                building=str(row["Корпус"]).strip(),
                floor=int(row["Поверх"]),
                number=str(row["Номер"]).strip(),
                capacity=int(row["Місткість"]),
                room_type=models.RoomType(row["Тип"]) if pd.notna(row.get("Тип")) else models.RoomType.OTHER,
                department_id=dept.id if dept else None,
            )
            db.add(room)
            created += 1
        except (KeyError, ValueError) as e:
            errors.append({"row": int(i) + 2, "error": str(e)})
    db.commit()
    return {"created": created, "errors": errors}


@router.post("/groups")
async def import_groups(file: UploadFile, db: Session = Depends(get_db)):
    """Columns: Факультет*, Спеціальність (код)*, Спеціальність (назва)*,
    Освітня програма, Код групи*, Рік зарахування*, Чисельність."""
    df = _read(file)
    created, errors = 0, []
    for i, row in df.iterrows():
        try:
            faculty = _get_or_create(db, models.Faculty, name=str(row["Факультет"]).strip())
            specialty = _get_or_create(
                db,
                models.Specialty,
                code=str(row["Спеціальність (код)"]).strip(),
                name=str(row["Спеціальність (назва)"]).strip(),
            )
            program = None
            if pd.notna(row.get("Освітня програма")):
                program = _get_or_create(
                    db,
                    models.EducationalProgram,
                    specialty_id=specialty.id,
                    name=str(row["Освітня програма"]).strip(),
                )
            group = models.Group(
                faculty_id=faculty.id,
                specialty_id=specialty.id,
                program_id=program.id if program else None,
                code=str(row["Код групи"]).strip(),
                enrollment_year=int(row["Рік зарахування"]),
                size=int(row["Чисельність"]) if pd.notna(row.get("Чисельність")) else 0,
            )
            db.add(group)
            created += 1
        except (KeyError, ValueError) as e:
            errors.append({"row": int(i) + 2, "error": str(e)})
    db.commit()
    return {"created": created, "errors": errors}
