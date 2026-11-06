"""Faculties, departments, specialties, programs, subjects — mostly-static
reference data used by teachers/rooms/groups."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/faculties", response_model=list[schemas.FacultyOut])
def list_faculties(db: Session = Depends(get_db)):
    return db.query(models.Faculty).all()


@router.post("/faculties", response_model=schemas.FacultyOut, status_code=201)
def create_faculty(body: schemas.FacultyIn, db: Session = Depends(get_db)):
    faculty = models.Faculty(**body.model_dump())
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    return faculty


@router.get("/departments", response_model=list[schemas.DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()


@router.post("/departments", response_model=schemas.DepartmentOut, status_code=201)
def create_department(body: schemas.DepartmentIn, db: Session = Depends(get_db)):
    dept = models.Department(**body.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/specialties", response_model=list[schemas.SpecialtyOut])
def list_specialties(db: Session = Depends(get_db)):
    return db.query(models.Specialty).all()


@router.post("/specialties", response_model=schemas.SpecialtyOut, status_code=201)
def create_specialty(body: schemas.SpecialtyIn, db: Session = Depends(get_db)):
    specialty = models.Specialty(**body.model_dump())
    db.add(specialty)
    db.commit()
    db.refresh(specialty)
    return specialty


@router.get("/subjects", response_model=list[schemas.SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()


@router.post("/subjects", response_model=schemas.SubjectOut, status_code=201)
def create_subject(body: schemas.SubjectIn, db: Session = Depends(get_db)):
    subject = models.Subject(**body.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
