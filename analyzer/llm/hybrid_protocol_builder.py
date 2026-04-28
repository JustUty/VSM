import pandas as pd
from pathlib import Path

from analyzer.llm.local_model import generate_text
from analyzer.llm.event_aggregator import build_aggregated_events_text
from analyzer.handlers.export import (
    build_human_readable_entry,
    format_datetime,
)


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

INTRO_PROMPT_PATH = PROMPTS_DIR / "protocol_intro_prompt.txt"
CONCLUSION_PROMPT_PATH = PROMPTS_DIR / "protocol_conclusion_prompt.txt"


def load_prompt(path: Path) -> str:
    """Загружает текст промпта из файла."""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def build_events_section(timeline_df: pd.DataFrame) -> str:
    """Формирует точную хронологию событий кодом, без участия модели."""
    if timeline_df is None or timeline_df.empty:
        return "За указанный период диагностические события не обнаружены."

    lines = []

    for _, row in timeline_df.iterrows():
        entry_text = build_human_readable_entry(row)

        if entry_text.strip():
            lines.append(entry_text.strip())
            lines.append("")

    return "\n".join(lines).strip()


def generate_intro(
    train_name: str,
    dt_from,
    dt_to,
    aggregated_summary: str,
) -> str:
    """Генерирует вступительное резюме через локальную модель."""
    prompt_template = load_prompt(INTRO_PROMPT_PATH)

    prompt = prompt_template.format(
        train_name=train_name,
        dt_from=format_datetime(dt_from),
        dt_to=format_datetime(dt_to),
        aggregated_summary=aggregated_summary,
    )

    return generate_text(prompt).strip()


def generate_conclusion(
    train_name: str,
    dt_from,
    dt_to,
    aggregated_summary: str,
) -> str:
    """Генерирует заключение через локальную модель."""
    prompt_template = load_prompt(CONCLUSION_PROMPT_PATH)

    prompt = prompt_template.format(
        train_name=train_name,
        dt_from=format_datetime(dt_from),
        dt_to=format_datetime(dt_to),
        aggregated_summary=aggregated_summary,
    )

    return generate_text(prompt).strip()


def build_hybrid_protocol_text(
    timeline_df: pd.DataFrame,
    train_name: str,
    dt_from,
    dt_to,
    max_groups: int = 30,
) -> str:
    """
    Формирует гибридный эксплуатационный протокол:

    1. Вступительное резюме — генерируется моделью.
    2. Хронология событий — формируется алгоритмически.
    3. Заключение — генерируется моделью.
    """
    if timeline_df is None or timeline_df.empty:
        return (
            "Эксплуатационный протокол\n\n"
            f"Поезд: {train_name}\n"
            f"Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}\n"
            f"Дата формирования: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            "За указанный период диагностические события не обнаружены."
        )

    aggregated_summary = build_aggregated_events_text(
        timeline_df=timeline_df,
        max_groups=max_groups,
    )

    intro_text = generate_intro(
        train_name=train_name,
        dt_from=dt_from,
        dt_to=dt_to,
        aggregated_summary=aggregated_summary,
    )

    events_text = build_events_section(timeline_df)

    conclusion_text = generate_conclusion(
        train_name=train_name,
        dt_from=dt_from,
        dt_to=dt_to,
        aggregated_summary=aggregated_summary,
    )

    protocol_parts = [
        "Эксплуатационный протокол",
        "",
        f"Поезд: {train_name}",
        f"Период: с {format_datetime(dt_from)} по {format_datetime(dt_to)}",
        f"Дата формирования: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}",
        "",
        intro_text,
        "",
        "Хронология диагностических сообщений:",
        "",
        events_text,
        "",
        conclusion_text,
    ]

    return "\n".join(protocol_parts).strip()