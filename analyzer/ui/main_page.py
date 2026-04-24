import streamlit as st
import pandas as pd
from datetime import datetime

from analyzer.ui.filters import render_filters
from analyzer.db.queries import get_events, get_trains_list
from analyzer.handlers.decoder import decode_events_df
from analyzer.handlers.timeline_builder import build_timeline
from analyzer.handlers.export import (
    export_to_docx,
    export_human_readable_docx,
    export_to_xlsx,
    export_to_csv,
    build_human_readable_protocol_text,
    export_text_to_docx,
)


def render_main_page():
    st.set_page_config(
        page_title="АСФЭП-ДС ВПС",
        page_icon="🚆",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("АСФЭП-ДС ВПС")
    st.caption("Автоматизированная система формирования эксплуатационных протоколов")
    st.markdown("---")

    filters = render_filters()

    if filters and filters.get('train_id'):
        with st.spinner("Загрузка данных..."):
            try:
                # Загружаем маппинг поездов для отображения человекочитаемых имен
                trains_df = get_trains_list()
                train_mapping = dict(zip(trains_df['train_name'], trains_df['train_desc']))

                mode = filters.get('mode', 'Один поезд')
                train_id_1 = filters['train_id']
                train_id_2 = filters.get('train_id_2')

                # Загружаем события для первого поезда
                events_df_1 = get_events(
                    train_id_1,
                    filters['dt_from'],
                    filters['dt_to'],
                    limit=100000
                )

                if not events_df_1.empty:
                    events_df_1 = decode_events_df(events_df_1)
                    events_df_1['train_id'] = train_id_1  # Добавляем train_id если его нет
                    timeline_df_1 = build_timeline(events_df_1)
                else:
                    timeline_df_1 = pd.DataFrame()

                # Загружаем события для второго поезда (если режим "Два поезда")
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

                # Объединяем результаты
                if not timeline_df_1.empty and not timeline_df_2.empty:
                    timeline_df = pd.concat([timeline_df_1, timeline_df_2], ignore_index=True)
                    st.success(
                        f"Загружено {len(events_df_1) + (len(events_df_2) if not events_df_2.empty else 0)} событий, "
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
                    # Подменяем train_id на человекочитаемое название
                    timeline_df['train_id'] = timeline_df['train_id'].map(train_mapping).fillna(timeline_df['train_id'])

                    # Статистика
                    with st.expander("Статистика", expanded=True):
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            total_events = len(timeline_df)
                            st.metric("Всего записей", total_events)

                        with col2:
                            unique_codes = timeline_df['messagecode'].nunique()
                            st.metric("Уникальных кодов ДС", unique_codes)

                        with col3:
                            unique_trains = timeline_df['train_id'].nunique()
                            st.metric("Количество поездов", unique_trains)

                        with col4:
                            active_events = len(timeline_df[timeline_df['deactivation_time'].isna()])
                            st.metric("Активных событий", active_events)

                    # Если два поезда — показываем дополнительную статистику по каждому
                    if mode == "Два поезда" and timeline_df['train_id'].nunique() > 1:
                        with st.expander("Статистика по поездам", expanded=True):
                            stats_by_train = timeline_df.groupby('train_id').agg({
                                'messagecode': 'count',
                                'duration_str': lambda x: (x != 'Активно до сих пор').sum()
                            }).rename(columns={'messagecode': 'Количество событий', 'duration_str': 'Завершённых событий'})
                            st.dataframe(stats_by_train, use_container_width=True)

                    # Хронология эксплуатационных событий
                    # Хронология эксплуатационных событий
                    with st.expander("Хронология эксплуатационных событий", expanded=True):
                        if not timeline_df.empty:
                            display_columns = [
                                'train_id',
                                'carnumber',
                                'messagecode',
                                'event_type',
                                'timestamp',
                                'message_text'
                            ]

                            column_renames = {
                                'train_id': 'Номер поезда',
                                'carnumber': 'Вагон',
                                'code': 'Код ДС',
                                'event_type': 'Тип события',
                                'timestamp': 'Время события',
                                'message_text': 'Описание'
                            }

                            # Проверяем наличие колонок
                            existing_columns = [
                                col for col in display_columns if col in timeline_df.columns
                            ]

                            # Преобразуем event_type в человекочитаемый вид для отображения
                            display_timeline = timeline_df[existing_columns].copy()
                            if 'event_type' in display_timeline.columns:
                                event_type_map = {
                                    'activation': 'Активация',
                                    'deactivation': 'Деактивация',
                                    'still_active_marker': '⚠️ Активно до сих пор'
                                }
                                display_timeline['event_type'] = display_timeline['event_type'].map(
                                    event_type_map).fillna(display_timeline['event_type'])

                            display_timeline = display_timeline.rename(columns=column_renames)

                            st.dataframe(display_timeline, use_container_width=True)
                        else:
                            st.info("Нет сформированных записей в хронологии")

                    # Предпросмотр и редактирование человекочитаемого протокола
                    st.markdown("---")
                    with st.expander("Предпросмотр и редактирование протокола", expanded=False):
                        # Формируем название поезда(ов) для заголовка
                        if mode == "Два поезда":
                            train_names = timeline_df['train_id'].unique()
                            train_name_str = " и ".join(train_names)
                        else:
                            train_name_str = train_mapping.get(train_id_1, train_id_1)

                        protocol_text = build_human_readable_protocol_text(
                            timeline_df,
                            train_name_str,
                            filters['dt_from'],
                            filters['dt_to']
                        )

                        st.caption(
                            "Ниже отображается человекочитаемая версия протокола. "
                            "Текст можно отредактировать вручную и скачать в формате DOCX."
                        )

                        edited_protocol_text = st.text_area(
                            "Текст протокола",
                            value=protocol_text,
                            height=500,
                            key="edited_protocol_text"
                        )

                        edited_docx_data = export_text_to_docx(edited_protocol_text)

                        if edited_docx_data:
                            st.download_button(
                                label="Скачать отредактированный DOCX",
                                data=edited_docx_data,
                                file_name=(
                                    f"protocol_edited_{train_name_str}_"
                                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                                ),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                                key="download_edited_docx"
                            )
                        else:
                            st.error("Ошибка формирования отредактированного DOCX")

                    # Экспорт протокола
                    # Экспорт протокола
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

                    if mode == "Два поезда":
                        train_names = "_and_".join(timeline_df['train_id'].unique())
                    else:
                        train_names = train_mapping.get(train_id_1, train_id_1)

                    if selected_export_type == "docx_table":
                        export_data = export_to_docx(
                            timeline_df,
                            train_names,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = f"protocol_table_{train_names}_{timestamp_suffix}.docx"
                        export_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                    elif selected_export_type == "docx_human":
                        export_data = export_human_readable_docx(
                            timeline_df,
                            train_names,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = f"protocol_human_{train_names}_{timestamp_suffix}.docx"
                        export_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                    elif selected_export_type == "xlsx":
                        export_data = export_to_xlsx(
                            timeline_df,
                            train_names,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = f"protocol_{train_names}_{timestamp_suffix}.xlsx"
                        export_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                    elif selected_export_type == "csv":
                        export_data = export_to_csv(
                            timeline_df,
                            train_names,
                            filters['dt_from'],
                            filters['dt_to']
                        )
                        export_file_name = f"protocol_{train_names}_{timestamp_suffix}.csv"
                        export_mime = "text/csv"

                    if export_data:
                        st.download_button(
                            label="Скачать протокол",
                            data=export_data,
                            file_name=export_file_name,
                            mime=export_mime,
                            width="stretch",  # Исправлено: use_container_width заменён на width
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
            6. Система отобразит:
               - Статистику по событиям
               - Хронологию эксплуатационных событий с продолжительностью
            7. Выберите нужный формат в разделе **«Экспорт протокола»**
            8. Нажмите кнопку **«Скачать протокол»**
            """)


if __name__ == "__main__":
    render_main_page()