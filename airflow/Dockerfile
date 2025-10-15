FROM apache/airflow:2.9.2

USER root
RUN bash -lc "set -e; gosu airflow pip install --no-cache-dir clickhouse-connect==0.7.17"
USER airflow


