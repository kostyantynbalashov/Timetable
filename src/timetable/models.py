"""Domain model (input data). Validated with pydantic."""
from pydantic import BaseModel, Field


class Teacher(BaseModel):
    id: str
    unavailable: list[int] = Field(default_factory=list)  # slot indices


class Room(BaseModel):
    id: str
    capacity: int


class Group(BaseModel):
    id: str
    size: int


class Lesson(BaseModel):
    """One course requirement: `count` sessions per week of group+teacher."""
    id: str
    group: str
    teacher: str
    count: int = 1


class Problem(BaseModel):
    days: int
    slots_per_day: int
    teachers: list[Teacher]
    rooms: list[Room]
    groups: list[Group]
    lessons: list[Lesson]

    @property
    def n_slots(self) -> int:
        return self.days * self.slots_per_day
