from datetime import datetime, timedelta
import logging
import pandas as pd
from io import StringIO

def parse_datetime(date_str):
    if not date_str or not date_str.strip() or date_str.strip().lower() in ('na', 'nat', 'none', 'null'):
        return None

    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
        
    logging.warning(f"Не удалось распарсить дату: {date_str}")
    return None

def df_to_xcom(df, ti, key):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, date_format='%Y-%m-%d %H:%M:%S')
    ti.xcom_push(key=key, value=csv_buffer.getvalue())

def xcom_to_df(ti, task_id, key):
    csv_data = ti.xcom_pull(task_ids=task_id, key=key)
    if not csv_data:
        raise ValueError(f"Нет данных из XCom: task_id={task_id}, key={key}")
    df = pd.read_csv(StringIO(csv_data))
    if 'signal_time' in df.columns or 'last_signal_time' in df.columns:
        time_col = 'signal_time' if 'signal_time' in df.columns else 'last_signal_time'
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    return df
