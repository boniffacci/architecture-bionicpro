from datetime import datetime, timedelta
from airflow import DAG
from airflow.models.baseoperator import chain
from airflow.providers.postgres.operators.postgres import PostgresOperator

DEFAULT_ARGS = {
    "owner": "data-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="etl_crm_telem_to_olap",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2025, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["etl", "crm", "telemetry", "mart"],
) as dag:

    load_crm_to_stg = PostgresOperator(
        task_id="load_crm_to_stg",
        postgres_conn_id="OLAP_PG",
        sql="""
            truncate table stg.customers_like_src;
            insert into stg.customers_like_src (username, email, first_name, last_name, updated_at)
            select username, email, first_name, last_name, greatest(created_at, updated_at)
            from dblink('{{ conn.CRM_PG.get_uri() }}',
                        'select username, email, first_name, last_name, created_at, updated_at from customers')
                as t(username text, email text, first_name text, last_name text, created_at timestamp, updated_at timestamp);
            """,
    )

    load_telem_to_stg = PostgresOperator(
        task_id="load_telem_to_stg",
        postgres_conn_id="OLAP_PG",
        sql="""
        delete from stg.events_like_src
        where event_time >= date_trunc('day', now() - interval '2 day');

        insert into stg.events_like_src (username, event_time, event_type, event_value)
        select username, event_time, event_type, event_value
        from dblink('{{ conn.TELEM_PG.get_uri() }}',
                    $DBLINK$
                        select username, event_time, event_type, event_value
                        from events
                        where event_time >= date_trunc('day', now() - interval '2 day')
                    $DBLINK$)
        as t(username text, event_time timestamp, event_type text, event_value numeric);
         """,
    )

    build_customer_mart = PostgresOperator(
        task_id="build_customer_mart",
        postgres_conn_id="OLAP_PG",
        sql="""
        with daily as (
          select
            e.username,
            date_trunc('day', e.event_time)::date as dt,
            sum(case when e.event_type = 'accuracy' then 1 else 0 end)::bigint as accuracy,
            sum(case when e.event_type = 'movement' then 1 else 0 end)::bigint as movements,
            coalesce(sum(case when e.event_type = 'intensity' then e.event_value end), 0)::numeric as intensity,
            max(e.event_time) as last_event
          from stg.events_like_src e
          group by e.username, date_trunc('day', e.event_time)
        )
        insert into mart.customer_telemetry_daily as m
          (username, date, accuracy, movements, intensity, last_event)
        select d.username, d.dt, d.accuracy, d.movements, d.intensity, d.last_event
        from daily d
        on conflict (username, date) do update
          set accuracy  = excluded.accuracy,
              movements = excluded.movements,
              intensity = excluded.intensity,
              last_event = greatest(m.last_event, excluded.last_event);
        """,
    )

    analyze_mart = PostgresOperator(
        task_id="analyze_mart",
        postgres_conn_id="OLAP_PG",
        sql="analyze mart.customer_telemetry_daily;",
    )

    chain(load_crm_to_stg, load_telem_to_stg, build_customer_mart, analyze_mart)
