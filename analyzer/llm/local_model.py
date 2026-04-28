from functools import lru_cache

from llama_cpp import Llama

from analyzer.llm.config import MODEL_PATH, MODEL_CONFIG, GENERATION_CONFIG


@lru_cache(maxsize=1)
def get_model() -> Llama:
    """
    Загружает локальную GGUF-модель один раз и кэширует её.
    Повторные вызовы не будут заново загружать модель в память.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Файл модели не найден: {MODEL_PATH}"
        )

    return Llama(
        model_path=str(MODEL_PATH),
        **MODEL_CONFIG
    )


def generate_text(prompt: str) -> str:
    """
    Генерирует текст на основе переданного промпта.
    Используется для перефразирования диагностических сообщений
    в текст эксплуатационного протокола.
    """
    model = get_model()

    response = model.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты помощник для подготовки эксплуатационных протоколов. "
                    "Твоя задача — только переформулировать входные данные по заданному шаблону. "
                    "Не добавляй факты, которых нет во входных данных."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        **GENERATION_CONFIG
    )

    return response["choices"][0]["message"]["content"].strip()