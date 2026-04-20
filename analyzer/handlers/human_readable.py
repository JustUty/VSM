from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

'''
Скрипт для загрузки csv справочника, поиска шаблона по коду ДС, формирования одного блока человекочитаемого события
Создан и обновлен 20.04.2026
'''

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
HUMAN_MESSAGES_FILE = ASSETS_DIR / "massages_for_protocol.csv"


def _safe_str(value: Any) -> str:
    """
    Безопасно приводит значение к строке.
    Для NaN/None возвращает пустую строку.
    """
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


@lru_cache(maxsize=1)
def load_human_messages_dict() -> dict[str, dict[str, str]]:
    """
    Загружает CSV-справочник человекочитаемых сообщений и
    возвращает словарь вида:

    {
        "21000": {
            "kurztext_2": "...",
            "kurztext_3": "...",
            "kurztext_4": "..."
        },
        ...
    }

    Ключ словаря — meldecode, приведённый к строке.
    """
    if not HUMAN_MESSAGES_FILE.exists():
        raise FileNotFoundError(
            f"Файл справочника не найден: {HUMAN_MESSAGES_FILE}"
        )

    df = pd.read_csv(HUMAN_MESSAGES_FILE)

    required_columns = {
        "meldecode",
        "kurztext_2",
        "kurztext_3",
        "kurztext_4",
    }
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        missing_str = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"В CSV отсутствуют обязательные столбцы: {missing_str}"
        )

    mapping: dict[str, dict[str, str]] = {}

    for _, row in df.iterrows():
        code = _safe_str(row["meldecode"])
        if not code:
            continue

        mapping[code] = {
            "kurztext_2": _safe_str(row.get("kurztext_2")),
            "kurztext_3": _safe_str(row.get("kurztext_3")),
            "kurztext_4": _safe_str(row.get("kurztext_4")),
        }

    return mapping


def get_human_message_templates(message_code: Any) -> dict[str, str]:
    """
    Возвращает шаблоны человекочитаемого текста для конкретного кода ДС.

    Если код не найден, возвращает безопасные шаблоны по умолчанию.
    """
    code = _safe_str(message_code)
    mapping = load_human_messages_dict()

    if code in mapping:
        return mapping[code]

    return {
        "kurztext_2": f"Сообщение с кодом ДС {code}",
        "kurztext_3": f"Поступило сообщение с кодом ДС {code}",
        "kurztext_4": f"Сообщение с кодом ДС {code} более не активно",
    }


def build_human_readable_entry(row: dict[str, Any]) -> str:
    """
    Формирует человекочитаемый текстовый блок для одной записи timeline.

    Ожидает, что row содержит как минимум:
    - messagecode
    - train_id
    - carnumber
    - start_time
    - end_time
    - duration_human

    Возвращает готовый текст для вставки в DOCX.
    """
    code = _safe_str(row.get("messagecode"))
    train_id = _safe_str(row.get("train_id"))
    carnumber = _safe_str(row.get("carnumber"))
    start_time = _safe_str(row.get("start_time"))
    end_time = _safe_str(row.get("end_time"))
    duration_human = _safe_str(row.get("duration_human"))

    templates = get_human_message_templates(code)

    activation_text = templates["kurztext_3"]
    deactivation_text = templates["kurztext_4"]

    header_parts = []
    if code:
        header_parts.append(f"Код ДС {code}")
    if train_id:
        header_parts.append(f"поезд {train_id}")
    if carnumber:
        header_parts.append(f"вагон {carnumber}")

    header = ", ".join(header_parts) + "."

    lines = [header]

    if start_time:
        lines.append(f"Время поступления сообщения: {start_time}.")
        lines.append(f"Описание события: {activation_text}.")

    if end_time and end_time != "Активно до сих пор":
        lines.append(f"Время завершения сообщения: {end_time}.")
        lines.append(f"Статус завершения: {deactivation_text}.")
        if duration_human:
            lines.append(f"Продолжительность активности: {duration_human}.")
    else:
        lines.append(
            "На момент формирования протокола сообщение остаётся активным."
        )

    if row.get("orphan_end", False):
        lines.append(
            "Начало события в пределах выбранного временного интервала не обнаружено."
        )

    return "\n".join(lines)