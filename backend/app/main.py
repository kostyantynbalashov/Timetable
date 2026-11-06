from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import groups, import_excel, lesson_series, reference, rooms, schedule, teachers, workload

app = FastAPI(title="Timetable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (teachers, rooms, groups, reference, lesson_series, workload, import_excel, schedule):
    app.include_router(router.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}
