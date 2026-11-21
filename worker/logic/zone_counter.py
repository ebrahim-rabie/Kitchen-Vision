from dataclasses import dataclass
from datetime import datetime

from worker.logic.count_events import CountEventDraft
from worker.logic.ids import idempotency_key
from worker.logic.line_counter import Point, center_of
from worker.pipeline.frame_types import BBox


@dataclass
class _ZoneTrackState:
    inside: bool | None = None
    since: datetime | None = None
    candidate_inside: bool | None = None
    candidate_since: datetime | None = None
    counted: bool = False


def point_in_polygon(point: Point, polygon: tuple[Point, ...]) -> bool:
    if len(polygon) < 3:
        return False
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            x_at_y = (previous.x - current.x) * (point.y - current.y) / (
                previous.y - current.y
            ) + current.x
            if point.x < x_at_y:
                inside = not inside
        previous = current
    return inside


class ZoneCounter:
    def __init__(
        self,
        polygon: tuple[Point, ...],
        dwell_seconds: float = 1.0,
        bucket_seconds: int = 900,
    ) -> None:
        self.polygon = polygon
        self.dwell_seconds = dwell_seconds
        self.bucket_seconds = bucket_seconds
        self._tracks: dict[tuple[str, str, str], _ZoneTrackState] = {}

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
        state = self._tracks.setdefault((camera_id, track_id, class_name), _ZoneTrackState())
        if state.counted:
            return None

        inside = point_in_polygon(center_of(bbox), self.polygon)
        if state.inside is None:
            state.inside = inside
            state.since = timestamp
            return None

        if inside == state.inside:
            state.candidate_inside = None
            state.candidate_since = None
            return None

        if state.candidate_inside != inside:
            state.candidate_inside = inside
            state.candidate_since = timestamp
            return None

        if state.candidate_since is None or state.since is None:
            return None
        if (timestamp - state.candidate_since).total_seconds() < self.dwell_seconds:
            return None
        if (timestamp - state.since).total_seconds() < self.dwell_seconds:
            return None

        entered = bool(inside and not state.inside)
        state.inside = inside
        state.since = timestamp
        state.candidate_inside = None
        state.candidate_since = None
        state.counted = True

        if not entered:
            return None

        return CountEventDraft(
            camera_id=camera_id,
            track_id=track_id,
            class_name=class_name,
            mode="zone_entry",
            direction="entry",
            occurred_at=timestamp,
            confidence=confidence,
            model_version=model_version,
            config_version=config_version,
            idempotency_key=idempotency_key(
                camera_id, track_id, class_name, "zone_entry",
                timestamp.isoformat(), model_version, config_version
            ),
        )

    def snapshot(
        self,
        camera_id: str,
        class_name: str,
        timestamp: datetime,
        tracks: list[str],
        confidence: float,
        model_version: str,
        config_version: str,
    ) -> CountEventDraft:
        bucket = int(timestamp.timestamp()) // self.bucket_seconds
        return CountEventDraft(
            camera_id=camera_id,
            track_id="snapshot",
            class_name=class_name,
            mode="zone_occupancy",
            direction="snapshot",
            occurred_at=timestamp,
            confidence=confidence,
            model_version=model_version,
            config_version=config_version,
            idempotency_key=idempotency_key(
                camera_id, class_name, "zone_occupancy", bucket,
                model_version, config_version
            ),
            count=len(tracks),
        )

    def reset_track(self, camera_id: str, track_id: str) -> None:
        for key in list(self._tracks):
            if key[0] == camera_id and key[1] == track_id:
                del self._tracks[key]
