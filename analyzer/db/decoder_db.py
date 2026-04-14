import psycopg2
import pandas as pd
from functools import lru_cache

DB_CONFIG = {
    "host": "217.198.83.165",
    "port": 9030,
    "database": "vsm_service_trains",
    "user": "tmp",
    "password": "ngqU-5Gk9J"
}


class MessageDecoder:
    def __init__(self):
        self.codes_cache = None

    def load_codes(self):
        """Загружает все коды и описания из master_data для Velaro"""
        if self.codes_cache is not None:
            return self.codes_cache

        try:
            conn = psycopg2.connect(**DB_CONFIG)
            query = """
                SELECT name_or_code, description_ru
                FROM master_data
                WHERE platform = 'Velaro'
                AND description_ru IS NOT NULL;
            """
            df = pd.read_sql(query, conn)
            conn.close()

            # Создаем словарь
            self.codes_cache = dict(zip(df['name_or_code'], df['description_ru']))
            print(f"Loaded {len(self.codes_cache)} message codes from database")
            return self.codes_cache
        except Exception as e:
            print(f"Error loading codes: {e}")
            return {}

    @lru_cache(maxsize=1000)
    def decode(self, code: str) -> str:
        """Декодирует сообщение по коду с кешированием"""
        codes = self.load_codes()
        code_upper = code.upper().strip()

        if code_upper in codes:
            return codes[code_upper]
        else:
            return f"Неизвестное сообщение (код: {code})"

    def decode_dataframe(self, df):
        """Добавляет колонку с расшифровкой в DataFrame"""
        if df is not None and not df.empty:
            df['message_text'] = df['messagecode'].apply(self.decode)
        return df


# Создаем глобальный экземпляр
decoder = MessageDecoder()