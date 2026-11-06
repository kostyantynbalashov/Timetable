"""SQLAlchemy ORM models — reference data, people/places, and the flexible
lesson-scheduling model (weekly / cyclic / custom patterns -> occurrences)."""
import enum
from datetime import date

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ---------------------------------------------------------------- reference

class Faculty(Base):
    __tablename__ = "faculties"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)

    departments: Mapped[list["Department"]] = relationship(back_populates="faculty")
    groups: Mapped[list["Group"]] = relationship(back_populates="faculty")


class Department(Base):
    """Кафедра."""
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"))
    name: Mapped[str] = mapped_column(String(200))

    faculty: Mapped[Faculty] = relationship(back_populates="departments")
    __table_args__ = (UniqueConstraint("faculty_id", "name"),)


class Specialty(Base):
    """Спеціальність, напр. '122 Комп'ютерні науки'."""
    __tablename__ = "specialties"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint("code", "name"),)


class EducationalProgram(Base):
    """Освітня програма."""
    __tablename__ = "educational_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"))
    name: Mapped[str] = mapped_column(String(300))

    specialty: Mapped[Specialty] = relationship()


class Subject(Base):
    """Навчальна дисципліна."""
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), unique=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))

    department: Mapped[Department | None] = relationship()


# --------------------------------------------------------------- entities

class Degree(str, enum.Enum):
    NONE = "немає"
    PHD = "кандидат наук / доктор філософії"
    DSC = "доктор наук"


class AcademicTitle(str, enum.Enum):
    NONE = "немає"
    DOCENT = "доцент"
    PROFESSOR = "професор"
    SENIOR_RESEARCHER = "старший дослідник"


class Position(str, enum.Enum):
    ASSISTANT = "асистент"
    LECTURER = "викладач"
    SENIOR_LECTURER = "старший викладач"
    DOCENT = "доцент"
    PROFESSOR = "професор"
    HEAD_OF_DEPARTMENT = "завідувач кафедри"


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    degree: Mapped[Degree] = mapped_column(Enum(Degree), default=Degree.NONE)
    academic_title: Mapped[AcademicTitle] = mapped_column(
        Enum(AcademicTitle), default=AcademicTitle.NONE
    )
    position: Mapped[Position] = mapped_column(Enum(Position, name="position_enum"))
    fte: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)  # частка ставки
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))

    department: Mapped[Department | None] = relationship()
    subjects: Mapped[list[Subject]] = relationship(secondary="teacher_subjects")

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)


class TeacherSubject(Base):
    """Предмети, які читає викладач (M2M)."""
    __tablename__ = "teacher_subjects"
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), primary_key=True)


class RoomType(str, enum.Enum):
    LECTURE_HALL = "лекційна"
    SEMINAR = "семінарська"
    LAB = "лабораторія"
    COMPUTER_LAB = "комп'ютерний клас"
    GYM = "спортзал"
    OTHER = "інше"


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    building: Mapped[str] = mapped_column(String(50))  # корпус
    floor: Mapped[int] = mapped_column()
    number: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column()
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), default=RoomType.OTHER)

    department: Mapped[Department | None] = relationship()
    __table_args__ = (UniqueConstraint("building", "number"),)

    @property
    def label(self) -> str:
        return f"{self.building}-{self.number}"


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id"))
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"))
    program_id: Mapped[int | None] = mapped_column(ForeignKey("educational_programs.id"))
    code: Mapped[str] = mapped_column(String(50), unique=True)  # напр. ІПЗ-21-1
    enrollment_year: Mapped[int] = mapped_column()
    size: Mapped[int] = mapped_column(default=0)  # к-сть студентів

    faculty: Mapped[Faculty] = relationship(back_populates="groups")
    specialty: Mapped[Specialty] = relationship()
    program: Mapped[EducationalProgram | None] = relationship()

    def course(self, as_of_year: int, as_of_month: int = 9) -> int:
        """Курс навчання станом на дату (укр. навчальний рік починається у вересні)."""
        academic_year_start = as_of_year if as_of_month >= 9 else as_of_year - 1
        return max(1, academic_year_start - self.enrollment_year + 1)


# ----------------------------------------------------- scheduling patterns

class LessonType(str, enum.Enum):
    LECTURE = "лекція"
    PRACTICAL = "практичне"
    LAB = "лабораторне"
    SEMINAR = "семінар"
    EXAM = "екзамен"
    CONSULTATION = "консультація"


class PatternType(str, enum.Enum):
    WEEKLY = "стрічковий"   # same weekday+period every week in a range
    CYCLIC = "цикловий"     # consecutive days, same period(s), for a block of weeks
    CUSTOM = "довільний"    # explicit list of occurrences


class LessonSeries(Base):
    """Одна навчальна дисципліна для групи/викладача за певним шаблоном
    розкладу. Шаблон (`pattern_params`) генерує конкретні `Occurrence`.

    pattern_params за типом:
      WEEKLY: {"day_of_week": 0-6, "period": int, "week_from": int, "week_to": int,
                "week_parity": "any"|"odd"|"even"}
      CYCLIC: {"date_from": "YYYY-MM-DD", "days": int, "periods": [int, ...]}
      CUSTOM: {"occurrences": [{"date": "YYYY-MM-DD", "period": int}, ...]}
    """
    __tablename__ = "lesson_series"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    lesson_type: Mapped[LessonType] = mapped_column(Enum(LessonType))
    pattern_type: Mapped[PatternType] = mapped_column(Enum(PatternType))
    pattern_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    academic_year: Mapped[str] = mapped_column(String(9))  # "2026/2027"
    semester: Mapped[int] = mapped_column()
    room_type_required: Mapped[RoomType | None] = mapped_column(Enum(RoomType))
    notes: Mapped[str | None] = mapped_column(String(500))

    subject: Mapped[Subject] = relationship()
    teacher: Mapped[Teacher] = relationship()
    group: Mapped[Group] = relationship()
    occurrences: Mapped[list["Occurrence"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class OccurrenceStatus(str, enum.Enum):
    SCHEDULED = "заплановано"
    CANCELLED = "скасовано"
    MOVED = "перенесено"


class Occurrence(Base):
    """Конкретне заняття на конкретну дату й пару — те, що фактично
    розставляє солвер і бачать користувачі в розкладі."""
    __tablename__ = "occurrences"
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("lesson_series.id"))
    occurrence_date: Mapped[date] = mapped_column(Date)
    period: Mapped[int] = mapped_column()  # номер пари в дні
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    status: Mapped[OccurrenceStatus] = mapped_column(
        Enum(OccurrenceStatus), default=OccurrenceStatus.SCHEDULED
    )

    series: Mapped[LessonSeries] = relationship(back_populates="occurrences")
    room: Mapped[Room | None] = relationship()
    __table_args__ = (UniqueConstraint("series_id", "occurrence_date", "period"),)
