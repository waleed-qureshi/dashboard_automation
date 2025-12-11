from pydantic import BaseModel
from typing import Optional, List
import datetime


class UserOut(BaseModel):
    id: int
    name: str
    capacity_hours_per_week: float

    class Config:
        orm_mode = True


class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    assignee_id: Optional[int]
    due_date: Optional[datetime.datetime]

    class Config:
        orm_mode = True


class Insight(BaseModel):
    key: str
    value: object

