import pandas as pd
from pathlib import Path

from analyzer.llm.event_aggregator import build_aggregated_events_text


PROMPT_PATH = (
    Path(__file__).resolve().parent
    / "prompts"
    / "protocol_rewrite_prompt.txt"
)


def load_prompt_template() -> str:
    """
    Загружает шаблон промпта из txt-файла.
    """
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def format_datetime(dt) -> str:
    """
    Безопасное форматирование даты/времени.
    """
    if dt is None:
        return "не указано"

    try:
        if pd.isna(dt):
            return "не указано"
    except Exception:
        pass

    try:
        return pd.to_datetime(dt).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return str(dt)


def build_protocol_prompt(
    timeline_df: pd.DataFrame,
    train_name: str,
    dt_from,
    dt_to,
    max_groups: int = 30
) -> str:
    """
    Формирует полный промпт для LLM.

    В модель передается не полный список диагностических сообщений,
    а агрегированная сводка по кодам ДС, вагонам и описаниям.
    Это уменьшает размер промпта и снижает риск повторов.
    """
    template = load_prompt_template()

    events_text = build_aggregated_events_text(
        timeline_df=timeline_df,
        max_groups=max_groups
    )

    prompt = template.format(
        train_name=train_name,
        period_from=format_datetime(dt_from),
        period_to=format_datetime(dt_to),
        events_text=events_text,

        # placeholders из текста промпта, чтобы .format() не падал
        time_start="{time_start}",
        time_end="{time_end}",
        duration="{duration}",
        car_number="{car_number}",
    )

    return prompt