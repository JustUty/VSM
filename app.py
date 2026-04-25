import streamlit as st
from analyzer.ui.login_page import check_password, logout
from analyzer.ui.main_page import render_main_page


def main():
    # Проверяем аутентификацию
    if not check_password():
        return  # Показываем форму входа

    # Если аутентификация пройдена, добавляем кнопку выхода
    with st.sidebar:
        st.markdown("---")
        if st.button("Выйти (сменить БД)", width="stretch"):
            logout()

    # Запускаем основное приложение
    render_main_page()


if __name__ == "__main__":
    main()