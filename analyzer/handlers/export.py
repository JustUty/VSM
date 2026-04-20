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

    activation_time = row.get('activation_time', None)
    deactivation_time = row.get('deactivation_time', None)

    activation_time_str = format_datetime(activation_time)
    deactivation_time_str = format_datetime(deactivation_time)

    duration_str = clean_text(row.get('duration_str', ''))

    templates = get_human_message_templates(code)
    activation_text = clean_text(templates.get('kurztext_3', ''))
    deactivation_text = clean_text(templates.get('kurztext_4', ''))

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

    if activation_time_str and activation_text:
        lines.append(f'{activation_time_str} {activation_text}.')
    elif activation_time_str:
        lines.append(f'{activation_time_str} Зафиксировано поступление сообщения.')

    if deactivation_time is not None and not pd.isna(deactivation_time):
        if deactivation_time_str and deactivation_text:
            lines.append(f'С {deactivation_time_str} {deactivation_text}.')
        elif deactivation_time_str:
            lines.append(f'С {deactivation_time_str} сообщение более не активно.')

        if duration_str:
            lines.append(f'Продолжительность активности: {duration_str}.')
    else:
        lines.append('На момент формирования протокола сообщение остаётся активным.')

    return '\n'.join(lines)

def build_human_readable_protocol_text(timeline_df, train_name, dt_from, dt_to):
    """
    Формирует полный человекочитаемый протокол в виде одного текста.
    Этот текст можно показывать в предпросмотре и редактировать в интерфейсе.
    """
    lines = [
        "Эксплуатационный протокол",
        "",
        f"Поезд: {train_name}",
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
    
    
def export_to_docx(timeline_df, train_name, dt_from, dt_to):
    """Экспорт хронологии в DOCX (табличный формат)"""
    try:
        doc = Document()

        title = doc.add_heading('Эксплуатационный протокол', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f'Поезд: {train_name}')
        doc.add_paragraph(f'Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}')
        doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M")}')
        doc.add_paragraph('')

        table = doc.add_table(rows=1, cols=7)
        table.style = 'Table Grid'

        headers = [
            'Номер поезда',
            'Вагон',
            'Код ДС',
            'Описание ДС',
            'Время активации',
            'Время деактивации',
            'Продолжительность',
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
            cells[3].text = clean_text(row.get('message_text', ''))[:200]

            act_time = row.get('activation_time', None)
            cells[4].text = format_datetime(act_time)

            deact_time = row.get('deactivation_time', None)
            if deact_time is not None and not pd.isna(deact_time):
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


def export_human_readable_docx(timeline_df, train_name, dt_from, dt_to):
    """Экспорт хронологии в DOCX (человекочитаемый формат)"""
    try:
        doc = Document()

        title = doc.add_heading('Эксплуатационный протокол', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f'Поезд: {train_name}')
        doc.add_paragraph(f'Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}')
        doc.add_paragraph(f'Дата формирования: {datetime.now().strftime("%d.%m.%Y %H:%M")}')
        doc.add_paragraph('')

        if timeline_df.empty:
            doc.add_paragraph('За указанный период диагностические события не обнаружены.')
        else:
            for idx, (_, row) in enumerate(timeline_df.iterrows(), start=1):
                entry_text = build_human_readable_entry(row)

                #p_num = doc.add_paragraph()
                #p_num.add_run(f'Событие {idx}.').bold = True

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


def export_to_xlsx(timeline_df, train_name, dt_from, dt_to):
    """Экспорт хронологии в XLSX"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Эксплуатационный протокол"

        headers = [
            'Номер поезда',
            'Вагон',
            'Код ДС',
            'Описание ДС',
            'Время активации',
            'Время деактивации',
            'Продолжительность',
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        for row_idx, (_, row) in enumerate(timeline_df.iterrows(), 2):
            ws.cell(row=row_idx, column=1, value=clean_text(row.get('train_id', '')))
            ws.cell(row=row_idx, column=2, value=clean_text(row.get('carnumber', '')))
            ws.cell(row=row_idx, column=3, value=clean_text(row.get('messagecode', '')))
            ws.cell(row=row_idx, column=4, value=clean_text(row.get('message_text', ''))[:200])

            act_time = row.get('activation_time', None)
            ws.cell(row=row_idx, column=5, value=format_datetime(act_time))

            deact_time = row.get('deactivation_time', None)
            if deact_time is not None and not pd.isna(deact_time):
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
                df_clean[col] = df_clean[col].apply(
                    lambda x: clean_text(x) if x is not None else ''
                )
            elif 'time' in col.lower():
                df_clean[col] = df_clean[col].apply(
                    lambda x: format_datetime(x) if x is not None else ''
                )

        csv_data = io.StringIO()
        df_clean.to_csv(csv_data, index=False, encoding='utf-8-sig')
        csv_bytes = io.BytesIO(csv_data.getvalue().encode('utf-8-sig'))
        return csv_bytes
    except Exception as e:
        print(f"CSV export error: {e}")
        return None