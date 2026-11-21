from dataclasses import dataclass
from datetime import datetime
from math import hypot
from typing import Literal

from worker.logic.count_events import CountEventDraft
from worker.logic.ids import idempotency_key
from worker.pipeline.frame_types import BBox

Direction = Literal["positive", "negative", "both"]
CountDirection = Literal["positive", "negative"]


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Line:
    start: Point
    end: Point

    def signed_distance(self, point: Point) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        length = hypot(dx, dy)
        if length == 0:
            return 0.0
        cross = dx * (point.y - self.start.y) - dy * (point.x - self.start.x)
        return cross / length

    def side(self, point: Point, margin_px: float = 5.0) -> int | None:
        distance = self.signed_distance(point)
        if distance > margin_px:
            return 1
        if distance < -margin_px:
            return -1
        return None


@dataclass
class _CrossingState:
    side: int | None = None
    side_since: datetime | None = None
    candidate_side: int | None = None
    candidate_since: datetime | None = None
    counted: bool = False


def center_of(bbox: BBox) -> Point:
    x1, y1, x2, y2 = bbox
    return Point(x=(x1 + x2) / 2, y=(y1 + y2) / 2)


class LineCounter:
    def __init__(
        self,
        line: Line,
        direction: Direction = "positive",
        stability_seconds: float = 0.5,
        margin_px: float = 5.0,
    ) -> None:
        self.line = line
        self.direction = direction
        self.stability_seconds = stability_seconds
        self.margin_px = margin_px
        self._tracks: dict[tuple[str, str, str], _CrossingState] = {}

    def update(
        self,
        camera_id: str,
        track_id: str,
        class_name: str,
        bbox: BBox,
        timestamp: datetime,
        confidence: float,
        model_version: str,
        config_version: str,
    ) -> CountEventDraft | None:
        state = self._tracks.setdefault((camera_id, track_id, class_name), _CrossingState())
        if state.counted:
            return None

        side = self.line.side(center_of(bbox), self.margin_px)
        if side is None:
            return None

        if state.side is None:
            state.side = side
            state.side_since = timestamp
            return None

        if side == state.side:
            state.candidate_side = None
            state.candidate_since = None
            return None

        if state.candidate_side != side:
            state.candidate_side = side
            state.candidate_since = timestamp
            return None

        if state.candidate_since is None or state.side_since is None:
            return None
        if (timestamp - state.candidate_since).total_seconds() < self.stability_seconds:
            return None
        if (timestamp - state.side_since).total_seconds() < self.stability_seconds:
            return None

        crossed = "positive" if state.side < 0 and side > 0 else "negative"
        state.side = side
        state.side_since = timestamp
        state.candidate_side = None
        state.candidate_since = None
        state.counted = True

        if self.direction not in ("both", crossed):
            return None

        return CountEventDraft(
            camera_id=camera_id,
            track_id=track_id,
            class_name=class_name,
            mode="line_crossing",
            direction=crossed,
            occurred_at=timestamp,
            confidence=confidence,
            model_version=model_version,
            config_version=config_version,
            idempotency_key=idempotency_key(
                camera_id, track_id, class_name, "line_crossing", crossed,
                timestamp.isoformat(), model_version, config_version
            ),
        )

    def reset_track(self, camera_id: str, track_id: str) -> None:
        for key in list(self._tracks):
            if key[0] == camera_id and key[1] == track_id:
                del self._tracks[key]
