from pathlib import Path

# Корень проекта
BASE_DIR = Path(__file__).resolve().parents[2]

# Путь к GGUF-модели
MODEL_PATH = (
    BASE_DIR
    / "models"
    / "qwen"
    / "qwen2.5-3b-instruct-q4_k_m.gguf"
)

# Конфигурация загрузки модели
MODEL_CONFIG = {
    # Размер контекста
    "n_ctx": 8192,

    # Количество потоков CPU
    # Можно подкрутить под свой процессор
    "n_threads": 6,

    # GPU не используем
    "n_gpu_layers": 0,

    # Логи llama.cpp
    "verbose": False,
}

# Параметры генерации
GENERATION_CONFIG = {
    # Максимальная длина ответа
    "max_tokens": 1200,

    # Низкая температура = меньше фантазии
    "temperature": 0.05,

    # Стабильность генерации
    "top_p": 0.8,

    # Уменьшаем повторы
    "repeat_penalty": 1.25,
}