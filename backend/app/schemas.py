"""Pydantic I/O schemas, separate from the ORM models."""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    AcademicTitle,
    Degree,
    LessonType,
    OccurrenceStatus,
    PatternType,
    Position,
    RoomType,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------- reference

class FacultyIn(BaseModel):
    name: str


class FacultyOut(ORMModel):
    id: int
    name: str


class SpecialtyIn(BaseModel):
    code: str
    name: str


class DepartmentIn(BaseModel):
    faculty_id: int
    name: str


class DepartmentOut(ORMModel):
    id: int
    faculty_id: int
    name: str


class SpecialtyOut(ORMModel):
    id: int
    code: str
    name: str


class SubjectIn(BaseModel):
    name: str
    department_id: int | None = None


class SubjectOut(ORMModel):
    id: int
    name: str
    department_id: int | None


# ---------------------------------------------------------------- teacher

class TeacherIn(BaseModel):
    last_name: str
    first_name: str
    middle_name: str | None = None
    degree: Degree = Degree.NONE
    academic_title: AcademicTitle = AcademicTitle.NONE
    position: Position
    fte: float = Field(1.0, gt=0, le=2.0)
    department_id: int | None = None
    subject_ids: list[int] = []


class TeacherOut(ORMModel):
    id: int
    last_name: str
    first_name: str
    middle_name: str | None
    degree: Degree
    academic_title: AcademicTitle
    position: Position
    fte: float
    department_id: int | None
    subjects: list[SubjectOut] = []


# ------------------------------------------------------------------- room

class RoomIn(BaseModel):
    department_id: int | None = None
    building: str
    floor: int
    number: str
    capacity: int = Field(gt=0)
    room_type: RoomType = RoomType.OTHER


class RoomOut(ORMModel):
    id: int
    department_id: int | None
    building: str
    floor: int
    number: str
    capacity: int
    room_type: RoomType


# ------------------------------------------------------------------ group

class GroupIn(BaseModel):
    faculty_id: int
    specialty_id: int
    program_id: int | None = None
    code: str
    enrollment_year: int
    size: int = 0


class GroupOut(ORMModel):
    id: int
    faculty_id: int
    specialty_id: int
    program_id: int | None
    code: str
    enrollment_year: int
    size: int


# ------------------------------------------------------- scheduling series

class LessonSeriesIn(BaseModel):
    subject_id: int
    teacher_id: int
    group_id: int
    lesson_type: LessonType
    pattern_type: PatternType
    pattern_params: dict
    academic_year: str
    semester: int = Field(ge=1, le=2)
    room_type_required: RoomType | None = None
    notes: str | None = None


class LessonSeriesOut(ORMModel):
    id: int
    subject_id: int
    teacher_id: int
    group_id: int
    lesson_type: LessonType
    pattern_type: PatternType
    pattern_params: dict
    academic_year: str
    semester: int
    room_type_required: RoomType | None
    notes: str | None


class OccurrenceOut(ORMModel):
    id: int
    series_id: int
    occurrence_date: date
    period: int
    room_id: int | None
    status: OccurrenceStatus
