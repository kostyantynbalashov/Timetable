"""Loading problems from YAML/JSON."""
from pathlib import Path

import yaml

from .models import Problem


def load_problem(path: str | Path) -> Problem:
    with open(path, encoding="utf-8") as f:
        return Problem.model_validate(yaml.safe_load(f))
