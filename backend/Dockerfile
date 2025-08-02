FROM python:3.10-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /backend

COPY ./ /backend

RUN pip install -r /backend/requirements.txt


EXPOSE 8000
