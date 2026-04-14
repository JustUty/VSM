import psycopg2
import pandas as pd

DB_CONFIG = {
    "host": "217.198.83.165",
    "port": 9030,
    "database": "vsm_service_trains",
    "user": "tmp",
    "password": "ngqU-5Gk9J"
}

def get_trains_list():
    conn = psycopg2.connect(**DB_CONFIG)
    query = """
        SELECT train_name, train_desc, active_number
        FROM trains
        ORDER BY train_name;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_events(train_id, dt_from, dt_to, limit=100000):
    conn = psycopg2.connect(**DB_CONFIG)
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
    conn = psycopg2.connect(**DB_CONFIG)
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