import streamlit as st
from datetime import datetime


def check_password():
    """Проверяет пароль БД и возвращает True/False"""

    if "db_authenticated" not in st.session_state:
        st.session_state.db_authenticated = False
        st.session_state.db_user = ""
        st.session_state.db_password = ""
        st.session_state.db_host = ""
        st.session_state.db_port = ""
        st.session_state.db_name = ""

    if st.session_state.db_authenticated:
        return True

    # Показываем форму ввода
    st.title("🔐 Подключение к базе данных")
    st.caption("Введите параметры подключения к базе данных")

    with st.form("db_credentials"):
        # Дефолтные значения (можно предзаполнить, но лучше оставить пустыми)
        db_host = st.text_input(
            "Хост БД",
            value="217.198.83.165",
            help="Адрес сервера базы данных"
        )
        db_port = st.number_input(
            "Порт БД",
            value=9030,
            step=1,
            help="Порт для подключения"
        )
        db_name = st.text_input(
            "Название базы данных",
            value="vsm_service_trains",
            help="Имя базы данных"
        )
        db_user = st.text_input(
            "Пользователь БД",
            value="tmp",
            help="Имя пользователя"
        )
        db_password = st.text_input(
            "Пароль БД",
            type="password",
            help="Пароль для подключения"
        )

        submitted = st.form_submit_button("Подключиться")

        if submitted:
            if not db_user or not db_password:
                st.error("Введите имя пользователя и пароль")
                return False

            # Пробуем подключиться к БД с введёнными параметрами
            try:
                import psycopg2
                test_conn = psycopg2.connect(
                    host=db_host,
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_password
                )
                test_conn.close()

                # Сохраняем в session_state
                st.session_state.db_host = db_host
                st.session_state.db_port = db_port
                st.session_state.db_name = db_name
                st.session_state.db_user = db_user
                st.session_state.db_password = db_password
                st.session_state.db_authenticated = True

                st.success("Подключение успешно!")
                st.rerun()

            except Exception as e:
                st.error(f"Ошибка подключения: {e}")
                return False

    return False


def logout():
    """Сбрасывает аутентификацию"""
    st.session_state.db_authenticated = False
    st.session_state.db_user = ""
    st.session_state.db_password = ""
    st.rerun()