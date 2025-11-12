FROM python:3.9-slim

WORKDIR /API
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]