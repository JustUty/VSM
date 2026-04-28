from analyzer.llm.prompt_builder import build_protocol_prompt
from analyzer.llm.local_model import generate_text


MAX_EVENTS_FOR_LLM = 30


def rewrite_protocol_with_model(
    timeline_df,
    train_name,
    dt_from,
    dt_to
) -> str:
    """
    Генерирует связный текст эксплуатационного протокола
    через локальную LLM-модель.

    Для защиты от переполнения контекста модель получает
    ограниченное количество событий.
    """

    if timeline_df is None or timeline_df.empty:
        return "За выбранный период диагностические сообщения отсутствуют."

    limited_timeline_df = timeline_df.head(MAX_EVENTS_FOR_LLM).copy()

    prompt = build_protocol_prompt(
        timeline_df=limited_timeline_df,
        train_name=train_name,
        dt_from=dt_from,
        dt_to=dt_to
    )

    generated_protocol = generate_text(prompt).strip()

    total_events = len(timeline_df)
    used_events = len(limited_timeline_df)

    if total_events > used_events:
        generated_protocol += (
            "\n\nПримечание: текст сформирован по первым "
            f"{used_events} событиям из {total_events}, так как полный набор "
            "диагностических сообщений превышает допустимый объём контекста локальной модели."
        )

    return generated_protocol