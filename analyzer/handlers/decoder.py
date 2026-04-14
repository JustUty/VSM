import psycopg2
import pandas as pd

DB_CONFIG = {
    "host": "217.198.83.165",
    "port": 9030,
    "database": "vsm_service_trains",
    "user": "tmp",
    "password": "ngqU-5Gk9J"
}

_codes_cache = None


def load_message_codes():
    global _codes_cache
    if _codes_cache is not None:
        return _codes_cache

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        query = """
            SELECT name_or_code, description_ru
            FROM master_data
            WHERE name_or_code IS NOT NULL
            AND description_ru IS NOT NULL
            AND description_ru != '';
        """
        df = pd.read_sql(query, conn)
        conn.close()

        _codes_cache = {}
        for _, row in df.iterrows():
            code = str(row['name_or_code']).strip()
            desc = row['description_ru']
            if code not in _codes_cache:
                _codes_cache[code] = desc

        print(f"Loaded {len(_codes_cache)} message codes from database")
        return _codes_cache
    except Exception as e:
        print(f"Error loading codes: {e}")
        return {}


def decode_message(code):
    code_str = str(code).strip()
    codes = load_message_codes()

    if code_str in codes:
        return codes[code_str]
    else:
        return f"Неизвестный код: {code}"


def decode_events_df(df):
    if df is not None and not df.empty:
        df['message_text'] = df['messagecode'].apply(decode_message)
    return df