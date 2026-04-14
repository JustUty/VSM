import streamlit as st
import pandas as pd
from datetime import datetime
from analyzer.ui.filters import render_filters
from analyzer.db.queries import get_events, get_event_stats
from analyzer.handlers.decoder import decode_events_df
from analyzer.handlers.timeline_builder import build_timeline
from analyzer.handlers.export import export_to_docx, export_to_xlsx, export_to_csv


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

                    st.success(f"Загружено {len(events_df)} событий, построено {len(timeline_df)} записей в хронологии")

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
                            display_columns = ['train_id', 'carnumber', 'messagecode', 'message_text',
                                               'activation_time', 'deactivation_time', 'duration_str']
                            column_renames = {
                                'train_id': 'Номер поезда',
                                'carnumber': 'Вагон',
                                'messagecode': 'Код ДС',
                                'message_text': 'Описание ДС',
                                'activation_time': 'Время активации',
                                'deactivation_time': 'Время деактивации',
                                'duration_str': 'Продолжительность'
                            }
                            existing_columns = [col for col in display_columns if col in timeline_df.columns]
                            display_timeline = timeline_df[existing_columns].rename(columns=column_renames)
                            st.dataframe(display_timeline, use_container_width=True)
                        else:
                            st.info("Нет сформированных записей в хронологии")

                    # Таблица событий (сырые данные)
                    with st.expander("Диагностические сообщения (сырые данные)"):
                        display_df = events_df[
                            ['timestamp', 'messagecode', 'message_text', 'carnumber', 'messagestate']].rename(columns={
                            'timestamp': 'Время',
                            'messagecode': 'Код ДС',
                            'message_text': 'Сообщение',
                            'carnumber': 'Вагон',
                            'messagestate': 'Активно'
                        })
                        st.dataframe(display_df, use_container_width=True)

                    # Кнопки экспорта
                    st.markdown("---")
                    st.subheader("Экспорт протокола")

                    # Генерируем файлы для экспорта
                    docx_data = export_to_docx(timeline_df, filters['train_id'], filters['dt_from'], filters['dt_to'])
                    xlsx_data = export_to_xlsx(timeline_df, filters['train_id'], filters['dt_from'], filters['dt_to'])
                    csv_data = export_to_csv(timeline_df, filters['train_id'], filters['dt_from'], filters['dt_to'])

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        if docx_data:
                            st.download_button(
                                label="📄 Экспорт в DOCX",
                                data=docx_data,
                                file_name=f"protocol_{filters['train_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                                key="download_docx_unique"
                            )
                        else:
                            st.error("Ошибка создания DOCX")

                    with col2:
                        if xlsx_data:
                            st.download_button(
                                label="📊 Экспорт в XLSX",
                                data=xlsx_data,
                                file_name=f"protocol_{filters['train_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="download_xlsx_unique"
                            )
                        else:
                            st.error("Ошибка создания XLSX")


                    with col3:
                        if csv_data:
                            st.download_button(
                                label="📋 Экспорт в CSV",
                                data=csv_data,
                                file_name=f"protocol_{filters['train_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="download_csv_unique"
                            )
                        else:
                            st.error("Ошибка создания CSV")

            except Exception as e:
                st.error(f"Ошибка при загрузке данных: {e}")
                st.exception(e)

    else:
        st.info("Выберите поезд и временной интервал на боковой панели, затем нажмите 'Сформировать протокол'")

        with st.expander("Инструкция"):
            st.markdown("""
            1. Выберите **поезд** из списка на боковой панели
            2. Укажите **временной интервал** (начало и конец периода)
            3. Нажмите кнопку **«Сформировать протокол»**
            4. Система отобразит:
               - Статистику по событиям
               - Хронологию эксплуатационных событий с продолжительностью
               - Список диагностических сообщений
            5. Нажмите на кнопку экспорта для выгрузки протокола в нужном формате
            """)


if __name__ == "__main__":
    render_main_page()