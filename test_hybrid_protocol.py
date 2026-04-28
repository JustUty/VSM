from datetime import datetime

import pandas as pd

from analyzer.llm.hybrid_protocol_builder import build_hybrid_protocol_text


test_df = pd.DataFrame([
    {
        "train_id": "ЭС1-029",
        "carnumber": "1202901",
        "messagecode": "44098",
        "timestamp": datetime(2026, 4, 21, 4, 30, 3),
        "event_type": "activation",
        "message_text": "Поступило ДС 44098 Автопилот:+1 неиспр.линии связи",
    },
    {
        "train_id": "ЭС1-029",
        "carnumber": "1202901",
        "messagecode": "44098",
        "timestamp": datetime(2026, 4, 21, 5, 30, 14),
        "event_type": "deactivation",
        "message_text": "Более не активно ДС 44098 Автопилот:+1 неиспр.линии связи",
    },
    {
        "train_id": "ЭС1-029",
        "carnumber": "1202901",
        "messagecode": "44036",
        "timestamp": datetime(2026, 4, 21, 4, 44, 15),
        "event_type": "activation",
        "message_text": "Поступило ДС 44036 БЛОК: недостоверность GPS",
    },
])

result = build_hybrid_protocol_text(
    timeline_df=test_df,
    train_name="ЭС1-029",
    dt_from=datetime(2026, 4, 21, 4, 0, 0),
    dt_to=datetime(2026, 4, 21, 6, 0, 0),
    max_groups=10,
)

print(result)