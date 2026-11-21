from dataclasses import dataclass
from datetime import datetime
from typing import Literal

CountMode = Literal["line_crossing", "zone_entry", "zone_occupancy"]


@dataclass(frozen=True)
class CountEventDraft:
    camera_id: str
    track_id: str
    class_name: str
    mode: CountMode
    direction: str
    occurred_at: datetime
    confidence: float
    model_version: str
    config_version: str
    idempotency_key: str
    count: int = 1
