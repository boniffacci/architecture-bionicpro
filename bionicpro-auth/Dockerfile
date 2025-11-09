FROM python:3.13-alpine

WORKDIR /app/
COPY ./requirements.txt /app/
RUN python -m pip install -r requirements.txt

COPY ./bionicpro_auth /app/bionicpro_auth

ENTRYPOINT [ "python", "-m", "bionicpro_auth" ]
