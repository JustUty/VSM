import streamlit as st
import pandas as pd
from datetime import datetime

from analyzer.ui.filters import render_filters
from analyzer.db.queries import get_events, get_event_stats
from analyzer.handlers.decoder import decode_events_df
from analyzer.handlers.timeline_builder import build_timeline
from analyzer.handlers.export import (
    export_to_docx,
    export_human_readable_docx,
    export_to_xlsx,
    export_to_csv,
)


def render_main_page():
    st.set_page_config(
        page_title="АСФЭП-ДС ВПС",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("АСФЭП-ДС ВПС")
    st.caption("Автоматизированная система формирования эксплуатационных протоколов")
    st.markdown("---")

    filters = render_filters()

    if filters:
        with st.spinner("Загрузка данных..."):
            try:
                events_df = get_events(
                    filters['train_id'],
                    filters['dt_from'],
                    filters['dt_to'],
                    limit=100000
                )

                if events_df.empty:
                    st.warning("За выбранный период нет диагностических сообщений")
                else:
                    events_df = decode_events_df(events_df)
                    timeline_df = build_timeline(events_df)

                    st.success(
                        f"Загружено {len(events_df)} событий, "
                        f"построено {len(timeline_df)} записей в хронологии"
                    )

                    # Статистика
                    with st.expander("Статистика", expanded=True):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Всего событий", len(events_df))

                        with col2:
                            unique_codes = events_df['messagecode'].nunique()
                            st.metric("Уникальных кодов", unique_codes)

                        with col3:
                            unique_cars = events_df['carnumber'].nunique()
                            st.metric("Задействовано вагонов", unique_cars)

                        with col4:
                            st.metric("Записей в хронологии", len(timeline_df))

                    # Хронология эксплуатационных событий
                    with st.expander("Хронология эксплуатационных событий", expanded=True):
                        if not timeline_df.empty:
                            display_columns = [
                                'train_id',
                                'carnumber',
                                'messagecode',
                                'message_text',
                                'activation_time',
                                'deactivation_time',
                                'duration_str'
                            ]

                            column_renames = {
                                'train_id': 'Номер поезда',
                                'carnumber': 'Вагон',
                                'messagecode': 'Код ДС',
                                'message_text': 'Описание ДС',
                                'activation_time': 'Время активации',
                                'deactivation_time': 'Время деактивации',
                                'duration_str': 'Продолжительность'
                            }

                            existing_columns = [
                                col for col in display_columns if col in timeline_df.columns
                            ]
                            display_timeline = timeline_df[existing_columns].rename(
                                columns=column_renames
                            )

                            st.dataframe(display_timeline, use_container_width=True)
                        else:
                            st.info("Нет сформированных записей в хронологии")

                    # Таблица событий (сырые данные)
                    with st.expander("Диагностические сообщения (сырые данные)"):
                        display_df = events_df[
                            ['timestamp', 'messagecode', 'message_text', 'carnumber', 'messagestate']
                        ].rename(columns={
                            'timestamp': 'Время',
                            'messagecode': 'Код ДС',
                            'message_text': 'Сообщение',
                            'carnumber': 'Вагон',
                            'messagestate': 'Активно'
                        })

                        st.dataframe(display_df, use_container_width=True)

                    # Экспорт протокола
                    st.markdown("---")
                    st.subheader("Экспорт протокола")

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
                    train_id = filters['train_id']

                    if selected_export_type == "docx_table":
                        export_data = export_to_docx(
                            timeline_df,
                            train_id,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = (
                            f"protocol_table_{train_id}_{timestamp_suffix}.docx"
                        )
                        export_mime = (
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        )

                    elif selected_export_type == "docx_human":
                        export_data = export_human_readable_docx(
                            timeline_df,
                            train_id,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = (
                            f"protocol_human_{train_id}_{timestamp_suffix}.docx"
                        )
                        export_mime = (
                            "application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document"
                        )

                    elif selected_export_type == "xlsx":
                        export_data = export_to_xlsx(
                            timeline_df,
                            train_id,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = (
                            f"protocol_{train_id}_{timestamp_suffix}.xlsx"
                        )
                        export_mime = (
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        )

                    elif selected_export_type == "csv":
                        export_data = export_to_csv(
                            timeline_df,
                            train_id,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = (
                            f"protocol_{train_id}_{timestamp_suffix}.csv"
                        )
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
            "Выберите поезд и временной интервал на боковой панели, "
            "затем нажмите 'Сформировать протокол'"
        )

        with st.expander("Инструкция"):
            st.markdown("""
            1. Выберите **поезд** из списка на боковой панели
            2. Укажите **временной интервал** (начало и конец периода)
            3. Нажмите кнопку **«Сформировать протокол»**
            4. Система отобразит:
               - Статистику по событиям
               - Хронологию эксплуатационных событий с продолжительностью
               - Список диагностических сообщений
            5. Выберите нужный формат в разделе **«Экспорт протокола»**
            6. Нажмите кнопку **«Скачать протокол»**
            """)


if __name__ == "__main__":
    render_main_page()