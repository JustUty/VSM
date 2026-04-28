import streamlit as st
from analyzer.ui.login_page import check_password, logout
from analyzer.ui.main_page import render_main_page


st.set_page_config(
    page_title="АСФЭП-ДС ВПС",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    if not check_password():
        return

    with st.sidebar:
        st.markdown("---")
        if st.button("Выйти (сменить БД)", use_container_width=True):
            logout()

    render_main_page()


if __name__ == "__main__":
    main()