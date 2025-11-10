from collections.abc import Generator
from contextlib import contextmanager
import json
from typing import Self

import psycopg2
from psycopg2.extras import RealDictCursor
from anyio import ContextManagerMixin


class ReportService(ContextManagerMixin):
    @contextmanager
    def __contextmanager__(self) -> Generator[Self]:
        self.conn = psycopg2.connect(
            host="airflow-db",
            user="airflow",
            password="airflow",
            dbname="sample",
        )
        yield self
        self.conn.close()

    def load_report(self, username: str):
        if username == "user1":
            user_id = 648821
        elif username == "user2":
            user_id = 6488219
        else:
            raise ValueError

        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        select_query = "SELECT id, buyer_id, telemetry_count, sales_amount FROM sample_facade WHERE buyer_id = %s;"
        cur.execute(select_query, (user_id,))
        rows_as_dicts = cur.fetchall()
        result = [
            {
                "id": row["id"],
                "buyer_id": row["buyer_id"],
                "telemetry_count": row["telemetry_count"],
                "sales_amount": str(row["sales_amount"]),
            }
            for row in rows_as_dicts
        ]
        json_output = json.dumps(result, indent=4)
        cur.close()

        return json_output
