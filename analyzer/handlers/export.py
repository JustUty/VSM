import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from fpdf import FPDF
import streamlit as st
from datetime import datetime
import io
import re


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
        except:
            return str(dt)
    return str(dt)


def export_to_docx(timeline_df, train_name, dt_from, dt_to):
    """Экспорт хронологии в DOCX"""
    try:
        doc = Document()

        # Заголовок
        title = doc.add_heading('Эксплуатационный протокол', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Информация о поезде и периоде
        doc.add_paragraph(f'Поезд: {train_name}')
        doc.add_paragraph(f'Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}')
        doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M")}')
        doc.add_paragraph('')

        # Таблица
        table = doc.add_table(rows=1, cols=7)
        table.style = 'Table Grid'

        # Заголовки таблицы
        headers = ['Номер поезда', 'Вагон', 'Код ДС', 'Описание ДС', 'Время активации', 'Время деактивации',
                   'Продолжительность']
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = header
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

        # Данные
        for _, row in timeline_df.iterrows():
            cells = table.add_row().cells
            cells[0].text = clean_text(row.get('train_id', ''))
            cells[1].text = clean_text(row.get('carnumber', ''))
            cells[2].text = clean_text(row.get('messagecode', ''))
            cells[3].text = clean_text(row.get('message_text', ''))[:200]

            act_time = row.get('activation_time', None)
            cells[4].text = format_datetime(act_time)

            deact_time = row.get('deactivation_time', None)
            if deact_time and not pd.isna(deact_time):
                cells[5].text = format_datetime(deact_time)
            else:
                cells[5].text = 'Активно до сих пор'

            cells[6].text = clean_text(row.get('duration_str', ''))

        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        return doc_bytes
    except Exception as e:
        print(f"DOCX export error: {e}")
        return None


def export_to_xlsx(timeline_df, train_name, dt_from, dt_to):
    """Экспорт хронологии в XLSX"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Эксплуатационный протокол"

        # Заголовки
        headers = ['Номер поезда', 'Вагон', 'Код ДС', 'Описание ДС', 'Время активации', 'Время деактивации',
                   'Продолжительность']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        # Данные
        for row_idx, (_, row) in enumerate(timeline_df.iterrows(), 2):
            ws.cell(row=row_idx, column=1, value=clean_text(row.get('train_id', '')))
            ws.cell(row=row_idx, column=2, value=clean_text(row.get('carnumber', '')))
            ws.cell(row=row_idx, column=3, value=clean_text(row.get('messagecode', '')))
            ws.cell(row=row_idx, column=4, value=clean_text(row.get('message_text', ''))[:200])

            act_time = row.get('activation_time', None)
            ws.cell(row=row_idx, column=5, value=format_datetime(act_time))

            deact_time = row.get('deactivation_time', None)
            if deact_time and not pd.isna(deact_time):
                ws.cell(row=row_idx, column=6, value=format_datetime(deact_time))
            else:
                ws.cell(row=row_idx, column=6, value='Активно до сих пор')

            ws.cell(row=row_idx, column=7, value=clean_text(row.get('duration_str', '')))

        xlsx_bytes = io.BytesIO()
        wb.save(xlsx_bytes)
        xlsx_bytes.seek(0)
        return xlsx_bytes
    except Exception as e:
        print(f"XLSX export error: {e}")
        return None




def export_to_csv(timeline_df, train_name, dt_from, dt_to):
    """Экспорт хронологии в CSV"""
    try:
        df_clean = timeline_df.copy()
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].apply(lambda x: clean_text(x) if x is not None else '')
            elif 'time' in col.lower():
                df_clean[col] = df_clean[col].apply(lambda x: format_datetime(x) if x is not None else '')

        csv_data = io.StringIO()
        df_clean.to_csv(csv_data, index=False, encoding='utf-8-sig')
        csv_bytes = io.BytesIO(csv_data.getvalue().encode('utf-8-sig'))
        return csv_bytes
    except Exception as e:
        print(f"CSV export error: {e}")
        return None