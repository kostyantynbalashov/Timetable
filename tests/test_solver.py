from collections import Counter
from pathlib import Path

from timetable.io import load_problem
from timetable.solver import solve

SAMPLE = Path(__file__).parent.parent / "data/sample/small.yaml"


def test_sample_is_feasible_and_respects_hard_constraints():
    p = load_problem(SAMPLE)
    res = solve(p, time_limit_s=10)
    assert res is not None
    lessons = {l.id: l for l in p.lessons}
    slot = lambda a: a.day * p.slots_per_day + a.period
    assert len(res) == sum(l.count for l in p.lessons)
    assert max(Counter((slot(a), a.room) for a in res).values()) == 1
    for attr in ("teacher", "group"):
        c = Counter((slot(a), getattr(lessons[a.lesson], attr)) for a in res)
        assert max(c.values()) == 1
    t1_unavail = {0, 1}
    assert not any(slot(a) in t1_unavail for a in res if lessons[a.lesson].teacher == "T1")
