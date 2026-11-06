# Backend (FastAPI + PostgreSQL)

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/timetable
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/pytest
```

Tables are created automatically on startup (`Base.metadata.create_all`) — no
migrations yet; add Alembic once the schema stabilizes.

## Domain model (`app/models.py`)
- **Reference**: Faculty → Department (кафедра) → Specialty →
  EducationalProgram, Subject.
- **Teacher**: ПІБ, ступінь, звання, посада, частка ставки, кафедра, предмети (M2M).
- **Room**: кафедра, корпус, поверх, номер, місткість, тип.
- **Group**: факультет, спеціальність, програма, код, рік зарахування, чисельність
  (курс обчислюється методом `Group.course()`).
- **LessonSeries + Occurrence**: довільне планування занять. `LessonSeries`
  describes *what* (subject/teacher/group/type) and *how it repeats*
  (`pattern_type` + `pattern_params`); creating it materializes explicit
  `Occurrence` rows (date + period), which is what schedule views, the CP-SAT
  solver, and workload accounting all read. Three pattern generators
  (`app/patterns.py`):
  - **WEEKLY** (стрічковий): same weekday+period every week in a range,
    optional odd/even-week parity.
  - **CYCLIC** (цикловий): consecutive weekdays, same period(s), for a block
    (e.g. a 2-week intensive module).
  - **CUSTOM** (довільний): explicit `(date, period)` list — covers any
    irregular case.

## Workload (`app/workload.py`)
MVP: sums contact hours (1 pair = 2 academic hours) from scheduled
occurrences, grouped by teacher and lesson type, against a configurable
per-FTE norm (default 600h — a placeholder; get the real figure from the
institution). Subgroup-splitting rules for practicals/labs and non-contact
(methodical) workload are not modeled yet.

## Excel import (`app/routers/import_excel.py`)
`POST /api/import/{teachers,rooms,groups}`, multipart `.xlsx`. Unknown
faculties/departments/specialties/subjects are created on the fly; bad rows
are skipped and reported rather than failing the whole import.
