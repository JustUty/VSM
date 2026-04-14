import streamlit as st
from datetime import datetime, timedelta
from analyzer.db.queries import get_trains_list
from analyzer.validators.datetime_range import validate_datetime_range


def render_filters():
    with st.sidebar:
        st.header("Параметры фильтрации")

        try:
            trains_df = get_trains_list()

            train_display = {}
            for _, row in trains_df.iterrows():
                display_name = f"{row['train_desc']} ({row['train_name']})"
                train_display[display_name] = row['train_name']

            selected_display = st.selectbox(
                "Выберите поезд",
                options=list(train_display.keys()),
                help="Выберите подвижной состав"
            )

            train_id = train_display[selected_display]

            st.caption(f"Выбран поезд: **{train_id}**")

        except Exception as e:
            st.error(f"Ошибка загрузки списка поездов: {e}")
            train_id = st.text_input("Номер поезда", placeholder="VELARORUS_1 или desirorus_12021")

        st.markdown("---")

        st.subheader("Временной интервал")

        default_to = datetime.now()
        default_from = default_to - timedelta(days=7)

        dt_from = st.datetime_input(
            "Начальная дата и время",
            value=default_from
        )

        dt_to = st.datetime_input(
            "Конечная дата и время",
            value=default_to
        )

        st.markdown("---")

        analyze_btn = st.button(
            "Сформировать протокол",
            type="primary",
            use_container_width=True
        )

        if analyze_btn:
            if dt_from is None or dt_to is None:
                st.error("Выберите начальную и конечную дату")
                return None

            is_valid_range, range_error = validate_datetime_range(dt_from, dt_to)
            if not is_valid_range:
                st.error(f"{range_error}")
                return None

            return {
                "train_id": train_id,
                "dt_from": dt_from,
                "dt_to": dt_to
            }

        return None