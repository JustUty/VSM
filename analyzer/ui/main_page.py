import streamlit as st
import pandas as pd
from datetime import datetime

from analyzer.ui.filters import render_filters, render_column_selector
from analyzer.db.queries import get_events, get_trains_list
from analyzer.handlers.decoder import decode_events_df
from analyzer.handlers.timeline_builder import build_timeline
from analyzer.handlers.export import (
    export_to_docx,
    export_human_readable_docx,
    export_to_xlsx,
    export_to_csv,
    export_text_to_docx,
    get_column_names_map
)
from analyzer.llm.hybrid_protocol_builder import build_hybrid_protocol_text


def render_main_page():
    st.title("АСФЭП-ДС ВПС")
    st.caption("Автоматизированная система формирования эксплуатационных протоколов")
    st.markdown("---")

    filters = render_filters()

    if filters and filters.get('train_id'):
        with st.spinner("Загрузка данных..."):
            try:
                trains_df = get_trains_list()
                train_mapping = dict(zip(trains_df['train_name'], trains_df['train_desc']))

                mode = filters.get('mode', 'Один поезд')
                train_id_1 = filters['train_id']
                train_id_2 = filters.get('train_id_2')

                events_df_1 = get_events(
                    train_id_1,
                    filters['dt_from'],
                    filters['dt_to'],
                    limit=100000
                )

                if not events_df_1.empty:
                    events_df_1 = decode_events_df(events_df_1)
                    events_df_1['train_id'] = train_id_1
                    timeline_df_1 = build_timeline(events_df_1)
                else:
                    timeline_df_1 = pd.DataFrame()

                timeline_df_2 = pd.DataFrame()
                if mode == "Два поезда" and train_id_2:
                    events_df_2 = get_events(
                        train_id_2,
                        filters['dt_from'],
                        filters['dt_to'],
                        limit=100000
                    )

                    if not events_df_2.empty:
                        events_df_2 = decode_events_df(events_df_2)
                        events_df_2['train_id'] = train_id_2
                        timeline_df_2 = build_timeline(events_df_2)

                if not timeline_df_1.empty and not timeline_df_2.empty:
                    timeline_df = pd.concat([timeline_df_1, timeline_df_2], ignore_index=True)
                    st.success(
                        f"Загружено {len(events_df_1) + len(events_df_2)} событий, "
                        f"построено {len(timeline_df)} записей в хронологии"
                    )
                elif not timeline_df_1.empty:
                    timeline_df = timeline_df_1
                    st.success(
                        f"Загружено {len(events_df_1)} событий, "
                        f"построено {len(timeline_df)} записей в хронологии"
                    )
                elif not timeline_df_2.empty:
                    timeline_df = timeline_df_2
                    st.success(
                        f"Загружено {len(events_df_2)} событий, "
                        f"построено {len(timeline_df)} записей в хронологии"
                    )
                else:
                    timeline_df = pd.DataFrame()
                    st.warning("За выбранный период нет диагностических сообщений")

                if not timeline_df.empty:
                    timeline_df['train_id'] = timeline_df['train_id'].map(train_mapping).fillna(timeline_df['train_id'])

                    default_columns = [
                        'train_id',
                        'carnumber',
                        'messagecode',
                        'event_type',
                        'timestamp',
                        'message_text'
                    ]

                    if "selected_columns" not in st.session_state:
                        st.session_state.selected_columns = default_columns

                    column_names_map = get_column_names_map()

                    if mode == "Два поезда":
                        train_name_str = " и ".join(timeline_df['train_id'].unique())
                        train_names_for_file = "_and_".join(timeline_df['train_id'].unique())
                    else:
                        train_name_str = train_mapping.get(train_id_1, train_id_1)
                        train_names_for_file = train_name_str

                    with st.expander("Статистика", expanded=True):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Всего записей", len(timeline_df))

                        with col2:
                            unique_codes = timeline_df['messagecode'].nunique()
                            st.metric("Уникальных кодов ДС", unique_codes)

                        with col3:
                            unique_trains = timeline_df['train_id'].nunique()
                            st.metric("Количество поездов", unique_trains)

                        with col4:
                            active_events = len(timeline_df[timeline_df['deactivation_time'].isna()])
                            st.metric("Активных событий", active_events)

                    if mode == "Два поезда" and timeline_df['train_id'].nunique() > 1:
                        with st.expander("Статистика по поездам", expanded=True):
                            stats_by_train = timeline_df.groupby('train_id').agg({
                                'messagecode': 'count',
                            }).rename(columns={'messagecode': 'Количество событий'})
                            st.dataframe(stats_by_train, use_container_width=True)

                    with st.expander("Хронология эксплуатационных событий", expanded=True):
                        selected_columns = render_column_selector(st.session_state.selected_columns)

                        if selected_columns:
                            available_cols = [
                                col for col in selected_columns
                                if col in timeline_df.columns
                            ]
                            display_timeline = timeline_df[available_cols].copy()

                            if 'event_type' in display_timeline.columns:
                                event_type_map = {
                                    'activation': 'Активация',
                                    'deactivation': 'Деактивация',
                                    'still_active_marker': '⚠️ Активно до сих пор'
                                }
                                display_timeline['event_type'] = display_timeline['event_type'].map(
                                    event_type_map
                                ).fillna(display_timeline['event_type'])

                            if 'timestamp' in display_timeline.columns:
                                display_timeline['timestamp'] = display_timeline['timestamp'].apply(
                                    lambda x: x.strftime('%d.%m.%Y %H:%M:%S') if pd.notna(x) else ''
                                )

                            display_timeline = display_timeline.rename(columns=column_names_map)
                            st.dataframe(display_timeline, use_container_width=True)
                        else:
                            st.warning("Не выбрано ни одной колонки для отображения")

                    with st.expander("Диагностические сообщения (сырые данные)"):
                        if 'events_df_1' in locals() and not events_df_1.empty:
                            display_df = events_df_1[
                                ['timestamp', 'messagecode', 'message_text', 'carnumber', 'messagestate']
                            ].rename(columns={
                                'timestamp': 'Время',
                                'messagecode': 'Код ДС',
                                'message_text': 'Сообщение',
                                'carnumber': 'Вагон',
                                'messagestate': 'Активно'
                            })
                            st.dataframe(display_df, use_container_width=True)
                        else:
                            st.info("Нет данных для отображения")

                    st.markdown("---")

                    with st.expander("Интеллектуальное формирование протокола", expanded=False):
                        st.markdown(
                            """
                            В данном модуле формируется расширенная человекочитаемая версия эксплуатационного протокола.

                            Локальная языковая модель создаёт вступительное резюме и заключение на основе агрегированной сводки диагностических сообщений. 
                            Основная хронология событий формируется алгоритмически, без изменения исходных временных меток, кодов ДС, номеров поездов и вагонов.

                            После формирования текст можно вручную отредактировать и скачать в формате DOCX.
                            """
                        )

                        hybrid_state_key = "hybrid_protocol_text"

                        if st.button(
                            "Сформировать интеллектуальный протокол",
                            type="primary",
                            use_container_width=True
                        ):
                            with st.spinner("Локальная модель формирует резюме и заключение протокола..."):
                                st.session_state[hybrid_state_key] = build_hybrid_protocol_text(
                                    timeline_df=timeline_df,
                                    train_name=train_name_str,
                                    dt_from=filters['dt_from'],
                                    dt_to=filters['dt_to'],
                                    max_groups=30
                                )

                        if hybrid_state_key in st.session_state:
                            edited_hybrid_text = st.text_area(
                                "Текст интеллектуального протокола",
                                value=st.session_state[hybrid_state_key],
                                height=650,
                                key="edited_hybrid_protocol_text"
                            )

                            hybrid_docx_data = export_text_to_docx(edited_hybrid_text)

                            if hybrid_docx_data:
                                st.download_button(
                                    label="Скачать интеллектуальный протокол (DOCX)",
                                    data=hybrid_docx_data,
                                    file_name=(
                                        f"protocol_intelligent_{train_names_for_file}_"
                                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                                    ),
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    use_container_width=True,
                                    key="download_hybrid_docx"
                                )
                            else:
                                st.error("Ошибка формирования DOCX из текста интеллектуального протокола")
                        else:
                            st.info("Нажмите кнопку выше, чтобы сформировать интеллектуальный протокол.")

                    st.markdown("---")
                    st.subheader("Экспорт файлов")

                    export_options = {
                        "DOCX (табличный протокол)": "docx_table",
                        "DOCX (человекочитаемый протокол)": "docx_human",
                        "XLSX": "xlsx",
                        "CSV": "csv",
                    }

                    selected_export_label = st.selectbox(
                        "Выберите формат экспорта",
                        options=list(export_options.keys()),
                        index=0,
                    )

                    selected_export_type = export_options[selected_export_label]

                    export_data = None
                    export_file_name = None
                    export_mime = None

                    timestamp_suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
                    selected_cols = st.session_state.get('selected_columns', None)

                    if selected_export_type == "docx_table":
                        export_data = export_to_docx(
                            timeline_df,
                            train_names_for_file,
                            filters['dt_from'],
                            filters['dt_to'],
                            selected_columns=selected_cols
                        )
                        export_file_name = f"protocol_table_{train_names_for_file}_{timestamp_suffix}.docx"
                        export_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                    elif selected_export_type == "docx_human":
                        export_data = export_human_readable_docx(
                            timeline_df,
                            train_names_for_file,
                            filters['dt_from'],
                            filters['dt_to'],
                            selected_columns=selected_cols
                        )
                        export_file_name = f"protocol_human_{train_names_for_file}_{timestamp_suffix}.docx"
                        export_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                    elif selected_export_type == "xlsx":
                        export_data = export_to_xlsx(
                            timeline_df,
                            train_names_for_file,
                            filters['dt_from'],
                            filters['dt_to'],
                            selected_columns=selected_cols
                        )
                        export_file_name = f"protocol_{train_names_for_file}_{timestamp_suffix}.xlsx"
                        export_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                    elif selected_export_type == "csv":
                        export_data = export_to_csv(
                            timeline_df,
                            train_names_for_file,
                            filters['dt_from'],
                            filters['dt_to'],
                            selected_columns=selected_cols
                        )
                        export_file_name = f"protocol_{train_names_for_file}_{timestamp_suffix}.csv"
                        export_mime = "text/csv"

                    if export_data:
                        st.download_button(
                            label="Скачать протокол",
                            data=export_data,
                            file_name=export_file_name,
                            mime=export_mime,
                            use_container_width=True,
                            key="download_protocol_unified"
                        )
                    else:
                        st.error("Ошибка формирования выбранного формата экспорта")

            except Exception as e:
                st.error(f"Ошибка при загрузке данных: {e}")
                st.exception(e)

    else:
        st.info(
            "Выберите поезд(а) и временной интервал на боковой панели, "
            "затем нажмите 'Сформировать протокол'"
        )

        with st.expander("Инструкция"):
            st.markdown("""
            1. Выберите **режим анализа** (один или два поезда)
            2. Выберите **тип поезда** (Desiro или Velaro)
            3. Выберите **серию и номер** (для Desiro) или **конкретный поезд** (для Velaro)
            4. Укажите **временной интервал** (начало и конец периода)
            5. Нажмите кнопку **«Сформировать протокол»**
            6. При необходимости настройте **отображаемые колонки**
            7. При необходимости сформируйте интеллектуальный протокол
            8. Выберите нужный формат в разделе **«Экспорт файлов»**
            9. Нажмите кнопку **«Скачать протокол»**
            """)


if __name__ == "__main__":
    render_main_page()