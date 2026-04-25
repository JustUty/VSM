import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


class DBConfig:
    """Централизованная конфигурация базы данных"""

    @staticmethod
    def is_authenticated():
        """Проверяет, аутентифицирован ли пользователь в БД"""
        return st.session_state.get("db_authenticated", False)

    @staticmethod
    def get_config():
        """Возвращает конфигурацию для подключения к БД"""

        # Если пользователь ввёл свои данные через форму
        if st.session_state.get("db_authenticated", False):
            return {
                "host": st.session_state.get("db_host", os.getenv("DB_HOST", "217.198.83.165")),
                "port": int(st.session_state.get("db_port", os.getenv("DB_PORT", 9030))),
                "database": st.session_state.get("db_name", os.getenv("DB_NAME", "vsm_service_trains")),
                "user": st.session_state.get("db_user", os.getenv("DB_USER", "tmp")),
                "password": st.session_state.get("db_password", os.getenv("DB_PASSWORD", ""))
            }

        # Fallback на .env (если не используется форма)
        return {
            "host": os.getenv("DB_HOST", "217.198.83.165"),
            "port": int(os.getenv("DB_PORT", 9030)),
            "database": os.getenv("DB_NAME", "vsm_service_trains"),
            "user": os.getenv("DB_USER", "tmp"),
            "password": os.getenv("DB_PASSWORD", "ngqU-5Gk9J")
        }

    @staticmethod
    def get_connection_string():
        """Возвращает строку подключения для SQLAlchemy"""
        config = DBConfig.get_config()
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"


# Глобальная переменная (будет заполнена после аутентификации)
DB_CONFIG = None  # Заполнится при первом вызове