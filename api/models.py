from pydantic import BaseModel
from typing import List

class Report(BaseModel):
    report_id: int
    title: str
    data: List[int]
    summary: str