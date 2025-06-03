from fastapi import FastAPI
from models import Report, ReportsResponse
from datetime import date
from random import randint
from faker import Faker

app = FastAPI(title="Reports API")
fake = Faker()

@app.get("/reports", response_model=ReportsResponse)
def get_reports():
    reports = []
    for i in range(10):
        report = Report(
            id=i + 1,
            title=fake.sentence(nb_words=4),
            created_at=fake.date_this_year(),
            summary=fake.paragraph(nb_sentences=3)
        )
        reports.append(report)
    
    return ReportsResponse(reports=reports)
