import psycopg2
import pandas as pd
from contextlib import contextmanager
import streamlit as st


class DatabaseConnectionManager:
    """Менеджер подключений к БД с автоматическим закрытием"""

    @staticmethod
    def get_current_config():
        """Динамически получает конфиг (с учётом введённых пользователем данных)"""
        from analyzer.db.config import DBConfig
        return DBConfig.get_config()

    @staticmethod
    @contextmanager
    def get_connection():
        """Контекстный менеджер для работы с БД"""
        conn = None
        try:
            config = DatabaseConnectionManager.get_current_config()
            conn = psycopg2.connect(**config)
            yield conn
        except psycopg2.Error as e:
            st.error(f"Ошибка подключения к базе данных: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    def execute_query(query, params=None):
        """Выполняет запрос и возвращает DataFrame"""
        with DatabaseConnectionManager.get_connection() as conn:
            if params:
                df = pd.read_sql(query, conn, params=params)
            else:
                df = pd.read_sql(query, conn)
            return df