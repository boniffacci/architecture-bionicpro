from pydantic import BaseModel
from typing import List
from datetime import date

class Report(BaseModel):
    id: int
    title: str
    created_at: date
    summary: str

class ReportsResponse(BaseModel):
    reports: List[Report]
