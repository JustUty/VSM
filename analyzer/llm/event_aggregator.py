from __future__ import annotations

import pandas as pd


def _safe_str(value) -> str:
    """
    Безопасно приводит значение к строке.
    """
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def _format_datetime(value) -> str:
    """
    Безопасно форматирует дату/время для передачи в модель.
    """
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    try:
        return pd.to_datetime(value).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return str(value)


def _get_event_time(row) -> str:
    """
    Возвращает основное время события.

    В разных версиях timeline_df время может лежать в разных колонках:
    - timestamp
    - activation_time
    - deactivation_time
    """
    timestamp = row.get("timestamp")
    activation_time = row.get("activation_time")
    deactivation_time = row.get("deactivation_time")

    if timestamp is not None and not pd.isna(timestamp):
        return timestamp

    if activation_time is not None and not pd.isna(activation_time):
        return activation_time

    if deactivation_time is not None and not pd.isna(deactivation_time):
        return deactivation_time

    return None


def prepare_timeline_for_aggregation(timeline_df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготавливает timeline_df к агрегации.

    Приводит основные поля к безопасному виду и создаёт колонку event_time,
    по которой дальше определяется первое и последнее появление сообщения.
    """
    df = timeline_df.copy()

    if df.empty:
        return df

    required_columns = [
        "messagecode",
        "message_text",
        "carnumber",
        "train_id",
        "event_type",
        "timestamp",
        "activation_time",
        "deactivation_time",
        "duration_str",
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    df["messagecode"] = df["messagecode"].apply(_safe_str)
    df["message_text"] = df["message_text"].apply(_safe_str)
    df["carnumber"] = df["carnumber"].apply(_safe_str)
    df["train_id"] = df["train_id"].apply(_safe_str)
    df["event_type"] = df["event_type"].apply(_safe_str)
    df["duration_str"] = df["duration_str"].apply(_safe_str)

    df["event_time"] = df.apply(_get_event_time, axis=1)
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")

    return df


def aggregate_events(timeline_df: pd.DataFrame) -> pd.DataFrame:
    """
    Агрегирует диагностические события для передачи в LLM.

    Вместо сотен отдельных строк формирует компактную сводку:
    - код ДС;
    - описание;
    - вагон;
    - поезд;
    - количество фиксаций;
    - первое появление;
    - последнее появление;
    - количество активаций;
    - количество деактиваций;
    - количество событий без завершения.
    """
    df = prepare_timeline_for_aggregation(timeline_df)

    if df.empty:
        return pd.DataFrame()

    group_columns = [
        "train_id",
        "carnumber",
        "messagecode",
        "message_text",
    ]

    rows = []

    for group_values, group_df in df.groupby(group_columns, dropna=False):
        train_id, carnumber, messagecode, message_text = group_values

        event_count = len(group_df)

        activation_count = (
            group_df["event_type"]
            .astype(str)
            .str.lower()
            .eq("activation")
            .sum()
        )

        deactivation_count = (
            group_df["event_type"]
            .astype(str)
            .str.lower()
            .eq("deactivation")
            .sum()
        )

        active_without_end_count = group_df["deactivation_time"].isna().sum()

        valid_times = group_df["event_time"].dropna()

        first_time = valid_times.min() if not valid_times.empty else None
        last_time = valid_times.max() if not valid_times.empty else None

        rows.append(
            {
                "train_id": train_id,
                "carnumber": carnumber,
                "messagecode": messagecode,
                "message_text": message_text,
                "event_count": int(event_count),
                "activation_count": int(activation_count),
                "deactivation_count": int(deactivation_count),
                "active_without_end_count": int(active_without_end_count),
                "first_time": first_time,
                "last_time": last_time,
            }
        )

    result_df = pd.DataFrame(rows)

    if result_df.empty:
        return result_df

    result_df = result_df.sort_values(
        by=["event_count", "first_time"],
        ascending=[False, True]
    ).reset_index(drop=True)

    return result_df


def build_aggregated_events_text(
    timeline_df: pd.DataFrame,
    max_groups: int = 30
) -> str:
    """
    Формирует компактный текст агрегированной сводки для LLM.

    Именно этот текст нужно передавать модели вместо полного списка событий.
    """
    aggregated_df = aggregate_events(timeline_df)

    if aggregated_df.empty:
        return "Диагностические события отсутствуют."

    total_groups = len(aggregated_df)

    limited_df = aggregated_df.head(max_groups)

    lines = []

    lines.append(
        f"Всего выделено групп диагностических сообщений: {total_groups}."
    )
    lines.append(
        f"В сводке ниже приведены наиболее частые и значимые группы: {len(limited_df)}."
    )
    lines.append("")

    for idx, row in limited_df.iterrows():
        messagecode = _safe_str(row.get("messagecode"))
        message_text = _safe_str(row.get("message_text"))
        train_id = _safe_str(row.get("train_id"))
        carnumber = _safe_str(row.get("carnumber"))

        event_count = int(row.get("event_count", 0))
        activation_count = int(row.get("activation_count", 0))
        deactivation_count = int(row.get("deactivation_count", 0))
        active_without_end_count = int(row.get("active_without_end_count", 0))

        first_time = _format_datetime(row.get("first_time"))
        last_time = _format_datetime(row.get("last_time"))

        block = [
            f"Группа {idx + 1}:",
            f"Код ДС: [{messagecode}]",
            f"Описание ДС: {message_text}",
            f"Поезд: {train_id}",
            f"Вагон: {carnumber}",
            f"Количество фиксаций: {event_count}",
            f"Количество активаций: {activation_count}",
            f"Количество деактиваций: {deactivation_count}",
            f"Количество сообщений без завершения: {active_without_end_count}",
            f"Первое появление: {first_time}",
            f"Последнее появление: {last_time}",
        ]

        lines.append("\n".join(block))
        lines.append("")

    if total_groups > max_groups:
        lines.append(
            f"Примечание: всего групп {total_groups}, "
            f"в промпт переданы первые {max_groups} групп, "
            "отсортированные по частоте фиксации."
        )

    return "\n".join(lines).strip()


def get_aggregation_stats(timeline_df: pd.DataFrame) -> dict:
    """
    Возвращает краткую статистику агрегации.
    Можно использовать в интерфейсе Streamlit.
    """
    aggregated_df = aggregate_events(timeline_df)

    if timeline_df is None or timeline_df.empty:
        total_events = 0
    else:
        total_events = len(timeline_df)

    return {
        "total_events": total_events,
        "total_groups": len(aggregated_df),
    }