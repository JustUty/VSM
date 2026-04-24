import pandas as pd
from collections import deque


def build_timeline(events_df):
    """
    Строит линейную хронологию событий, где каждая активация и деактивация
    отображается отдельной строкой.

    Возвращает DataFrame с колонками:
    - train_id: номер поезда
    - carnumber: номер вагона
    - messagecode: код ДС
    - message_text: расшифровка для отображения (активация или деактивация)
    - timestamp: время события
    - event_type: 'activation' или 'deactivation'
    - pair_id: идентификатор пары (активация + её деактивация имеют одинаковый ID)
    - parsingtime: время парсинга
    """
    if events_df.empty:
        return pd.DataFrame()

    # Сортировка: сначала по времени, затем активации (True) перед деактивациями (False)
    events_df = events_df.sort_values(
        ['timestamp', 'messagestate'],
        ascending=[True, False]
    )

    timeline = []
    active_queues = {}  # key -> deque of active events
    next_pair_id = 1
    orphan_deactivations = []

    for _, row in events_df.iterrows():
        key = (row['messagecode'], row['train_id'], row['carnumber'])

        if key not in active_queues:
            active_queues[key] = deque()

        if row['messagestate'] == True:
            # Активация - добавляем в очередь и создаём запись
            pair_id = f"pair_{next_pair_id}"
            next_pair_id += 1

            active_event = {
                'train_id': row['train_id'],
                'carnumber': row['carnumber'],
                'messagecode': row['messagecode'],
                'activation_time': row['timestamp'],
                'parsingtime': row.get('parsingtime'),
                'pair_id': pair_id
            }
            active_queues[key].append(active_event)

            # Добавляем запись об активации в таймлайн
            timeline.append({
                'train_id': row['train_id'],
                'carnumber': row['carnumber'],
                'messagecode': row['messagecode'],
                'timestamp': row['timestamp'],
                'event_type': 'activation',
                'pair_id': pair_id,
                'parsingtime': row.get('parsingtime'),
                'deactivation_time': None
            })

        elif row['messagestate'] == False:
            # Деактивация - ищем соответствующую активацию
            if active_queues[key]:
                active_event = active_queues[key].popleft()
                pair_id = active_event['pair_id']

                # Определяем время деактивации
                deactivation_time = row.get('gonets')
                if deactivation_time is None or pd.isna(deactivation_time):
                    deactivation_time = row['timestamp']

                # Добавляем запись о деактивации в таймлайн
                timeline.append({
                    'train_id': row['train_id'],
                    'carnumber': row['carnumber'],
                    'messagecode': row['messagecode'],
                    'timestamp': deactivation_time,
                    'event_type': 'deactivation',
                    'pair_id': pair_id,
                    'parsingtime': row.get('parsingtime'),
                    'activation_time': active_event['activation_time']
                })
            else:
                # Нет соответствующей активации - сиротская деактивация
                orphan_pair_id = f"orphan_{next_pair_id}"
                next_pair_id += 1
                orphan_deactivations.append({
                    'train_id': row['train_id'],
                    'carnumber': row['carnumber'],
                    'messagecode': row['messagecode'],
                    'timestamp': row.get('gonets', row['timestamp']),
                    'parsingtime': row.get('parsingtime'),
                    'pair_id': orphan_pair_id,
                    'event_type': 'deactivation'
                })

    # Добавляем "сиротские" деактивации
    for orphan in orphan_deactivations:
        timeline.append({
            'train_id': orphan['train_id'],
            'carnumber': orphan['carnumber'],
            'messagecode': orphan['messagecode'],
            'timestamp': orphan['timestamp'],
            'event_type': 'deactivation',
            'pair_id': orphan['pair_id'],
            'parsingtime': orphan['parsingtime'],
            'activation_time': None
        })

    # Добавляем незакрытые активации (сообщения, активные до сих пор)
    for key, queue in active_queues.items():
        for active_event in queue:
            # Добавляем запись об активации, которая так и не закрылась
            timeline.append({
                'train_id': active_event['train_id'],
                'carnumber': active_event['carnumber'],
                'messagecode': active_event['messagecode'],
                'timestamp': active_event['activation_time'],
                'event_type': 'activation',
                'pair_id': active_event['pair_id'],
                'parsingtime': active_event['parsingtime'],
                'deactivation_time': None
            })
            # Также добавляем маркер, что сообщение всё ещё активно
            timeline.append({
                'train_id': active_event['train_id'],
                'carnumber': active_event['carnumber'],
                'messagecode': active_event['messagecode'],
                'timestamp': pd.Timestamp.now(),
                'event_type': 'still_active_marker',
                'pair_id': active_event['pair_id'],
                'parsingtime': active_event['parsingtime'],
                'activation_time': active_event['activation_time']
            })

    # Сортируем таймлайн по времени
    result_df = pd.DataFrame(timeline)
    if not result_df.empty:
        result_df = result_df.sort_values('timestamp').reset_index(drop=True)

    # Добавляем текст сообщения для каждой записи
    if not result_df.empty:
        result_df['message_text'] = result_df.apply(
            lambda row: get_message_text_for_row(row), axis=1
        )

    return result_df


def get_message_text_for_row(row):
    """
    Возвращает подходящий текст для строки таймлайна в зависимости от типа события.
    Для активации: kurztext_3 (сообщение появилось)
    Для деактивации: kurztext_4 (сообщение больше не активно)
    """
    from analyzer.handlers.human_readable import get_human_message_templates

    code = row['messagecode']
    event_type = row.get('event_type', 'activation')
    templates = get_human_message_templates(code)

    if event_type == 'activation':
        # Для активации: сначала пробуем kurztext_3, затем kurztext_2
        text = templates.get('kurztext_3', '')
        if not text:
            text = templates.get('kurztext_2', f'Поступило сообщение с кодом ДС {code}')
        return text
    elif event_type == 'deactivation':
        # Для деактивации: kurztext_4
        text = templates.get('kurztext_4', '')
        if not text:
            text = f'Сообщение с кодом ДС {code} более не активно'
        return text
    elif event_type == 'still_active_marker':
        act_time = row.get('activation_time', 'неизвестного времени')
        if isinstance(act_time, pd.Timestamp):
            act_time = act_time.strftime('%d.%m.%Y %H:%M:%S')
        return f'⚠️ Сообщение с кодом ДС {code} остаётся активным до сих пор (с {act_time})'
    else:
        return f'Код ДС {code}: неизвестное событие'


def format_duration(seconds):
    """Оставлен для совместимости, но не используется в новой версии"""
    if seconds is None:
        return None
    if seconds < 0:
        return "Ошибка"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}ч {minutes}м {secs}с"
    elif minutes > 0:
        return f"{minutes}м {secs}с"
    else:
        return f"{secs}с"