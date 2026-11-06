"""CLI: python -m timetable data/sample/small.yaml"""
import sys

from .io import load_problem
from .solver import solve


def main() -> int:
    result = solve(load_problem(sys.argv[1]))
    if result is None:
        print("No feasible timetable found.")
        return 1
    for a in sorted(result, key=lambda a: (a.day, a.period, a.room)):
        print(f"day {a.day} period {a.period} room {a.room}: {a.lesson}#{a.session}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
