import streamlit as st
from datetime import datetime, timedelta

from analyzer.db.queries import get_trains_list
from analyzer.validators.datetime_range import validate_datetime_range


def get_train_type(train_name, train_desc):
    """Определяет тип поезда по имени и описанию"""
    name_lower = train_name.lower()
    desc_lower = train_desc.lower()

    if 'velaro' in name_lower or 'velaro' in desc_lower or 'velarorus' in name_lower:
        return 'Velaro'
    elif 'desiro' in name_lower or 'desirorus' in name_lower or 'эс' in desc_lower:
        return 'Desiro'
    else:
        return 'Другое'


def load_trains_data():
    """Загружает и обрабатывает данные поездов"""
    trains_df = get_trains_list()

    human_to_train_id = {}
    train_id_to_human = {}

    for _, row in trains_df.iterrows():
        train_name = row['train_name']
        train_desc = row['train_desc']

        human_to_train_id[train_desc] = train_name
        train_id_to_human[train_name] = train_desc

    desiro_trains = {}
    velaro_trains = {}

    for human_name, train_id in human_to_train_id.items():
        train_desc = human_name
        train_type = get_train_type(train_id, train_desc)

        if train_type == 'Desiro':
            desiro_trains[human_name] = train_id
        elif train_type == 'Velaro':
            velaro_trains[human_name] = train_id

    return {
        'human_to_train_id': human_to_train_id,
        'train_id_to_human': train_id_to_human,
        'desiro_trains': desiro_trains,
        'velaro_trains': velaro_trains,
    }


def render_train_selector(key_prefix, trains_data, default_train_id=None):
    """
    Рендерит селектор выбора поезда.
    Возвращает train_id.
    """
    desiro_trains = trains_data['desiro_trains']
    velaro_trains = trains_data['velaro_trains']
    train_id_to_human = trains_data['train_id_to_human']

    default_type = "Desiro"
    default_series = None
    default_number = None
    default_velaro = None

    if default_train_id and default_train_id in train_id_to_human:
        default_human = train_id_to_human[default_train_id]

        if default_human in desiro_trains:
            default_type = "Desiro"
            if '-' in default_human:
                default_series, default_number = default_human.split('-', 1)

        elif default_human in velaro_trains:
            default_type = "Velaro"
            default_velaro = default_human

    selected_train_type = st.radio(
        "Тип поезда",
        options=["Desiro", "Velaro"],
        index=0 if default_type == "Desiro" else 1,
        horizontal=True,
        key=f"{key_prefix}_train_type"
    )

    if selected_train_type == "Desiro":
        available_trains = desiro_trains
    else:
        available_trains = velaro_trains

    if not available_trains:
        st.warning(f"Нет доступных поездов типа {selected_train_type}")
        return ""

    if selected_train_type == "Desiro":
        series_set = set()
        number_by_series = {}

        for human_name in available_trains.keys():
            if '-' in human_name:
                series, number = human_name.split('-', 1)
                series_set.add(series)

                if series not in number_by_series:
                    number_by_series[series] = []

                if number not in number_by_series[series]:
                    number_by_series[series].append(number)

        series_list = sorted(series_set)

        for series in number_by_series:
            number_by_series[series] = sorted(number_by_series[series])

        series_index = 0
        if default_series and default_series in series_list:
            series_index = series_list.index(default_series)

        selected_series = st.selectbox(
            "Серия поезда",
            options=series_list,
            index=series_index,
            key=f"{key_prefix}_series"
        )

        available_numbers = number_by_series.get(selected_series, [])

        number_index = 0
        if default_number and default_number in available_numbers:
            number_index = available_numbers.index(default_number)

        selected_number = st.selectbox(
            "Номер поезда",
            options=available_numbers,
            index=number_index,
            key=f"{key_prefix}_number"
        )

        human_name = f"{selected_series}-{selected_number}"
        train_id = available_trains.get(human_name, "")

        st.caption(f"Выбран поезд: **{human_name}**")
        return train_id

    velaro_list = list(available_trains.keys())

    velaro_index = 0
    if default_velaro and default_velaro in velaro_list:
        velaro_index = velaro_list.index(default_velaro)

    selected_velaro = st.selectbox(
        "Выберите поезд Velaro",
        options=velaro_list,
        index=velaro_index,
        key=f"{key_prefix}_velaro"
    )

    train_id = available_trains.get(selected_velaro, "")
    st.caption(f"Выбран поезд: **{selected_velaro}**")
    return train_id


def render_column_selector(default_columns=None):
    """
    Рендерит мультивыбор колонок для отображения.
    Возвращает список выбранных колонок.
    """
    if default_columns is None:
        default_columns = [
            'train_id',
            'carnumber',
            'messagecode',
            'event_type',
            'timestamp',
            'message_text'
        ]

    all_columns_map = {
        'train_id': 'Номер поезда',
        'carnumber': 'Вагон',
        'messagecode': 'Код ДС',
        'event_type': 'Тип события',
        'timestamp': 'Время события',
        'message_text': 'Описание',
        'parsingtime': 'Время парсинга'
    }

    st.caption("Выберите колонки, которые будут отображаться в таблице и экспортироваться")

    if "selected_columns" not in st.session_state:
        st.session_state.selected_columns = default_columns

    selected_keys = st.multiselect(
        "Отображаемые колонки",
        options=list(all_columns_map.keys()),
        format_func=lambda x: all_columns_map[x],
        default=st.session_state.selected_columns,
        key="column_selector_widget"
    )

    st.session_state.selected_columns = selected_keys

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Все колонки", use_container_width=True):
            st.session_state.selected_columns = list(all_columns_map.keys())
            st.rerun()

    with col2:
        if st.button("Сбросить", use_container_width=True):
            st.session_state.selected_columns = default_columns
            st.rerun()

    return st.session_state.selected_columns


def render_filters():
    if "submitted_filters" not in st.session_state:
        st.session_state.submitted_filters = None

    with st.sidebar:
        st.header("Параметры фильтрации")

        try:
            trains_data = load_trains_data()

            st.subheader("Режим анализа")

            mode_options = ["Один поезд", "Два поезда"]
            default_mode_index = 0

            if st.session_state.submitted_filters is not None:
                if st.session_state.submitted_filters.get("train_id_2"):
                    default_mode_index = 1

            selected_mode = st.radio(
                "Выберите режим",
                options=mode_options,
                index=default_mode_index,
                horizontal=True,
                help="Один поезд — стандартный режим. Два поезда — для сравнения или сводного отчета"
            )

            st.markdown("---")

            saved_train_id_1 = None
            saved_train_id_2 = None

            if st.session_state.submitted_filters is not None:
                saved_train_id_1 = st.session_state.submitted_filters.get("train_id")
                saved_train_id_2 = st.session_state.submitted_filters.get("train_id_2")

            st.subheader("Поезд №1")
            train_id_1 = render_train_selector("train1", trains_data, saved_train_id_1)

            train_id_2 = None
            if selected_mode == "Два поезда":
                st.markdown("---")
                st.subheader("Поезд №2")
                train_id_2 = render_train_selector("train2", trains_data, saved_train_id_2)

        except Exception as e:
            st.error(f"Ошибка загрузки списка поездов: {e}")

            default_train_id_1 = ""
            default_train_id_2 = ""

            if st.session_state.submitted_filters is not None:
                default_train_id_1 = st.session_state.submitted_filters.get("train_id", "")
                default_train_id_2 = st.session_state.submitted_filters.get("train_id_2", "")

            train_id_1 = st.text_input(
                "Номер поезда №1 (технический ID)",
                value=default_train_id_1,
                placeholder="VELARORUS_1 или desirorus_12021"
            )

            selected_mode = "Один поезд"
            train_id_2 = None

            mode_checkbox = st.checkbox("Сравнить с другим поездом")
            if mode_checkbox:
                selected_mode = "Два поезда"
                train_id_2 = st.text_input(
                    "Номер поезда №2 (технический ID)",
                    value=default_train_id_2,
                    placeholder="VELARORUS_1 или desirorus_12021"
                )

        st.markdown("---")
        st.subheader("Временной интервал")

        default_to = datetime.now()
        default_from = default_to - timedelta(days=7)

        if st.session_state.submitted_filters is not None:
            default_from = st.session_state.submitted_filters.get("dt_from", default_from)
            default_to = st.session_state.submitted_filters.get("dt_to", default_to)

        if "demo_dt_from" not in st.session_state:
            st.session_state.demo_dt_from = default_from

        if "demo_dt_to" not in st.session_state:
            st.session_state.demo_dt_to = default_to

        demo_btn = st.button(
            "Демонстрация",
            help="Установить интервал: позавчера 13:00 → позавчера 17:00",
            use_container_width=True
        )

        if demo_btn:
            day_before_yesterday = datetime.now().replace(
                hour=13,
                minute=0,
                second=0,
                microsecond=0
            ) - timedelta(days=2)

            st.session_state.demo_dt_from = day_before_yesterday
            st.session_state.demo_dt_to = day_before_yesterday + timedelta(hours=4)

        from_date = st.date_input(
            "Начальная дата",
            value=st.session_state.demo_dt_from.date(),
            key="dt_from_date_input"
        )

        from_time = st.time_input(
            "Начальное время",
            value=st.session_state.demo_dt_from.time(),
            key="dt_from_time_input"
        )

        to_date = st.date_input(
            "Конечная дата",
            value=st.session_state.demo_dt_to.date(),
            key="dt_to_date_input"
        )

        to_time = st.time_input(
            "Конечное время",
            value=st.session_state.demo_dt_to.time(),
            key="dt_to_time_input"
        )

        dt_from = datetime.combine(from_date, from_time)
        dt_to = datetime.combine(to_date, to_time)

        if dt_from != st.session_state.demo_dt_from:
            st.session_state.demo_dt_from = dt_from

        if dt_to != st.session_state.demo_dt_to:
            st.session_state.demo_dt_to = dt_to

        st.markdown("---")

        analyze_btn = st.button(
            "Сформировать протокол",
            type="primary",
            use_container_width=True
        )

        if analyze_btn:
            if dt_from is None or dt_to is None:
                st.error("Выберите начальную и конечную дату")
                return st.session_state.submitted_filters

            is_valid_range, range_error = validate_datetime_range(dt_from, dt_to)
            if not is_valid_range:
                st.error(range_error)
                return st.session_state.submitted_filters

            if not train_id_1:
                st.error("Выберите первый поезд")
                return st.session_state.submitted_filters

            filters_dict = {
                "train_id": train_id_1,
                "train_id_2": train_id_2 if selected_mode == "Два поезда" else None,
                "dt_from": dt_from,
                "dt_to": dt_to,
                "mode": selected_mode,
            }

            st.session_state.submitted_filters = filters_dict

        return st.session_state.submitted_filters