"""CP-SAT model: x[l, k, s, r] = session k of lesson l in slot s, room r."""
from dataclasses import dataclass

from ortools.sat.python import cp_model

from .models import Problem


@dataclass
class Assignment:
    lesson: str
    session: int
    day: int
    period: int
    room: str


def solve(p: Problem, time_limit_s: float = 30.0) -> list[Assignment] | None:
    m = cp_model.CpModel()
    group_size = {g.id: g.size for g in p.groups}
    unavail = {t.id: set(t.unavailable) for t in p.teachers}
    S, R = range(p.n_slots), p.rooms

    x = {}
    for l in p.lessons:
        for k in range(l.count):
            for s in S:
                if s in unavail.get(l.teacher, ()):
                    continue  # hard: teacher availability
                for r in R:
                    if r.capacity >= group_size[l.group]:  # hard: room capacity
                        x[l.id, k, s, r.id] = m.new_bool_var(f"x_{l.id}_{k}_{s}_{r.id}")

    # Hard: each session scheduled exactly once
    for l in p.lessons:
        for k in range(l.count):
            m.add_exactly_one(v for (li, ki, _, _), v in x.items() if li == l.id and ki == k)

    by_lesson = {l.id: l for l in p.lessons}
    for s in S:
        # Hard: no room / teacher / group double-booking
        for r in R:
            m.add_at_most_one(v for (_, _, si, ri), v in x.items() if si == s and ri == r.id)
        for attr in ("teacher", "group"):
            for key in {getattr(l, attr) for l in p.lessons}:
                m.add_at_most_one(
                    v for (li, _, si, _), v in x.items()
                    if si == s and getattr(by_lesson[li], attr) == key
                )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 8
    if solver.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    return [
        Assignment(li, ki, s // p.slots_per_day, s % p.slots_per_day, ri)
        for (li, ki, s, ri), v in x.items() if solver.value(v)
    ]
