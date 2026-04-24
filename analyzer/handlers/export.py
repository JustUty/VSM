import io
import re
from datetime import datetime

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from analyzer.handlers.human_readable import get_human_message_templates

'''
в human_readable.py лежит логика работы со справочником;
в export.py лежит логика оформления текста для документа;
20.04.2026 добавила функцию для формирования отчета по справочнику
'''


def clean_text(text):
    """Очищает текст от недопустимых символов для XML"""
    if text is None:
        return ''
    text = str(text)
    if pd.isna(text) or text == 'NaT' or text == 'nan':
        return ''
    text = text.replace('\x00', '')
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    if len(text) > 500:
        text = text[:497] + '...'
    return text


def format_datetime(dt):
    """Безопасное форматирование даты/времени"""
    if dt is None:
        return ''
    if pd.isna(dt):
        return ''
    if isinstance(dt, (datetime, pd.Timestamp)):
        try:
            return dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            return str(dt)
    return str(dt)


def build_human_readable_entry(row):
    """
    Формирует человекочитаемый текстовый блок для одной записи timeline_df.
    Использует CSV-справочник по коду ДС.
    """
    code = clean_text(row.get('messagecode', ''))
    train_id = clean_text(row.get('train_id', ''))
    carnumber = clean_text(row.get('carnumber', ''))
    timestamp = row.get('timestamp', None)
    event_type = row.get('event_type', 'activation')
    message_text = clean_text(row.get('message_text', ''))

    timestamp_str = format_datetime(timestamp)

    lines = []

    header_parts = []
    if code:
        header_parts.append(f'Код ДС {code}')
    if train_id:
        header_parts.append(f'поезд {train_id}')
    if carnumber:
        header_parts.append(f'вагон {carnumber}')

    if header_parts:
        lines.append(', '.join(header_parts) + '.')

    if timestamp_str and message_text:
        lines.append(f'{timestamp_str} {message_text}.')
    elif timestamp_str:
        lines.append(f'{timestamp_str} Зафиксировано событие по коду ДС {code}.')

    return '\n'.join(lines)


def build_human_readable_protocol_text(timeline_df, train_human_name, dt_from, dt_to):
    """
    Формирует полный человекочитаемый протокол в виде одного текста.
    Этот текст можно показывать в предпросмотре и редактировать в интерфейсе.
    """
    lines = [
        "Эксплуатационный протокол",
        "",
        f"Поезд: {train_human_name}",
        f"Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}",
        f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
    ]

    if timeline_df.empty:
        lines.append("За указанный период диагностические события не обнаружены.")
        return '\n'.join(lines)

    for _, row in timeline_df.iterrows():
        entry_text = build_human_readable_entry(row)
        lines.append(entry_text)
        lines.append("")

    return '\n'.join(lines).strip()


def export_text_to_docx(protocol_text, file_title="Эксплуатационный протокол"):
    """
    Экспортирует произвольный отредактированный текст протокола в DOCX.
    Каждая непустая строка становится отдельным абзацем.
    """
    try:
        doc = Document()

        lines = str(protocol_text).splitlines()

        if lines:
            first_line = lines[0].strip()
            if first_line:
                title = doc.add_heading(first_line, 0)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                lines = lines[1:]

        for line in lines:
            if line.strip():
                doc.add_paragraph(clean_text(line))
            else:
                doc.add_paragraph("")

        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        return doc_bytes
    except Exception as e:
        print(f"EDITED DOCX export error: {e}")
        return None


def export_to_docx(timeline_df, train_human_name, dt_from, dt_to):
    """Экспорт хронологии в DOCX (табличный формат)"""
    try:
        doc = Document()

        title = doc.add_heading('Эксплуатационный протокол', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f'Поезд: {train_human_name}')
        doc.add_paragraph(f'Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}')
        doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M")}')
        doc.add_paragraph('')

        table = doc.add_table(rows=1, cols=6)
        table.style = 'Table Grid'

        headers = [
            'Номер поезда',
            'Вагон',
            'Код ДС',
            'Тип события',
            'Время события',
            'Описание',
        ]

        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        for _, row in timeline_df.iterrows():
            cells = table.add_row().cells
            cells[0].text = clean_text(row.get('train_id', ''))
            cells[1].text = clean_text(row.get('carnumber', ''))
            cells[2].text = clean_text(row.get('messagecode', ''))

            event_type = row.get('event_type', '')
            if event_type == 'activation':
                cells[3].text = 'Активация'
            elif event_type == 'deactivation':
                cells[3].text = 'Деактивация'
            elif event_type == 'still_active_marker':
                cells[3].text = 'Активно до сих пор'
            else:
                cells[3].text = '—'

            cells[4].text = format_datetime(row.get('timestamp', None))
            cells[5].text = clean_text(row.get('message_text', ''))[:300]

        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        return doc_bytes
    except Exception as e:
        print(f"DOCX export error: {e}")
        return None


def export_human_readable_docx(timeline_df, train_human_name, dt_from, dt_to):
    """Экспорт хронологии в DOCX (человекочитаемый формат)"""
    try:
        doc = Document()

        title = doc.add_heading('Эксплуатационный протокол', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f'Поезд: {train_human_name}')
        doc.add_paragraph(f'Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}')
        doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M")}')
        doc.add_paragraph('')

        if timeline_df.empty:
            doc.add_paragraph('За указанный период диагностические события не обнаружены.')
        else:
            for idx, (_, row) in enumerate(timeline_df.iterrows(), start=1):
                entry_text = build_human_readable_entry(row)

                doc.add_paragraph(f'Событие {idx}')
                for line in entry_text.split('\n'):
                    if line.strip():
                        doc.add_paragraph(clean_text(line))

                doc.add_paragraph('')

        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        return doc_bytes
    except Exception as e:
        print(f"HUMAN DOCX export error: {e}")
        return None


def export_to_xlsx(timeline_df, train_human_name, dt_from, dt_to):
    """Экспорт хронологии в XLSX"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Эксплуатационный протокол"

        # Информационная шапка
        ws['A1'] = f'Поезд: {train_human_name}'
        ws['A2'] = f'Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}'
        ws['A3'] = f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        ws['A5'] = ''

        headers = [
            'Номер поезда',
            'Вагон',
            'Код ДС',
            'Тип события',
            'Время события',
            'Описание',
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=6, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        for row_idx, (_, row) in enumerate(timeline_df.iterrows(), 7):
            ws.cell(row=row_idx, column=1, value=clean_text(row.get('train_id', '')))
            ws.cell(row=row_idx, column=2, value=clean_text(row.get('carnumber', '')))
            ws.cell(row=row_idx, column=3, value=clean_text(row.get('messagecode', '')))

            event_type = row.get('event_type', '')
            if event_type == 'activation':
                event_type_str = 'Активация'
            elif event_type == 'deactivation':
                event_type_str = 'Деактивация'
            elif event_type == 'still_active_marker':
                event_type_str = 'Активно до сих пор'
            else:
                event_type_str = '—'
            ws.cell(row=row_idx, column=4, value=event_type_str)

            ws.cell(row=row_idx, column=5, value=format_datetime(row.get('timestamp', None)))
            ws.cell(row=row_idx, column=6, value=clean_text(row.get('message_text', ''))[:300])

        # Автоматическая ширина колонок
        for col in range(1, 7):
            max_length = 0
            column_letter = ws.cell(row=6, column=col).column_letter
            for row in range(6, ws.max_row + 1):
                cell_value = ws.cell(row=row, column=col).value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        xlsx_bytes = io.BytesIO()
        wb.save(xlsx_bytes)
        xlsx_bytes.seek(0)
        return xlsx_bytes
    except Exception as e:
        print(f"XLSX export error: {e}")
        return None


def export_to_csv(timeline_df, train_human_name, dt_from, dt_to):
    """Экспорт хронологии в CSV"""
    try:
        df_clean = timeline_df.copy()

        # Преобразуем event_type в читаемый вид
        def format_event_type(event_type):
            if event_type == 'activation':
                return 'Активация'
            elif event_type == 'deactivation':
                return 'Деактивация'
            elif event_type == 'still_active_marker':
                return 'Активно до сих пор'
            return '—'

        if 'event_type' in df_clean.columns:
            df_clean['event_type'] = df_clean['event_type'].apply(format_event_type)

        # Очищаем текстовые колонки
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].apply(
                    lambda x: clean_text(x) if x is not None else ''
                )

        # Форматируем временные колонки
        if 'timestamp' in df_clean.columns:
            df_clean['timestamp'] = df_clean['timestamp'].apply(
                lambda x: format_datetime(x) if x is not None else ''
            )

        csv_data = io.StringIO()
        df_clean.to_csv(csv_data, index=False, encoding='utf-8-sig')
        csv_bytes = io.BytesIO(csv_data.getvalue().encode('utf-8-sig'))
        return csv_bytes
    except Exception as e:
        print(f"CSV export error: {e}")
        return None