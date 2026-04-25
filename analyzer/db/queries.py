import pandas as pd
from analyzer.db.config import DBConfig
import psycopg2


def _get_connection():
    """Создаёт подключение к БД с безопасной конфигурацией"""
    config = DBConfig.get_config()
    return psycopg2.connect(**config)


def get_trains_list():
    conn = _get_connection()
    query = """
        SELECT train_name, train_desc, active_number
        FROM trains
        ORDER BY train_name;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def get_events(train_id, dt_from, dt_to, limit=100000):
    conn = _get_connection()
    query = """
        SELECT 
            occts as timestamp,
            gonets as gonets,
            messagecode,
            messagestate,
            objectid as train_id,
            carnumber,
            parsingtime
        FROM events
        WHERE objectid = %s
            AND occts BETWEEN %s AND %s
        ORDER BY occts ASC
        LIMIT %s;
    """
    df = pd.read_sql(query, conn, params=[train_id, dt_from, dt_to, limit])
    conn.close()
    return df


def get_event_stats(train_id, dt_from, dt_to):
    conn = _get_connection()
    query = """
        SELECT 
            DATE(occts) as event_date,
            COUNT(*) as event_count,
            COUNT(DISTINCT messagecode) as unique_codes
        FROM events
        WHERE objectid = %s
            AND occts BETWEEN %s AND %s
        GROUP BY DATE(occts)
        ORDER BY event_date;
    """
    df = pd.read_sql(query, conn, params=[train_id, dt_from, dt_to])
    conn.close()
    return df