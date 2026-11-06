from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/teachers", tags=["teachers"])


@router.get("", response_model=list[schemas.TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(models.Teacher).all()


@router.post("", response_model=schemas.TeacherOut, status_code=201)
def create_teacher(body: schemas.TeacherIn, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"subject_ids"})
    teacher = models.Teacher(**data)
    if body.subject_ids:
        teacher.subjects = (
            db.query(models.Subject).filter(models.Subject.id.in_(body.subject_ids)).all()
        )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/{teacher_id}", response_model=schemas.TeacherOut)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(404, "Teacher not found")
    return teacher


@router.put("/{teacher_id}", response_model=schemas.TeacherOut)
def update_teacher(teacher_id: int, body: schemas.TeacherIn, db: Session = Depends(get_db)):
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(404, "Teacher not found")
    for k, v in body.model_dump(exclude={"subject_ids"}).items():
        setattr(teacher, k, v)
    if body.subject_ids is not None:
        teacher.subjects = (
            db.query(models.Subject).filter(models.Subject.id.in_(body.subject_ids)).all()
        )
    db.commit()
    db.refresh(teacher)
    return teacher


@router.delete("/{teacher_id}", status_code=204)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(404, "Teacher not found")
    db.delete(teacher)
    db.commit()
