import pandas as pd
from collections import deque, defaultdict


def build_timeline(events_df):
    if events_df.empty:
        return pd.DataFrame()

    # Сортировка: сначала по времени, затем true перед false
    events_df = events_df.sort_values(
        ['timestamp', 'messagestate'],
        ascending=[True, False]
    )

    timeline = []
    active_queues = {}
    orphan_deactivations = []  # Для отслеживания "сиротских" деактиваций

    for _, row in events_df.iterrows():
        key = (row['messagecode'], row['train_id'], row['carnumber'])

        if key not in active_queues:
            active_queues[key] = deque()

        if row['messagestate'] == True:
            # Активация - добавляем в очередь
            active_queues[key].append({
                'train_id': row['train_id'],
                'carnumber': row['carnumber'],
                'messagecode': row['messagecode'],
                'message_text': row.get('message_text', str(row['messagecode'])),
                'activation_time': row['timestamp'],
                'parsingtime': row.get('parsingtime')
            })

        elif row['messagestate'] == False:
            # Деактивация - закрываем самый старый true
            if active_queues[key]:
                active_event = active_queues[key].popleft()

                # Берём время деактивации из gonets, если оно есть
                deactivation_time = row.get('gonets')
                if deactivation_time is None or pd.isna(deactivation_time):
                    deactivation_time = row['timestamp']

                duration = (deactivation_time - active_event['activation_time']).total_seconds()
                timeline.append({
                    'train_id': active_event['train_id'],
                    'carnumber': active_event['carnumber'],
                    'messagecode': active_event['messagecode'],
                    'message_text': active_event['message_text'],
                    'activation_time': active_event['activation_time'],
                    'deactivation_time': deactivation_time,
                    'duration_str': format_duration(duration),
                    'parsingtime': active_event['parsingtime'],
                    'is_orphan': False  # Маркер нормального события
                })
            else:
                # Нет соответствующей активации - запоминаем как "сиротскую" деактивацию
                orphan_deactivations.append({
                    'train_id': row['train_id'],
                    'carnumber': row['carnumber'],
                    'messagecode': row['messagecode'],
                    'message_text': row.get('message_text', str(row['messagecode'])),
                    'deactivation_time': row.get('gonets', row['timestamp']),
                    'timestamp': row['timestamp'],
                    'parsingtime': row.get('parsingtime')
                })

    # Обработка оставшихся активных событий
    for key, queue in active_queues.items():
        for active_event in queue:
            timeline.append({
                'train_id': active_event['train_id'],
                'carnumber': active_event['carnumber'],
                'messagecode': active_event['messagecode'],
                'message_text': active_event['message_text'],
                'activation_time': active_event['activation_time'],
                'deactivation_time': None,
                'duration_str': 'Активно до сих пор',
                'parsingtime': active_event['parsingtime'],
                'is_orphan': False
            })

    # Добавляем "сиротские" деактивации как отдельные записи
    for orphan in orphan_deactivations:
        timeline.append({
            'train_id': orphan['train_id'],
            'carnumber': orphan['carnumber'],
            'messagecode': orphan['messagecode'],
            'message_text': orphan['message_text'],
            'activation_time': None,  # Нет активации
            'deactivation_time': orphan['deactivation_time'],
            'duration_str': 'Нет начала (деактивация без активации)',
            'parsingtime': orphan['parsingtime'],
            'is_orphan': True  # Маркер "сиротского" события
        })

    result_df = pd.DataFrame(timeline)

    if not result_df.empty and 'message_text' in result_df.columns:
        result_df['message_text'] = result_df.apply(
            lambda row: decode_message_for_row(row), axis=1
        )

    return result_df


def decode_message_for_row(row):
    from analyzer.handlers.decoder import decode_message

    message_text = row.get('message_text', '')
    if message_text and message_text != '' and not str(message_text).startswith('Неизвестный'):
        return message_text
    return decode_message(row['messagecode'])


def format_duration(seconds):
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